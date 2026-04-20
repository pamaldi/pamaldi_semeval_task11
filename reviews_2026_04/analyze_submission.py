#!/usr/bin/env python3
"""
analyze_submission.py

End-to-end analysis for the camera-ready paper.
Joins:
  - Folder of 191 prediction files (one JSON per test instance)
  - Gold labels JSON (list of {id, validity, plausibility, syllogism})

Produces:
  1. Overall accuracy & confusion breakdown
  2. Path-level (symbolic vs fallback) accuracy and TCE   [§5.2]
  3. Subgroup distribution of errors (VP/VI/IP/II)        [§5 sanity check]
  4. Per-error detail table with gold/pred forms          [Table 9 / Appendix C]
  5. TCE decomposition (symbolic path vs fallback path)   [R1-Q5 answer]

Usage:
    python analyze_submission.py predictions_folder/ gold_labels.json

Prints a report to stdout and saves:
    errors_detailed.json     — full error records
    paper_numbers.txt         — ready-to-paste values for the .tex
"""

import sys
import json
from pathlib import Path
from collections import Counter, defaultdict


# -------- I/O helpers -------------------------------------------------------

def load_predictions(folder):
    """Load all .json files from a folder. One record per file."""
    records = []
    for f in sorted(Path(folder).glob("*.json")):
        with open(f) as fh:
            records.append(json.load(fh))
    return records


def load_gold(path):
    """Load gold labels file (list of dicts)."""
    with open(path) as f:
        return json.load(f)


def norm(v):
    """Normalize any truthy/label value to 'VALID' or 'INVALID'."""
    if isinstance(v, bool):
        return "VALID" if v else "INVALID"
    if isinstance(v, str):
        s = v.upper().strip()
        if s in ("VALID", "TRUE", "T", "1"): return "VALID"
        if s in ("INVALID", "FALSE", "F", "0"): return "INVALID"
        return s
    raise ValueError(f"unexpected value: {v!r}")


def plaus_str(v):
    """Normalize plausibility to 'PLAUSIBLE'/'IMPLAUSIBLE'."""
    if isinstance(v, bool):
        return "PLAUSIBLE" if v else "IMPLAUSIBLE"
    if isinstance(v, str):
        return v.upper().strip()
    return "?"


def subgroup_of(gold_valid, plausible):
    v = "V" if gold_valid == "VALID" else "I"
    p = "P" if plausible == "PLAUSIBLE" else ("I" if plausible == "IMPLAUSIBLE" else "?")
    return f"{v}{p}"


# -------- TCE (Total Content Effect) ---------------------------------------
# TCE = mean absolute accuracy gap between plausible and implausible,
#       averaged across valid and invalid conditions.
# TCE = ( |acc(VP) - acc(VI)| + |acc(IP) - acc(II)| ) / 2
# Expressed in percentage points. Lower is better.

def compute_tce(subgroup_correct, subgroup_total):
    """Compute TCE given per-subgroup counts (correct, total) dicts."""
    def acc(key):
        t = subgroup_total.get(key, 0)
        if t == 0: return None
        return 100.0 * subgroup_correct.get(key, 0) / t

    v_gap = i_gap = None
    accs = {k: acc(k) for k in ("VP", "VI", "IP", "II")}

    if accs["VP"] is not None and accs["VI"] is not None:
        v_gap = abs(accs["VP"] - accs["VI"])
    if accs["IP"] is not None and accs["II"] is not None:
        i_gap = abs(accs["IP"] - accs["II"])

    parts = [g for g in (v_gap, i_gap) if g is not None]
    tce = sum(parts) / len(parts) if parts else None
    return tce, accs


def combined_score(acc_pct, tce):
    """Primary SemEval ranking metric."""
    import math
    if acc_pct is None or tce is None:
        return None
    return acc_pct / (1.0 + math.log(1.0 + tce))


# -------- Main analysis ----------------------------------------------------

def main(pred_folder, gold_path):
    preds_raw = load_predictions(pred_folder)
    gold_raw = load_gold(gold_path)

    print(f"Loaded {len(preds_raw)} prediction files from {pred_folder}")
    print(f"Loaded {len(gold_raw)} gold records from {gold_path}")
    print()

    # Index by id
    preds = {r["id"]: r for r in preds_raw}
    gold = {r["id"]: r for r in gold_raw}

    common = sorted(set(preds) & set(gold))
    missing_pred = set(gold) - set(preds)
    missing_gold = set(preds) - set(gold)
    if missing_pred:
        print(f"WARNING: {len(missing_pred)} gold IDs have no prediction")
    if missing_gold:
        print(f"WARNING: {len(missing_gold)} prediction IDs not in gold")
    print(f"Matched: {len(common)} instances.\n")

    # -------- Build joined records ----------------------------------------
    joined = []
    for uid in common:
        p = preds[uid]
        g = gold[uid]
        gold_label = norm(g["validity"])
        pred_label = norm(p["prediction"])
        plaus = plaus_str(g.get("plausibility"))
        sub = subgroup_of(gold_label, plaus)
        method = p.get("method", "unknown")
        struct = p.get("structure") or {}
        form = struct.get("form", "extraction_failed")
        vdet = p.get("validity_details") or {}
        form_name = vdet.get("form_name")
        joined.append({
            "id": uid,
            "gold": gold_label,
            "pred": pred_label,
            "correct": gold_label == pred_label,
            "plausibility": plaus,
            "subgroup": sub,
            "method": method,
            "pred_form": form,
            "pred_form_name": form_name,
            "syllogism": g.get("syllogism", ""),
            "extraction_success": p.get("extraction_success", None),
            "error": p.get("error"),
            "structure": struct,
        })

    # -------- 1. Overall metrics ------------------------------------------
    n = len(joined)
    n_correct = sum(1 for r in joined if r["correct"])
    acc = 100.0 * n_correct / n
    method_counts = Counter(r["method"] for r in joined)

    print("=" * 78)
    print("1. OVERALL METRICS")
    print("=" * 78)
    print(f"  Total:   {n}")
    print(f"  Correct: {n_correct}")
    print(f"  Errors:  {n - n_correct}")
    print(f"  Accuracy: {acc:.2f}%")
    print(f"  Methods: {dict(method_counts)}")
    print()

    # -------- 2. Subgroup accuracy & overall TCE --------------------------
    sg_total = Counter(r["subgroup"] for r in joined)
    sg_correct = Counter(r["subgroup"] for r in joined if r["correct"])
    tce_overall, accs = compute_tce(sg_correct, sg_total)
    combined = combined_score(acc, tce_overall)

    print("=" * 78)
    print("2. SUBGROUP ACCURACY  [for Table 3 in paper]")
    print("=" * 78)
    for k in ("VP", "VI", "IP", "II"):
        t, c = sg_total.get(k, 0), sg_correct.get(k, 0)
        a = accs[k]
        if a is not None:
            print(f"  {k}: {c}/{t} = {a:.2f}%")
    print(f"  TCE (overall):    {tce_overall:.2f}" if tce_overall is not None else "")
    print(f"  Combined Score:   {combined:.2f}" if combined is not None else "")
    print()

    # -------- 3. Path-level accuracy and TCE  [§5.2 Fallback Analysis] ----
    print("=" * 78)
    print("3. PATH-LEVEL BREAKDOWN  [for §5.2 Table 5]")
    print("=" * 78)
    path_table_rows = []
    for path_name in ("symbolic", "fallback"):
        items = [r for r in joined if r["method"] == path_name]
        if not items: continue
        N = len(items)
        c = sum(1 for r in items if r["correct"])
        a = 100.0 * c / N
        # TCE on this subset
        sg_t = Counter(r["subgroup"] for r in items)
        sg_c = Counter(r["subgroup"] for r in items if r["correct"])
        tce_p, _ = compute_tce(sg_c, sg_t)
        cs_p = combined_score(a, tce_p) if tce_p is not None else None
        print(f"\n  {path_name.upper()}:")
        print(f"    N:        {N}")
        print(f"    Correct:  {c}")
        print(f"    Errors:   {N - c}")
        print(f"    Accuracy: {a:.2f}%")
        print(f"    TCE:      {tce_p:.2f}" if tce_p is not None else "    TCE:      n/a")
        print(f"    Combined: {cs_p:.2f}" if cs_p is not None else "    Combined: n/a")
        print(f"    Subgroup totals:   {dict(sg_t)}")
        print(f"    Subgroup correct:  {dict(sg_c)}")
        path_table_rows.append((path_name, N, a, tce_p, cs_p))
    print()

    # -------- 4. Error distribution by subgroup  [for §5 sanity] ----------
    print("=" * 78)
    print("4. ERROR SUBGROUP DISTRIBUTION")
    print("=" * 78)
    err_sg = Counter(r["subgroup"] for r in joined if not r["correct"])
    for k in ("VP", "VI", "IP", "II"):
        print(f"  {k}: {err_sg.get(k, 0)}")
    total_err = sum(err_sg.values())
    print(f"  Total errors: {total_err}")
    print(f"  Distribution as VP-VI-IP-II: "
          f"{err_sg['VP']}-{err_sg['VI']}-{err_sg['IP']}-{err_sg['II']}")
    print()

    # -------- 5. Per-error detail table  [for Table 9 / Appendix C] -------
    errors = [r for r in joined if not r["correct"]]
    print("=" * 78)
    print("5. PER-ERROR DETAIL  [for Table 9 / Appendix C]")
    print("=" * 78)
    header = f"{'#':<3} {'short':<10} {'Type':<5} {'Sub':<4} {'Gold':<9} {'Pred':<9} {'Pred_form':<14} {'Method':<9}"
    print(header)
    print("-" * 78)
    for i, e in enumerate(errors, 1):
        err_type = "FN" if e["gold"] == "VALID" else "FP"
        short = e["id"][:8]
        print(f"{i:<3} {short:<10} {err_type:<5} {e['subgroup']:<4} "
              f"{e['gold']:<9} {e['pred']:<9} {e['pred_form']:<14} {e['method']:<9}")
    print()

    # Print the syllogism text for each error (useful for deciding trigger)
    print("=" * 78)
    print("6. ERROR SYLLOGISM TEXT  [to classify linguistic triggers]")
    print("=" * 78)
    for i, e in enumerate(errors, 1):
        print(f"\n--- Error #{i} ({e['id'][:8]}) ---")
        print(f"Gold: {e['gold']}  |  Pred: {e['pred']}  |  Path: {e['method']}")
        print(f"Subgroup: {e['subgroup']}  |  Pred form: {e['pred_form']}")
        print(f"Syllogism: {e['syllogism']}")
        if e["structure"]:
            p1 = e["structure"].get("premise1", {})
            p2 = e["structure"].get("premise2", {})
            c = e["structure"].get("conclusion", {})
            print(f"  Extracted P1: type={p1.get('type')}  "
                  f"S={p1.get('subject')}  P={p1.get('predicate')}")
            print(f"  Extracted P2: type={p2.get('type')}  "
                  f"S={p2.get('subject')}  P={p2.get('predicate')}")
            print(f"  Extracted C:  type={c.get('type')}  "
                  f"S={c.get('subject')}  P={c.get('predicate')}")
            print(f"  Mid:{e['structure'].get('middle_term')} "
                  f"Major:{e['structure'].get('major_term')} "
                  f"Minor:{e['structure'].get('minor_term')} "
                  f"Fig:{e['structure'].get('figure')}")
        if e.get("error"):
            print(f"  Error: {e['error']}")

    # -------- Save outputs -------------------------------------------------
    with open("errors_detailed.json", "w") as f:
        json.dump(errors, f, indent=2)
    print("\n\nSaved: errors_detailed.json (full error records)")

    with open("paper_numbers.txt", "w") as f:
        f.write(f"# Camera-ready numbers for semeval2026_paper.tex\n")
        f.write(f"# Generated by analyze_submission.py\n\n")
        f.write(f"Overall accuracy:   {acc:.2f}%  ({n_correct}/{n})\n")
        f.write(f"Overall TCE:        {tce_overall:.2f}\n" if tce_overall else "")
        f.write(f"Combined Score:     {combined:.2f}\n\n" if combined else "")
        f.write(f"Subgroup accuracy (Table 3):\n")
        for k in ("VP", "VI", "IP", "II"):
            t, c = sg_total.get(k, 0), sg_correct.get(k, 0)
            a = accs[k]
            if a is not None:
                f.write(f"  {k}: {c}/{t} = {a:.2f}%\n")
        f.write(f"\nError distribution VP-VI-IP-II: "
                f"{err_sg['VP']}-{err_sg['VI']}-{err_sg['IP']}-{err_sg['II']}\n")
        f.write(f"\nPath breakdown (Table 5):\n")
        for path, N, a, tce_p, cs_p in path_table_rows:
            f.write(f"  {path}: N={N}  acc={a:.2f}%  "
                    f"TCE={tce_p:.2f if tce_p is not None else 'n/a'}  "
                    f"combined={cs_p:.2f if cs_p is not None else 'n/a'}\n")
    print("Saved: paper_numbers.txt (summary for pasting into paper)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
