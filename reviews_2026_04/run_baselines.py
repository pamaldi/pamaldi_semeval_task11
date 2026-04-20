"""
Run three pure-LLM baselines (B1, B2, B3) against the 191-instance test set
from SemEval-2026 Task 11 Subtask 1, using Qwen3-32B on Bedrock.

Uses BedrockClientBearer (the client the submitted pipeline actually imports via
`from bedrock_client_bearer import BedrockClientBearer as BedrockClient`), which
already supports Qwen3-32B and max_tokens.
"""

import argparse
import json
import os
import re
import sys
import time
from collections import Counter

# Ensure we can import the project modules
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO_ROOT)

from load_credentials import load_credentials_from_file
from bedrock_client_bearer import BedrockClientBearer as BedrockClient


TEST_PATH = os.path.join(
    REPO_ROOT,
    "board_results",
    "56_57",
    "neurosymbolic_test_simplified_20260203_092505",
    "test_data_subtask_1.json",
)

MODEL_ID = "qwen.qwen3-32b-v1:0"
PROGRESS_EVERY = 20
SLEEP_BETWEEN_CALLS = 0.2


def parse_answer(text):
    """Last-occurrence, case-insensitive, word-boundary match of VALID/INVALID.

    Returns 'VALID', 'INVALID', or None if neither is found.
    Matches INVALID first to avoid it being swallowed by a VALID match inside it.
    """
    if not text:
        return None
    up = text.upper()
    # Find all INVALID matches
    invalid_matches = list(re.finditer(r"\bINVALID\b", up))
    # Find VALID matches that are not part of INVALID (i.e., not preceded by IN)
    valid_matches = []
    for m in re.finditer(r"\bVALID\b", up):
        s = m.start()
        if s >= 2 and up[s - 2:s] == "IN":
            continue
        valid_matches.append(m)
    last_invalid = invalid_matches[-1].start() if invalid_matches else -1
    last_valid = valid_matches[-1].start() if valid_matches else -1
    if last_invalid == -1 and last_valid == -1:
        return None
    return "INVALID" if last_invalid > last_valid else "VALID"


def call_bedrock(bedrock_client, prompt, temperature, max_tokens):
    """Call Qwen3-32B with retry (3 attempts, 1/2/4s backoff).

    Returns (response_text, error). error is None on success.
    """
    last_err = None
    for attempt in range(3):
        try:
            text = bedrock_client.generate(
                prompt=prompt,
                temperature=float(temperature),
                max_tokens=int(max_tokens),
            )
            return text, None
        except Exception as e:
            last_err = e
            if attempt < 2:
                delay = 1 * (2 ** attempt)
                time.sleep(delay)
            else:
                return None, str(e)
    return None, str(last_err)


def _load_existing(out_path):
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def run_b1(bedrock_client, test_items, out_path):
    """B1: Direct prompt, t=0.0, max_tokens=16, 1 sample."""
    results = _load_existing(out_path)
    done_ids = {r["id"] for r in results}
    if done_ids:
        print(f"[B1] Resuming: {len(done_ids)} already done.", flush=True)
    start = time.time()
    for i, item in enumerate(test_items, 1):
        if item["id"] in done_ids:
            continue
        prompt = (
            f"Is the following syllogism valid? "
            f"Answer only VALID or INVALID.\n\n{item['syllogism']}"
        )
        text, err = call_bedrock(bedrock_client, prompt, temperature=0.0, max_tokens=16)
        if err is not None:
            results.append({
                "id": item["id"],
                "syllogism": item["syllogism"],
                "prediction": "INVALID",
                "raw_response": "EXCEPTION",
                "error": err,
                "flagged": True,
            })
            last_pred = "ERR"
        else:
            pred = parse_answer(text)
            flagged = pred is None
            results.append({
                "id": item["id"],
                "syllogism": item["syllogism"],
                "prediction": pred if pred is not None else "INVALID",
                "raw_response": text,
                "flagged": flagged,
            })
            last_pred = pred if pred is not None else "PARSE_ERR"
        if i % PROGRESS_EVERY == 0 or i == len(test_items):
            elapsed = int(time.time() - start)
            print(f"[B1 {i}/{len(test_items)}]  elapsed={elapsed}s  last_pred={last_pred}", flush=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
        time.sleep(SLEEP_BETWEEN_CALLS)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    return results


def run_b2(bedrock_client, test_items, out_path):
    """B2: CoT, t=0.3, max_tokens=512, 1 sample."""
    results = _load_existing(out_path)
    done_ids = {r["id"] for r in results}
    if done_ids:
        print(f"[B2] Resuming: {len(done_ids)} already done.", flush=True)
    start = time.time()
    for i, item in enumerate(test_items, 1):
        if item["id"] in done_ids:
            continue
        prompt = (
            f"Is the following syllogism valid? Think step by step, then on the "
            f"last line answer only VALID or INVALID.\n\n{item['syllogism']}"
        )
        text, err = call_bedrock(bedrock_client, prompt, temperature=0.3, max_tokens=512)
        if err is not None:
            results.append({
                "id": item["id"],
                "syllogism": item["syllogism"],
                "prediction": "INVALID",
                "raw_response": "EXCEPTION",
                "error": err,
                "flagged": True,
            })
            last_pred = "ERR"
        else:
            pred = parse_answer(text)
            flagged = pred is None
            results.append({
                "id": item["id"],
                "syllogism": item["syllogism"],
                "prediction": pred if pred is not None else "INVALID",
                "raw_response": text,
                "flagged": flagged,
            })
            last_pred = pred if pred is not None else "PARSE_ERR"
        if i % PROGRESS_EVERY == 0 or i == len(test_items):
            elapsed = int(time.time() - start)
            print(f"[B2 {i}/{len(test_items)}]  elapsed={elapsed}s  last_pred={last_pred}", flush=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
        time.sleep(SLEEP_BETWEEN_CALLS)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    return results


def run_b3(bedrock_client, test_items, out_path):
    """B3: CoT + self-consistency k=4 at temperatures [0.0, 0.3, 0.5, 0.7]."""
    temperatures = [0.0, 0.3, 0.5, 0.7]
    results = _load_existing(out_path)
    done_ids = {r["id"] for r in results}
    if done_ids:
        print(f"[B3] Resuming: {len(done_ids)} already done.", flush=True)
    start = time.time()
    for i, item in enumerate(test_items, 1):
        if item["id"] in done_ids:
            continue
        prompt = (
            f"Is the following syllogism valid? Think step by step, then on the "
            f"last line answer only VALID or INVALID.\n\n{item['syllogism']}"
        )
        per_sample = []
        votes = []
        had_exception = False
        for t in temperatures:
            text, err = call_bedrock(bedrock_client, prompt, temperature=t, max_tokens=512)
            if err is not None:
                per_sample.append({
                    "temperature": t,
                    "prediction": "INVALID",
                    "raw_response": "EXCEPTION",
                    "error": err,
                    "flagged": True,
                })
                votes.append("INVALID")
                had_exception = True
            else:
                pred = parse_answer(text)
                flagged = pred is None
                final_pred = pred if pred is not None else "INVALID"
                per_sample.append({
                    "temperature": t,
                    "prediction": final_pred,
                    "raw_response": text,
                    "flagged": flagged,
                })
                votes.append(final_pred)
            time.sleep(SLEEP_BETWEEN_CALLS)

        # Majority vote; tie-break = temperature-0.0 sample (first in list)
        c = Counter(votes)
        valid_count = c.get("VALID", 0)
        invalid_count = c.get("INVALID", 0)
        if valid_count > invalid_count:
            final = "VALID"
        elif invalid_count > valid_count:
            final = "INVALID"
        else:
            final = per_sample[0]["prediction"]  # temperature=0.0 sample

        # Instance flagged if any sample was an exception, or any sample was unparseable
        any_flagged = any(s.get("flagged") for s in per_sample) or had_exception

        results.append({
            "id": item["id"],
            "syllogism": item["syllogism"],
            "prediction": final,
            "raw_response": None,
            "per_sample": per_sample,
            "vote_counts": {"VALID": valid_count, "INVALID": invalid_count},
            "flagged": any_flagged,
        })
        if i % PROGRESS_EVERY == 0 or i == len(test_items):
            elapsed = int(time.time() - start)
            print(f"[B3 {i}/{len(test_items)}]  elapsed={elapsed}s  last_pred={final}", flush=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--baseline",
        choices=["b1", "b2", "b3", "all"],
        default="all",
        help="Which baseline(s) to run.",
    )
    ap.add_argument("--limit", type=int, default=None, help="Limit # instances (for smoke tests).")
    ap.add_argument("--creds", default=os.path.join(REPO_ROOT, "aws_credentials.txt"))
    args = ap.parse_args()

    # Load creds (only sets environment variables; nothing is written to disk)
    load_credentials_from_file(args.creds)

    # Instantiate the shared client
    client = BedrockClient(model_id=MODEL_ID)

    with open(TEST_PATH, "r", encoding="utf-8") as f:
        test_items = json.load(f)
    if args.limit is not None:
        test_items = test_items[: args.limit]
    print(f"Loaded {len(test_items)} test items.", flush=True)

    if args.baseline in ("b1", "all"):
        print("\n=== Running B1: Direct prompt ===", flush=True)
        run_b1(client, test_items, os.path.join(REPO_ROOT, "out_b1.json"))
    if args.baseline in ("b2", "all"):
        print("\n=== Running B2: Chain-of-thought ===", flush=True)
        run_b2(client, test_items, os.path.join(REPO_ROOT, "out_b2.json"))
    if args.baseline in ("b3", "all"):
        print("\n=== Running B3: CoT + self-consistency k=4 ===", flush=True)
        run_b3(client, test_items, os.path.join(REPO_ROOT, "out_b3.json"))

    print("\nDone.", flush=True)


if __name__ == "__main__":
    main()
