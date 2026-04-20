"""
Run the full neuro-symbolic pipeline on the 191 test instances using
Claude Sonnet 4.5 (Anthropic API) as the extractor LLM.

The symbolic validator, post-processing rules, and fallback handler are
UNCHANGED — only the LLM client changes. This produces one row of Table 6.

Reads ANTHROPIC_API_KEY from the repo-root .env via python-dotenv. Never
prints the key. Writes per-instance JSONs to logs/multimodel_claude/ in the
same schema as board_results/56_57/.../logs/.
"""

import json
import os
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

# --- Credentials: load .env (never echo the key) -----------------------------
try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: python-dotenv not installed. Run: pip install python-dotenv")
    sys.exit(1)

ENV_PATH = REPO_ROOT / ".env"
if not ENV_PATH.exists():
    print(f"ERROR: {ENV_PATH} not found. Aborting.")
    sys.exit(1)

# override=True because the shell may have a pre-set empty ANTHROPIC_API_KEY
load_dotenv(dotenv_path=ENV_PATH, override=True)
if not os.environ.get("ANTHROPIC_API_KEY"):
    print("ERROR: ANTHROPIC_API_KEY not set after loading .env. Aborting.")
    sys.exit(1)

# --- Imports: use the lib/ copy of the pipeline used by the submitted run ----
LIB_PATH = REPO_ROOT / "pamaldi_semeval_2026_11_task1" / "lib"
if not LIB_PATH.exists():
    print(f"ERROR: lib path not found: {LIB_PATH}")
    sys.exit(1)
sys.path.insert(0, str(LIB_PATH))

from anthropic_client import AnthropicClient  # noqa: E402
from neurosymbolic_pipeline import NeuroSymbolicPipeline  # noqa: E402


# --- Configuration -----------------------------------------------------------
MODEL_ID = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 4096  # match the Bedrock default used by the submitted run

# Exactly the submitted-run PIPELINE_CONFIG
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

# Where per-instance JSONs should land (flat, matches task spec)
FLAT_LOGS_DIR = REPO_ROOT / "logs" / "multimodel_claude"

OUT_AGGREGATED = REPO_ROOT / "out_multimodel_claude.json"


def _to_ground_truth(item):
    v = item.get("validity")
    if isinstance(v, bool):
        return "VALID" if v else "INVALID"
    return v


def _to_plausibility(item):
    p = item.get("plausibility")
    if isinstance(p, bool):
        return "PLAUSIBLE" if p else "IMPLAUSIBLE"
    return p


def main():
    # Load test data
    with open(TEST_DATA_PATH, "r", encoding="utf-8") as f:
        test_items = json.load(f)
    n_total = len(test_items)
    print(f"Loaded {n_total} test items.", flush=True)

    # Prepare client (1s, 2s, 4s backoff; 3 retries)
    client = AnthropicClient(
        model_id=MODEL_ID,
        max_retries=3,
        base_delay=1.0,
        timeout=120,
        max_tokens=MAX_TOKENS,
    )

    # Initialize the pipeline (creates its own timestamped logs folder under logs/)
    pipeline = NeuroSymbolicPipeline(
        bedrock_client=client,  # duck-typed — AnthropicClient exposes generate()
        results_dir=str(REPO_ROOT / "logs"),
        run_name="multimodel_claude",
        **PIPELINE_CONFIG,
    )
    print(f"Pipeline logs_dir: {pipeline.logs_dir}", flush=True)

    # Prepare the flat target dir that the task specifies
    FLAT_LOGS_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    start = time.time()

    for i, item in enumerate(test_items, 1):
        syllogism_text = item.get("syllogism") or item.get("text") or ""
        syllogism_id = item["id"]

        try:
            result = pipeline.process_syllogism(syllogism_text, syllogism_id)
        except Exception as e:
            # AnthropicClient already retried 3x; record and move on.
            # Keep the exception message but never the API key (keys don't appear
            # in Anthropic SDK error messages, but we strip defensively).
            err_msg = str(e).replace(os.environ.get("ANTHROPIC_API_KEY", ""), "[REDACTED]")
            result = {
                "id": syllogism_id,
                "text": syllogism_text,
                "extraction_success": False,
                "validity": None,
                "prediction": "INVALID",  # conservative default
                "method": "error",
                "confidence": 0.0,
                "error": err_msg,
                "structure": None,
                "validity_details": None,
                "extraction_attempts": 1,
                "self_consistency": None,
                "fallback_info": None,
            }

        # Attach ground truth + plausibility (same as pipeline.run() does)
        gt = _to_ground_truth(item)
        if gt is not None:
            result["ground_truth"] = gt
        plaus = _to_plausibility(item)
        if plaus is not None:
            result["plausibility"] = plaus

        # Save per-instance log inside the pipeline's logs_dir (its native format)
        pipeline._save_log(result)

        # Mirror to the flat logs/multimodel_claude/ path the task asks for
        flat_path = FLAT_LOGS_DIR / f"{syllogism_id}.json"
        with open(flat_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        results.append(result)

        elapsed = int(time.time() - start)
        method = result.get("method") or "error"
        pred = result.get("prediction") or "NONE"
        print(f"[{i}/{n_total}] elapsed={elapsed}s method={method} pred={pred}", flush=True)

        # Intermediate aggregated dump every 20 instances (task spec)
        if i % 20 == 0 or i == n_total:
            with open(OUT_AGGREGATED, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)

    # Final dump
    with open(OUT_AGGREGATED, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # Tally
    method_counts = {"symbolic": 0, "fallback": 0, "error": 0, "none": 0}
    for r in results:
        m = r.get("method") or "none"
        method_counts[m] = method_counts.get(m, 0) + 1
    print(f"\nDone. method_counts={method_counts}", flush=True)
    print(f"Per-instance logs (flat): {FLAT_LOGS_DIR}", flush=True)
    print(f"Aggregated: {OUT_AGGREGATED}", flush=True)
    print(f"Pipeline logs dir: {pipeline.logs_dir}", flush=True)


if __name__ == "__main__":
    main()
