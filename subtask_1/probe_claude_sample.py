"""
Probe: does a Claude model judge syllogistic *validity* correctly on the two
hardest content-effect conditions?

Samples 10 instances from the test set:
  - 5 VALID + IMPLAUSIBLE   (validity=True,  plausibility=False)
  - 5 INVALID + PLAUSIBLE   (validity=False, plausibility=True)

These are exactly the cells where the "content effect" bites: a content-biased
reasoner rejects valid-but-absurd arguments and accepts invalid-but-believable
ones. Reasoning is DISABLED, so the model answers from immediate judgment —
this is where the content bias shows up most clearly.

Usage (PowerShell):
    # put your key in a .env file next to this script (or in the repo root):
    #   ANTHROPIC_API_KEY=sk-ant-...
    python probe_claude_sample.py
    # optional overrides:
    python probe_claude_sample.py --model claude-opus-4-8 --seed 42

The key is read from a .env file (ANTHROPIC_API_KEY). It is never printed.

Requires: pip install anthropic
"""

import argparse
import json
import os
import sys
from pathlib import Path


def load_env():
    """Minimal .env loader (no external dependency).

    Reads KEY=VALUE lines from a .env file located next to this script or in
    the repo root, and sets them in os.environ without overriding existing vars.
    """
    candidates = [
        Path(__file__).parent / ".env",
        Path(__file__).parent.parent / ".env",
        Path.cwd() / ".env",
    ]
    for env_path in candidates:
        if not env_path.is_file():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


load_env()

from pydantic import BaseModel, Field

import anthropic

DATA_PATH = Path(__file__).parent / "data" / "test_data_subtask_1.json"

SYSTEM_PROMPT = """You are an expert in Aristotelian term logic.

You will be given a categorical syllogism in English: two premises and a \
conclusion. Judge ONLY its FORMAL VALIDITY — whether the conclusion follows \
necessarily from the premises by logical form alone.

Crucial: validity is independent of whether the statements are factually true \
or plausible in the real world. A syllogism can be valid even if its premises \
or conclusion are absurd, and invalid even if everything sounds believable. \
Judge the form, not the content.

Use the classical interpretation with existential import (the 24 valid forms)."""


class Verdict(BaseModel):
    valid: bool = Field(
        description="True if the syllogism is formally valid, False otherwise."
    )
    reason: str = Field(
        description="One short sentence: the deciding rule or form (e.g. 'Datisi AII-3, valid')."
    )


class VerdictSnap(BaseModel):
    """Snap-judgment schema: only the boolean, no room to reason in the output."""

    valid: bool = Field(
        description="True if the syllogism is formally valid, False otherwise."
    )


def cond_of(case) -> str:
    """Map (validity, plausibility) to a condition code VP / VI / IP / II."""
    v = "V" if case["validity"] else "I"
    p = "P" if case["plausibility"] else "I"
    return v + p


def load_cases(seed: int, conditions, per_group):
    """Return a list of (cond, case) tuples for the requested conditions.

    conditions: list of condition codes to include (e.g. ["VI", "IP"] or all 4).
    per_group: number of instances per condition, or None for all of them.
    """
    import random

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    rng = random.Random(seed)

    cases = []
    for cond in conditions:
        group = [d for d in data if cond_of(d) == cond]
        rng.shuffle(group)
        if per_group is not None:
            if len(group) < per_group:
                sys.exit(f"Not enough instances for {cond}: have {len(group)}")
            group = group[:per_group]
        cases.extend((cond, c) for c in group)

    return cases


def judge(client: anthropic.Anthropic, model: str, syllogism: str, snap: bool):
    # snap=True forces an immediate boolean with no `reason` field, so the model
    # cannot work through the form in its output — this is where the content
    # effect shows up most. snap=False keeps a one-line justification.
    response = client.messages.parse(
        model=model,
        max_tokens=64 if snap else 1024,
        # Reasoning disabled (no `thinking` param) — immediate judgment. On
        # Opus 4.8, omitting `thinking` runs the model without extended reasoning.
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Syllogism:\n\n{syllogism}"}],
        output_format=VerdictSnap if snap else Verdict,
    )
    return response.parsed_output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="claude-opus-4-8", help="Claude model id")
    parser.add_argument("--seed", type=int, default=42, help="sampling seed")
    parser.add_argument(
        "--snap",
        action="store_true",
        help="snap judgment: boolean only, no reason field (elicits content effect)",
    )
    parser.add_argument(
        "--all",
        dest="all_instances",
        action="store_true",
        help="use ALL instances per condition instead of --n",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="run all 4 conditions (VP, VI, IP, II) over the whole test set and report TCE",
    )
    parser.add_argument(
        "--n", type=int, default=5, help="instances per condition (ignored with --all/--full)"
    )
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY not found. Add it to a .env file next to this script.")

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    conditions = ["VP", "VI", "IP", "II"] if args.full else ["VI", "IP"]
    per_group = None if (args.all_instances or args.full) else args.n
    cases = load_cases(args.seed, conditions, per_group)

    mode = "snap (boolean only)" if args.snap else "with one-line reason"
    print(
        f"Model: {args.model}  |  seed: {args.seed}  |  mode: {mode}  |  n={len(cases)}"
    )
    print("=" * 78)

    LABELS = {
        "VP": "valid+plausible",
        "VI": "valid+implausible",
        "IP": "invalid+plausible",
        "II": "invalid+implausible",
    }
    per_cond = {c: [0, 0] for c in conditions}  # [correct, total]
    false_valid = 0    # pred valid, gold invalid
    false_invalid = 0  # pred invalid, gold valid

    for cond, case in cases:
        gold = case["validity"]
        try:
            verdict = judge(client, args.model, case["syllogism"], args.snap)
        except anthropic.APIError as e:
            print(f"[{cond}] API error: {e}")
            continue

        ok = verdict.valid == gold
        per_cond[cond][0] += ok
        per_cond[cond][1] += 1
        if not ok:
            if verdict.valid and not gold:
                false_valid += 1
            elif not verdict.valid and gold:
                false_invalid += 1

        mark = "OK " if ok else "XX "
        reason = getattr(verdict, "reason", "")
        line = (
            f"{mark}[{cond}] gold={'valid' if gold else 'invalid':7} "
            f"pred={'valid' if verdict.valid else 'invalid':7}"
        )
        if reason:
            line += f" | {reason}"
        print(line)
        print(f"        {case['syllogism']}")

    correct = sum(c for c, _ in per_cond.values())
    total = sum(t for _, t in per_cond.values())
    print("=" * 78)
    if not total:
        print("No results")
        return

    print(f"Overall accuracy: {correct}/{total} = {correct / total:.2%}")
    for cond in conditions:
        c, t = per_cond[cond]
        if t:
            print(f"  {cond} ({LABELS[cond]}): {c}/{t} = {c / t:.2%}")

    # Content effect = |acc(plausible) - acc(implausible)|, pooled over conditions,
    # in percentage points (matches lib/evaluation.py).
    plaus_c = sum(per_cond[c][0] for c in ("VP", "IP") if c in per_cond)
    plaus_t = sum(per_cond[c][1] for c in ("VP", "IP") if c in per_cond)
    impl_c = sum(per_cond[c][0] for c in ("VI", "II") if c in per_cond)
    impl_t = sum(per_cond[c][1] for c in ("VI", "II") if c in per_cond)

    print(f"\nFalse-valid (accept invalid):   {false_valid}")
    print(f"False-invalid (reject valid):   {false_invalid}")

    if plaus_t and impl_t:
        plaus_acc = plaus_c / plaus_t
        impl_acc = impl_c / impl_t
        tce = abs(plaus_acc - impl_acc) * 100
        print(f"\nPlausible accuracy:   {plaus_acc:.2%} (n={plaus_t})")
        print(f"Implausible accuracy: {impl_acc:.2%} (n={impl_t})")
        print(f"Total Content Effect (TCE): {tce:.2f}")
        if not args.full:
            print("(note: TCE here uses only VI+IP — run --full for the paper-comparable value)")


if __name__ == "__main__":
    main()
