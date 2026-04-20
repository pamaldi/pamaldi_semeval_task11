"""
Paraphrase robustness probe for SemEval-2026 Task 11 Subtask 1 (§5.5).

Pipeline:
  1. Stratified-sample 30 originals from the test set (seed=42).
  2. Generate 3 paraphrases per original (voice / synonym / reorder) with
     Claude Sonnet 4.5 (temperature 0). Claude is ONLY the paraphraser.
  3. Run the submitted-config neuro-symbolic pipeline (Qwen3-32B
     extractor via Bedrock bearer token) on each paraphrase.
  4. Compute every metric reasonable for §5.5 and save to
     scores_paraphrase.json.
  5. Print the "PARAPHRASE PROBE SUMMARY" block.

Note: the task description names `lib/bedrock_client.py` for the Qwen
extractor, but the submitted run uses `lib/bedrock_client_bearer.py`
(REST + Bearer token — the non-bearer client has broken auth in this
repo). We use `BedrockClientBearer` to match the submitted pipeline.
"""

import json
import math
import os
import sys
import time
import random
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
LIB_PATH = REPO_ROOT / "pamaldi_semeval_2026_11_task1" / "lib"

# --- Dependencies ------------------------------------------------------------
try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: python-dotenv not installed. Run: <python> -m pip install python-dotenv")
    sys.exit(1)

try:
    import anthropic  # noqa: F401
except ImportError:
    print("ERROR: anthropic not installed. Run: <python> -m pip install anthropic")
    sys.exit(1)

try:
    import requests  # noqa: F401
except ImportError:
    print("ERROR: requests not installed. Run: <python> -m pip install requests")
    sys.exit(1)

# --- Credentials -------------------------------------------------------------
ENV_PATH = REPO_ROOT / ".env"
if not ENV_PATH.exists():
    print(f"ERROR: {ENV_PATH} not found. Aborting.")
    sys.exit(1)

load_dotenv(dotenv_path=ENV_PATH, override=True)

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("ERROR: ANTHROPIC_API_KEY not set after loading .env. Aborting.")
    sys.exit(1)

# AWS creds for Bedrock (Qwen3-32B)
sys.path.insert(0, str(REPO_ROOT))
from load_credentials import load_credentials_from_file  # noqa: E402

AWS_CREDS_CANDIDATES = [
    Path("C:/learning/pamaldi_semeval_task11/subtask_1/aws_credentials.txt"),
    REPO_ROOT / "aws_credentials.txt",
]
AWS_CREDS_PATH = next((p for p in AWS_CREDS_CANDIDATES if p.exists()), None)
if AWS_CREDS_PATH is None:
    print(f"ERROR: no aws_credentials.txt found in any of: {AWS_CREDS_CANDIDATES}")
    sys.exit(1)
load_credentials_from_file(str(AWS_CREDS_PATH))
print(f"AWS creds loaded from: {AWS_CREDS_PATH}")

if not os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
    print("ERROR: AWS_BEARER_TOKEN_BEDROCK not set after loading credentials. Aborting.")
    sys.exit(1)

# --- Pipeline / client imports (lib/) ---------------------------------------
sys.path.insert(0, str(LIB_PATH))

from bedrock_client_bearer import BedrockClientBearer  # noqa: E402
from neurosymbolic_pipeline import NeuroSymbolicPipeline  # noqa: E402

# Import the repo-root Anthropic client (lib/ does not ship one)
from anthropic_client import AnthropicClient  # noqa: E402


# --- Configuration -----------------------------------------------------------
QWEN_MODEL_ID = "qwen.qwen3-32b-v1:0"
CLAUDE_MODEL_ID = "claude-sonnet-4-5-20250929"
CLAUDE_MAX_TOKENS = 400
QWEN_MAX_TOKENS = 4096

PIPELINE_CONFIG = dict(
    use_simplified_extractor=True,
    use_reflexion=False,
    use_self_consistency=True,
    num_consistency_samples=3,
    temperature_schedule=[0.1, 0.3, 0.5],
    use_fallback=True,
    fallback_use_self_consistency=False,
)

TEST_DATA_PATH = (
    REPO_ROOT
    / "board_results"
    / "56_57"
    / "neurosymbolic_test_simplified_20260203_092505"
    / "test_data_subtask_1.json"
)
SUBMITTED_LOGS_DIR = (
    REPO_ROOT
    / "board_results"
    / "56_57"
    / "neurosymbolic_test_simplified_20260203_092505"
    / "logs"
)

SAMPLE_IDS_PATH = REPO_ROOT / "paraphrase_sample_ids.json"
PARAPHRASES_PATH = REPO_ROOT / "paraphrases.json"
PROBE_LOGS_DIR = REPO_ROOT / "logs" / "paraphrase_probe"
SCORES_PATH = REPO_ROOT / "scores_paraphrase.json"

SEED = 42
SUBGROUP_COUNTS = {"VP": 8, "VI": 8, "IP": 7, "II": 7}  # sums to 30

SLEEP_BETWEEN_CALLS = 0.3
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # 1s, 2s, 4s

TRANSFORMATIONS = {
    "voice": (
        "Change active voice to passive voice where grammatically natural, "
        "and passive to active otherwise. Keep the same quantifiers "
        "(all/no/some) and the same three terms."
    ),
    "synonym": (
        "Replace the middle term (the term appearing in both premises "
        "but not in the conclusion) with a semantically equivalent "
        "synonym. Keep the subject and predicate of the conclusion "
        "unchanged."
    ),
    "reorder": (
        "Keep each premise and the conclusion word-for-word identical, "
        "but present premise 2 BEFORE premise 1. The conclusion stays "
        "last."
    ),
}

PROMPT_TEMPLATE = """Paraphrase the following categorical syllogism using the transformation \
described below. Preserve the logical structure EXACTLY: same proposition \
types (all / no / some / some...not), same three terms (except where \
explicitly told to substitute a synonym), same conclusion. Do not \
change truth-value, add hedging, or insert new information.

Transformation: {transformation_description}

Syllogism:
{original_text}

Output ONLY the paraphrased syllogism as exactly three sentences. \
No preamble. No explanation. No bullet points."""


# --- Helpers -----------------------------------------------------------------
def _bool_to_valid(b):
    return "VALID" if b else "INVALID"


def _bool_to_plaus(b):
    return "PLAUSIBLE" if b else "IMPLAUSIBLE"


def _subgroup(validity, plausibility):
    v = "V" if validity == "VALID" else "I"
    p = "P" if plausibility == "PLAUSIBLE" else "I"
    return v + p


def stratified_sample(items, seed):
    rng = random.Random(seed)
    buckets = {k: [] for k in SUBGROUP_COUNTS}
    for it in items:
        validity = _bool_to_valid(it["validity"])
        plausibility = _bool_to_plaus(it["plausibility"])
        buckets[_subgroup(validity, plausibility)].append(it)
    picked = []
    for sg, n in SUBGROUP_COUNTS.items():
        pool = buckets[sg]
        if len(pool) < n:
            raise RuntimeError(f"Not enough {sg} items: have {len(pool)}, need {n}.")
        rng.shuffle(pool)
        picked.extend(pool[:n])
    rng.shuffle(picked)
    return picked


def call_claude_paraphrase(client, original_text, transformation_description):
    """Return (paraphrase_text or None, error_str or None)."""
    prompt = PROMPT_TEMPLATE.format(
        transformation_description=transformation_description,
        original_text=original_text,
    )
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            text = client.generate(prompt=prompt, temperature=0.0)
            return text.strip(), None
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BASE_DELAY * (2 ** attempt))
    return None, str(last_err) if last_err else "unknown_error"


def load_submitted_log(original_id):
    p = SUBMITTED_LOGS_DIR / f"{original_id}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


# --- Step 1: Sample ----------------------------------------------------------
def step1_sample():
    print("=" * 70)
    print("STEP 1: Stratified sample of 30 originals (seed=42)")
    print("=" * 70)
    with open(TEST_DATA_PATH, "r", encoding="utf-8") as f:
        test_items = json.load(f)
    print(f"Loaded {len(test_items)} test instances.")

    picked = stratified_sample(test_items, SEED)
    out = []
    for it in picked:
        validity = _bool_to_valid(it["validity"])
        plaus = _bool_to_plaus(it["plausibility"])
        text = it.get("syllogism") or it.get("text") or ""
        out.append({
            "id": it["id"],
            "original_text": text,
            "validity": validity,
            "plausibility": plaus,
            "subgroup": _subgroup(validity, plaus),
        })
    with open(SAMPLE_IDS_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    sg_counts = Counter(x["subgroup"] for x in out)
    print(f"Saved {len(out)} to {SAMPLE_IDS_PATH}  (subgroup counts: {dict(sg_counts)})")
    return out


# --- Step 2: Paraphrases -----------------------------------------------------
def step2_paraphrases(sample):
    print("=" * 70)
    print("STEP 2: Generating 3 paraphrases per instance (Claude Sonnet 4.5, t=0)")
    print("=" * 70)
    claude = AnthropicClient(
        model_id=CLAUDE_MODEL_ID,
        max_retries=0,          # outer loop handles retries
        base_delay=1.0,
        timeout=120,
        max_tokens=CLAUDE_MAX_TOKENS,
    )

    # Load existing paraphrases.json if present, to resume
    existing = {}
    if PARAPHRASES_PATH.exists():
        try:
            prev = json.loads(PARAPHRASES_PATH.read_text(encoding="utf-8"))
            for e in prev:
                existing[e["id"]] = e
            print(f"Resuming: {len(existing)} existing entries loaded.")
        except Exception:
            existing = {}

    results = []
    call_counter = 0
    start = time.time()
    for i, item in enumerate(sample, 1):
        prev = existing.get(item["id"])
        if prev and all(prev["paraphrases"].get(v) for v in TRANSFORMATIONS):
            results.append(prev)
            continue

        entry = prev or {
            "id": item["id"],
            "subgroup": item["subgroup"],
            "gold_validity": item["validity"],
            "plausibility": item["plausibility"],
            "original": item["original_text"],
            "paraphrases": {v: None for v in TRANSFORMATIONS},
            "generation_raw": {
                v: {"prompt_tokens": None, "completion_tokens": None, "error": None}
                for v in TRANSFORMATIONS
            },
        }

        for variant, desc in TRANSFORMATIONS.items():
            if entry["paraphrases"].get(variant):
                continue
            text, err = call_claude_paraphrase(claude, item["original_text"], desc)
            entry["paraphrases"][variant] = text
            entry["generation_raw"][variant]["error"] = err
            call_counter += 1
            time.sleep(SLEEP_BETWEEN_CALLS)

            # Intermediate save every 10 calls
            if call_counter % 10 == 0:
                _save_paraphrases(results + [entry] + [existing[x["id"]] for x in sample[i:] if x["id"] in existing and existing[x["id"]] is not entry])
        results.append(entry)

        elapsed = int(time.time() - start)
        got = sum(1 for v in entry["paraphrases"].values() if v)
        print(f"[{i}/{len(sample)}] elapsed={elapsed}s  id={item['id'][:8]}  got={got}/3")

    _save_paraphrases(results)
    n_generated = sum(sum(1 for v in r["paraphrases"].values() if v) for r in results)
    print(f"Saved {len(results)} entries ({n_generated}/90 paraphrase texts) to {PARAPHRASES_PATH}")
    return results


def _save_paraphrases(results):
    # Deduplicate by id, preserving order
    seen, out = set(), []
    for r in results:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        out.append(r)
    with open(PARAPHRASES_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)


# --- Step 3: Run pipeline on paraphrases ------------------------------------
def step3_run_pipeline(paraphrases):
    print("=" * 70)
    print("STEP 3: Running neuro-symbolic pipeline on paraphrases (Qwen3-32B)")
    print("=" * 70)
    PROBE_LOGS_DIR.mkdir(parents=True, exist_ok=True)

    qwen = BedrockClientBearer(
        model_id=QWEN_MODEL_ID,
        max_retries=3,
        base_delay=1.0,
        timeout=120,
    )

    pipeline = NeuroSymbolicPipeline(
        bedrock_client=qwen,
        results_dir=str(REPO_ROOT / "logs"),
        run_name="paraphrase_probe_run",
        **PIPELINE_CONFIG,
    )
    # Force the pipeline to emit max_tokens=QWEN_MAX_TOKENS on generate calls:
    # AnthropicClient stores max_tokens internally; BedrockClientBearer does
    # not — the pipeline passes its own default (4096) via generate(). So no
    # action needed here.

    # Build the 90-task list (skip nulls)
    tasks = []
    for r in paraphrases:
        for variant in ("voice", "synonym", "reorder"):
            text = r["paraphrases"].get(variant)
            if not text:
                continue
            tasks.append({
                "compound_id": f"{r['id']}__{variant}",
                "original_id": r["id"],
                "variant": variant,
                "gold_validity": r["gold_validity"],
                "plausibility": r["plausibility"],
                "subgroup": r["subgroup"],
                "original_text": r["original"],
                "paraphrased_text": text,
            })
    print(f"Total paraphrased syllogisms to process: {len(tasks)} (skipped nulls)")

    results = []
    start = time.time()
    for i, t in enumerate(tasks, 1):
        try:
            res = pipeline.process_syllogism(t["paraphrased_text"], t["compound_id"])
        except Exception as e:
            res = {
                "id": t["compound_id"],
                "text": t["paraphrased_text"],
                "extraction_success": False,
                "validity": None,
                "prediction": "INVALID",
                "method": "error",
                "confidence": 0.0,
                "error": str(e),
                "structure": None,
                "validity_details": None,
                "extraction_attempts": 1,
                "self_consistency": None,
                "fallback_info": None,
            }

        res["original_id"] = t["original_id"]
        res["variant"] = t["variant"]
        res["gold_validity"] = t["gold_validity"]
        res["plausibility"] = t["plausibility"]
        res["subgroup"] = t["subgroup"]
        res["original_text"] = t["original_text"]
        res["paraphrased_text"] = t["paraphrased_text"]

        # Save per-instance log to the probe dir AND to the pipeline's own logs_dir
        with open(PROBE_LOGS_DIR / f"{t['compound_id']}.json", "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
        try:
            pipeline._save_log(res)
        except Exception:
            pass

        results.append(res)
        if i % 10 == 0 or i == len(tasks):
            elapsed = int(time.time() - start)
            method = res.get("method") or "error"
            pred = res.get("prediction") or "NONE"
            print(f"[{i}/{len(tasks)}] elapsed={elapsed}s id={t['compound_id'][:16]} "
                  f"variant={t['variant']} method={method} pred={pred}")

    return results


# --- Step 4: Metrics ---------------------------------------------------------
def _acc(correct_list):
    return (sum(correct_list) / len(correct_list) * 100) if correct_list else 0.0


def _tce(sub_correct):
    # sub_correct: dict subgroup -> list[bool]
    a = {k: _acc(sub_correct[k]) for k in ("VP", "VI", "IP", "II")}
    return (abs(a["VP"] - a["VI"]) + abs(a["IP"] - a["II"])) / 2.0


def _combined(acc, tce):
    return acc / (1.0 + math.log(1.0 + tce))


def _group_metrics(records):
    """records: list of dicts with fields gold, pred, subgroup (pred may be
    'VALID'/'INVALID'/'generation_failed'/'error')."""
    scored = [r for r in records if r["pred"] in ("VALID", "INVALID")]
    correct = sum(1 for r in scored if r["pred"] == r["gold"])
    n = len(scored)
    acc = (correct / n * 100) if n else 0.0
    sub = {k: [] for k in ("VP", "VI", "IP", "II")}
    for r in scored:
        sub[r["subgroup"]].append(r["pred"] == r["gold"])
    sub_acc = {k: round(_acc(v), 2) for k, v in sub.items()}
    tce = _tce(sub)
    return {
        "accuracy": round(acc, 2),
        "correct": correct,
        "n": n,
        "subgroup_accuracy": sub_acc,
        "tce": round(tce, 2),
        "combined_score": round(_combined(acc, tce), 2),
    }


def _confusion(records):
    out = {"V->V": 0, "V->I": 0, "I->V": 0, "I->I": 0}
    for r in records:
        if r["pred"] not in ("VALID", "INVALID"):
            continue
        gk = "V" if r["gold"] == "VALID" else "I"
        pk = "V" if r["pred"] == "VALID" else "I"
        out[f"{gk}->{pk}"] += 1
    return out


def _classify_trigger(variant, method, original_method, extracted_structure,
                     extraction_success, original_structure):
    if not extraction_success:
        return "extraction failure"
    if method == "fallback":
        return "fallback judgement"
    # middle-term substitution on synonym variant that then led to wrong pred
    if variant == "synonym" and original_structure and extracted_structure:
        if (original_structure.get("middle_term") or "").lower() != \
           (extracted_structure.get("middle_term") or "").lower():
            return "middle-term surface form changed"
    # E/O mix-up (no A <-> some A-not) — common failure mode
    if extracted_structure and original_structure:
        o_mood = original_structure.get("mood")
        p_mood = extracted_structure.get("mood")
        if o_mood and p_mood and o_mood != p_mood:
            eo_swap = sorted([o_mood, p_mood]) == sorted([o_mood, p_mood])  # always true
            # Detect specifically E/O differences at any position
            for a, b in zip(o_mood, p_mood):
                if {a, b} == {"E", "O"}:
                    return "E/O confusion"
    return "other"


def step4_metrics(paraphrase_results, sample):
    print("=" * 70)
    print("STEP 4: Computing metrics")
    print("=" * 70)

    # --- Submitted-run predictions on the 30 originals ---
    originals = {}
    for s in sample:
        log = load_submitted_log(s["id"])
        if log is None:
            pred = "INVALID"
            method = "error"
            struct = None
        else:
            pred = log.get("prediction") or "INVALID"
            method = log.get("method") or "error"
            struct = log.get("structure")
        originals[s["id"]] = {
            "gold": s["validity"],
            "pred": pred,
            "subgroup": s["subgroup"],
            "method": method,
            "structure": struct,
            "extraction_success": bool((log or {}).get("extraction_success")),
        }

    orig_records = [
        {"id": oid, "gold": d["gold"], "pred": d["pred"], "subgroup": d["subgroup"]}
        for oid, d in originals.items()
    ]
    orig_metrics = _group_metrics(orig_records)
    orig_conf = _confusion(orig_records)
    orig_fallback = sum(1 for d in originals.values() if d["method"] == "fallback") / len(originals)
    orig_extract_fail = sum(1 for d in originals.values() if not d["extraction_success"])

    # --- Paraphrase results by variant ---
    by_variant = {"voice": [], "synonym": [], "reorder": []}
    for r in paraphrase_results:
        variant = r["variant"]
        by_variant[variant].append(r)

    # Build lookup: (original_id, variant) -> result
    pred_lookup = {(r["original_id"], r["variant"]): r for r in paraphrase_results}

    def _records(results_list):
        out = []
        for r in results_list:
            pred = r.get("prediction")
            if pred not in ("VALID", "INVALID"):
                pred = "INVALID"  # conservative default for rows that went method=error
            out.append({
                "gold": r["gold_validity"],
                "pred": pred,
                "subgroup": r["subgroup"],
            })
        return out

    paraphrase_accuracy = {}
    for v in ("voice", "synonym", "reorder"):
        paraphrase_accuracy[v] = _group_metrics(_records(by_variant[v]))
    paraphrase_accuracy["pooled"] = _group_metrics(_records(paraphrase_results))

    accuracy_delta = {
        "voice_minus_original":   round(paraphrase_accuracy["voice"]["accuracy"]   - orig_metrics["accuracy"], 2),
        "synonym_minus_original": round(paraphrase_accuracy["synonym"]["accuracy"] - orig_metrics["accuracy"], 2),
        "reorder_minus_original": round(paraphrase_accuracy["reorder"]["accuracy"] - orig_metrics["accuracy"], 2),
        "pooled_minus_original":  round(paraphrase_accuracy["pooled"]["accuracy"]  - orig_metrics["accuracy"], 2),
    }

    # Agreement with original
    agreement = {}
    pooled_agree, pooled_total = 0, 0
    for v in ("voice", "synonym", "reorder"):
        n_agree = n_tot = 0
        for r in by_variant[v]:
            orig = originals.get(r["original_id"])
            if orig is None:
                continue
            p_pred = r.get("prediction") if r.get("prediction") in ("VALID", "INVALID") else "INVALID"
            if orig["pred"] == p_pred:
                n_agree += 1
            n_tot += 1
        agreement[f"{v}_agreement_rate"] = round(n_agree / n_tot, 4) if n_tot else 0.0
        pooled_agree += n_agree
        pooled_total += n_tot
    agreement["pooled_agreement_rate"] = round(pooled_agree / pooled_total, 4) if pooled_total else 0.0

    # Method distribution + fallback rate
    def _method_counts(results_list):
        c = {"symbolic": 0, "fallback": 0, "error": 0}
        for r in results_list:
            m = r.get("method") or "error"
            if m not in c:
                c["error"] += 1
            else:
                c[m] += 1
        return c

    method_distribution = {
        "voice":   _method_counts(by_variant["voice"]),
        "synonym": _method_counts(by_variant["synonym"]),
        "reorder": _method_counts(by_variant["reorder"]),
        "pooled":  _method_counts(paraphrase_results),
    }

    def _rate(mc, key):
        total = sum(mc.values())
        return round(mc.get(key, 0) / total, 4) if total else 0.0

    fallback_rate = {
        "original_30": round(orig_fallback, 4),
        "voice":       _rate(method_distribution["voice"], "fallback"),
        "synonym":     _rate(method_distribution["synonym"], "fallback"),
        "reorder":     _rate(method_distribution["reorder"], "fallback"),
        "pooled":      _rate(method_distribution["pooled"], "fallback"),
    }

    extraction_failures = {
        "original_30": orig_extract_fail,
        "voice":   sum(1 for r in by_variant["voice"]   if not r.get("extraction_success")),
        "synonym": sum(1 for r in by_variant["synonym"] if not r.get("extraction_success")),
        "reorder": sum(1 for r in by_variant["reorder"] if not r.get("extraction_success")),
    }

    confusion_matrices = {
        "original_30": orig_conf,
        "voice":   _confusion(_records(by_variant["voice"])),
        "synonym": _confusion(_records(by_variant["synonym"])),
        "reorder": _confusion(_records(by_variant["reorder"])),
        "pooled":  _confusion(_records(paraphrase_results)),
    }

    # Error breakdown + novel-error counters
    error_breakdown = []
    newly_wrong = newly_right = 0
    for r in paraphrase_results:
        gold = r["gold_validity"]
        pred_para = r.get("prediction") if r.get("prediction") in ("VALID", "INVALID") else "INVALID"
        orig = originals.get(r["original_id"], {})
        pred_orig = orig.get("pred", "INVALID")

        if pred_para != gold and pred_orig == gold:
            newly_wrong += 1
        if pred_para == gold and pred_orig != gold:
            newly_right += 1

        if pred_para != gold:
            error_breakdown.append({
                "original_id": r["original_id"],
                "variant": r["variant"],
                "subgroup": r["subgroup"],
                "gold": gold,
                "pred_paraphrase": pred_para,
                "pred_original": pred_orig,
                "method": r.get("method") or "error",
                "original_method": orig.get("method", "error"),
                "same_error_as_original": (pred_orig != gold),
                "newly_introduced_by_paraphrase": (pred_orig == gold),
                "trigger_hypothesis": _classify_trigger(
                    r["variant"], r.get("method") or "error",
                    orig.get("method", "error"),
                    r.get("structure"),
                    bool(r.get("extraction_success")),
                    orig.get("structure"),
                ),
                "original_text": r["original_text"],
                "paraphrased_text": r["paraphrased_text"],
                "extracted_structure": r.get("structure"),
            })

    # Per-instance summary
    per_instance = []
    for s in sample:
        row = {
            "id": s["id"],
            "subgroup": s["subgroup"],
            "gold": s["validity"],
            "pred_original": originals[s["id"]]["pred"],
        }
        preds_para = {}
        for v in ("voice", "synonym", "reorder"):
            r = pred_lookup.get((s["id"], v))
            if r is None:
                preds_para[v] = "generation_failed"
            else:
                p = r.get("prediction")
                preds_para[v] = p if p in ("VALID", "INVALID") else "INVALID"
            row[f"pred_{v}"] = preds_para[v]
        row["all_three_agree_with_original"] = all(
            preds_para[v] == row["pred_original"] and preds_para[v] != "generation_failed"
            for v in ("voice", "synonym", "reorder")
        )
        row["how_many_correct"] = sum(
            1 for v in ("voice", "synonym", "reorder")
            if preds_para[v] == row["gold"]
        )
        per_instance.append(row)

    # Counts of generated / scored
    n_generated = 0
    gen_fail = {"voice": 0, "synonym": 0, "reorder": 0}
    for r in (json.loads(PARAPHRASES_PATH.read_text(encoding="utf-8")) if PARAPHRASES_PATH.exists() else []):
        for v in ("voice", "synonym", "reorder"):
            if r["paraphrases"].get(v):
                n_generated += 1
            else:
                gen_fail[v] += 1

    scores = {
        "n_original_instances": len(sample),
        "n_paraphrases_generated": n_generated,
        "n_paraphrases_scored": len(paraphrase_results),
        "generation_failures": gen_fail,
        "original_30_baseline": {
            "accuracy": orig_metrics["accuracy"],
            "correct": orig_metrics["correct"],
            "subgroup_accuracy": orig_metrics["subgroup_accuracy"],
            "tce": orig_metrics["tce"],
            "combined_score": orig_metrics["combined_score"],
        },
        "paraphrase_accuracy": paraphrase_accuracy,
        "accuracy_delta_pp": accuracy_delta,
        "consistency_with_original": agreement,
        "method_distribution": method_distribution,
        "fallback_rate": fallback_rate,
        "extraction_failures": extraction_failures,
        "confusion_matrices": confusion_matrices,
        "error_breakdown": error_breakdown,
        "instances_newly_wrong_due_to_paraphrase": newly_wrong,
        "instances_newly_right_due_to_paraphrase": newly_right,
        "per_instance_summary": per_instance,
    }

    with open(SCORES_PATH, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2)
    print(f"Saved {SCORES_PATH}")
    return scores


# --- Step 5: Summary print ---------------------------------------------------
def step5_print(scores):
    o = scores["original_30_baseline"]
    p = scores["paraphrase_accuracy"]
    d = scores["accuracy_delta_pp"]
    a = scores["consistency_with_original"]
    md_p = scores["method_distribution"]["pooled"]
    cf_p = scores["confusion_matrices"]["pooled"]
    triggers = Counter(e["trigger_hypothesis"] for e in scores["error_breakdown"])

    total_pool = sum(md_p.values())
    print()
    print("=" * 66)
    print(f"PARAPHRASE PROBE SUMMARY (n={scores['n_original_instances']} originals, "
          f"up to {3 * scores['n_original_instances']} paraphrases)")
    print("=" * 66)
    print()
    print("Original-30 baseline:")
    print(f"  Accuracy: {o['accuracy']:.2f}%  ({o['correct']}/{scores['n_original_instances']})")
    print(f"  TCE: {o['tce']:.2f}   Combined: {o['combined_score']:.2f}")
    print(f"  Fallback rate: {scores['fallback_rate']['original_30']*100:.1f}%  "
          f"Extraction failures: {scores['extraction_failures']['original_30']}")
    print()
    print("Paraphrase accuracy by variant:")
    for v in ("voice", "synonym", "reorder"):
        pv = p[v]; dv = d[f"{v}_minus_original"]
        sign = "+" if dv >= 0 else ""
        print(f"  {v:<9}{pv['accuracy']:6.2f}% ({pv['correct']}/{pv['n']})   delta = {sign}{dv:.2f} pp")
    pp = p["pooled"]; dp = d["pooled_minus_original"]
    sign = "+" if dp >= 0 else ""
    print(f"  POOLED:  {pp['accuracy']:6.2f}% ({pp['correct']}/{pp['n']})   delta = {sign}{dp:.2f} pp  <-- TBD_PP_DELTA")
    print()
    print("Agreement with original (prediction stability):")
    for v in ("voice", "synonym", "reorder"):
        print(f"  {v:<9}{a[f'{v}_agreement_rate']*100:5.1f}%")
    print(f"  POOLED:  {a['pooled_agreement_rate']*100:5.1f}%")
    print()
    print("Method distribution on paraphrases:")
    print(f"  symbolic: {md_p.get('symbolic',0)}/{total_pool}  "
          f"fallback: {md_p.get('fallback',0)}/{total_pool}  "
          f"error: {md_p.get('error',0)}/{total_pool}")
    print()
    print(f"Newly wrong (original correct, paraphrase wrong): {scores['instances_newly_wrong_due_to_paraphrase']}")
    print(f"Newly right (original wrong, paraphrase correct): {scores['instances_newly_right_due_to_paraphrase']}")
    print()
    print("Per-variant confusion (pooled):")
    print(f"  V->V: {cf_p['V->V']}  V->I: {cf_p['V->I']}  I->V: {cf_p['I->V']}  I->I: {cf_p['I->I']}")
    print()
    print("Top error triggers (from error_breakdown):")
    for key in ("extraction failure", "middle-term surface form changed", "E/O confusion",
                "fallback judgement", "other"):
        print(f"  {key:<34}{triggers.get(key, 0)}")
    print()
    print("=" * 66)
    print(f"FOR §5.5 IN THE PAPER: accuracy_delta_pp (pooled) = {dp:+.2f}")
    print("=" * 66)


# --- Main --------------------------------------------------------------------
def main():
    sample = step1_sample()
    paraphrases = step2_paraphrases(sample)

    # Sanity: require at least some paraphrases before burning pipeline calls
    total_para = sum(sum(1 for v in r["paraphrases"].values() if v) for r in paraphrases)
    if total_para == 0:
        print("ERROR: zero paraphrases generated; aborting before Qwen calls.")
        sys.exit(2)

    results = step3_run_pipeline(paraphrases)
    scores = step4_metrics(results, sample)
    step5_print(scores)


if __name__ == "__main__":
    main()
