"""
Score baseline prediction JSONs against gold labels.

Metrics (must reproduce the paper's 96.34 / 1.02 / 56.57 on the submitted system):
  - Accuracy: correct / total, in percent
  - TCE: mean of |acc(VP) - acc(VI)| and |acc(IP) - acc(II)|, in percentage points
  - Combined Score: accuracy / (1 + ln(1 + tce))
"""

import argparse
import json
import math
import os
import sys

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_GOLD = os.path.join(
    REPO_ROOT,
    "board_results",
    "56_57",
    "neurosymbolic_test_simplified_20260203_092505",
    "test_data_subtask_1.json",
)


def _bool_to_valid(b):
    return "VALID" if b else "INVALID"


def score(predictions_path, gold_path, out_path=None, label=None):
    with open(gold_path, "r", encoding="utf-8") as f:
        gold_items = json.load(f)
    with open(predictions_path, "r", encoding="utf-8") as f:
        pred_items = json.load(f)

    gold_by_id = {item["id"]: item for item in gold_items}
    pred_by_id = {item["id"]: item for item in pred_items}

    total = 0
    correct = 0
    n_parse_errors = 0
    confusion = {"V->V": 0, "V->I": 0, "I->V": 0, "I->I": 0}
    groups = {"VP": [], "VI": [], "IP": [], "II": []}

    for gid, gitem in gold_by_id.items():
        if gid not in pred_by_id:
            continue
        p = pred_by_id[gid]
        gold = _bool_to_valid(gitem["validity"])
        pred = p.get("prediction", "INVALID")
        if pred not in ("VALID", "INVALID"):
            pred = "INVALID"
        if p.get("flagged"):
            n_parse_errors += 1

        total += 1
        is_correct = (pred == gold)
        if is_correct:
            correct += 1

        gk = "V" if gold == "VALID" else "I"
        pk = "V" if pred == "VALID" else "I"
        confusion[f"{gk}->{pk}"] += 1

        plaus = "P" if gitem["plausibility"] else "I"
        vkey = "V" if gitem["validity"] else "I"
        groups[vkey + plaus].append(is_correct)

    accuracy = correct / total * 100 if total else 0.0

    def acc(lst):
        return (sum(lst) / len(lst) * 100) if lst else 0.0

    acc_vp = acc(groups["VP"])
    acc_vi = acc(groups["VI"])
    acc_ip = acc(groups["IP"])
    acc_ii = acc(groups["II"])

    tce = (abs(acc_vp - acc_vi) + abs(acc_ip - acc_ii)) / 2
    combined = accuracy / (1 + math.log(1 + tce))

    result = {
        "label": label or os.path.basename(predictions_path),
        "accuracy": round(accuracy, 2),
        "tce": round(tce, 2),
        "combined": round(combined, 2),
        "confusion": confusion,
        "subgroup_accuracy": {
            "VP": round(acc_vp, 2),
            "VI": round(acc_vi, 2),
            "IP": round(acc_ip, 2),
            "II": round(acc_ii, 2),
        },
        "subgroup_counts": {k: len(v) for k, v in groups.items()},
        "n_parse_errors": n_parse_errors,
        "total_scored": total,
    }

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

    return result


def print_row(label, r):
    print(f"{label:<22}{r['accuracy']:>6.2f}  {r['tce']:>5.2f}  {r['combined']:>6.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", required=False, help="Path to out_bX.json (if scoring one)")
    ap.add_argument("--gold", default=DEFAULT_GOLD)
    ap.add_argument("--out", default=None)
    ap.add_argument("--label", default=None)
    ap.add_argument("--all", action="store_true", help="Score out_b1/b2/b3.json together and print Table 4.")
    args = ap.parse_args()

    if args.all:
        labels = [
            ("B1: Direct prompt",   "out_b1.json", "scores_b1.json"),
            ("B2: Chain-of-thought","out_b2.json", "scores_b2.json"),
            ("B3: CoT + SC (k=4)",  "out_b3.json", "scores_b3.json"),
        ]
        results = []
        for lab, pred_fname, scores_fname in labels:
            pred_path = os.path.join(REPO_ROOT, pred_fname)
            scores_path = os.path.join(REPO_ROOT, scores_fname)
            if not os.path.exists(pred_path):
                print(f"Missing: {pred_path}", file=sys.stderr)
                continue
            r = score(pred_path, args.gold, out_path=scores_path, label=lab)
            results.append((lab, r))

        print()
        print("=" * 60)
        print("FOR TABLE 4 IN THE PAPER")
        print("=" * 60)
        print(f"{'System':<22}{'Acc.':>6}  {'TCE':>5}  {'Score':>6}")
        for lab, r in results:
            print_row(lab, r)
        return

    if not args.predictions:
        ap.error("--predictions is required when --all is not set")
    r = score(args.predictions, args.gold, out_path=args.out, label=args.label)
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
