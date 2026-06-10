# Does a strong LLM still show the content effect? Claude Opus 4.8 on SemEval‑2026 Task 11

**Probe run:** 2026‑06‑10 · Model: `claude-opus-4-8` · Full test set (191 instances)

## TL;DR

A frontier LLM (Claude Opus 4.8), asked for a **snap** validity judgment (boolean
only, no chain‑of‑thought), reaches essentially the **same accuracy** as our
neuro‑symbolic system — but with a **~4× larger content effect**. Accuracy alone
hides the bias; the Total Content Effect (TCE) exposes it.

| System | Accuracy | **TCE** |
|---|---|---|
| Claude Opus 4.8 — snap (raw LLM) | 96.86% | **4.22** |
| Our neuro‑symbolic system (submitted) | 96.34% | **1.02** |

## Why this probe

The task is to judge the **formal validity** of categorical syllogisms while
ignoring real‑world plausibility. The *content effect* is the tendency to accept
invalid‑but‑believable arguments and reject valid‑but‑absurd ones. Our system
attacks it by forbidding the LLM from reasoning — it only extracts A/E/I/O types
and terms, and a deterministic validator decides validity against the 24 valid
Aristotelian forms (TCE ≈ 0 by construction).

This probe asks the opposite question: **how much content bias does a strong LLM
show on its own?** To surface it, we strip away the LLM's ability to deliberate.

## Method

- **Model:** `claude-opus-4-8` via the official Anthropic API.
- **Snap judgment:** extended thinking **disabled**, and the structured output
  schema contains **only** `valid: bool` — no `reason` field — so the model
  cannot work through the form in its output. This is the condition under which
  content bias shows up most.
- **Data:** the full Subtask‑1 test set, 191 instances, balanced across the four
  conditions:

  | Condition | Meaning | N |
  |---|---|---|
  | VP | valid + plausible | 48 |
  | VI | valid + implausible | 48 |
  | IP | invalid + plausible | 47 |
  | II | invalid + implausible | 48 |

- **TCE:** computed with the **same formula** as the project evaluator
  (`lib/evaluation.py`): the absolute difference, in percentage points, between
  accuracy on *plausible* items (VP + IP) and accuracy on *implausible* items
  (VI + II).

  ```
  TCE = |acc(plausible) − acc(implausible)| × 100
  ```

Reproduce with:

```bash
# key in a .env file:  ANTHROPIC_API_KEY=sk-ant-...
python subtask_1/probe_claude_sample.py --snap --full
```

Script: [`probe_claude_sample.py`](probe_claude_sample.py) ·
Raw log: [`results_claude_opus48_snap_full.txt`](results_claude_opus48_snap_full.txt)

## Results

```
Overall accuracy: 185/191 = 96.86%
  VP (valid+plausible):     46/48 = 95.83%
  VI (valid+implausible):   47/48 = 97.92%
  IP (invalid+plausible):   44/47 = 93.62%
  II (invalid+implausible): 48/48 = 100.00%

Plausible accuracy:   94.74% (n=95)
Implausible accuracy: 98.96% (n=96)
Total Content Effect (TCE): 4.22
```

**The bias has a direction.** Plausible accuracy (94.74%) is *lower* than
implausible accuracy (98.96%): the model leans toward calling plausible things
valid and implausible things invalid. The cleanest tell is the corner cells —
**II = 100%** (rejecting implausible‑invalid arguments is easy *and* aligned with
the bias) versus **IP = 93.62%** (where plausibility lures the model into
accepting invalid arguments).

## The 6 errors

**Accepted invalid arguments (false‑valid) — all 3 are IP (invalid + plausible):**

| Syllogism | Gold | Pred |
|---|---|---|
| *No bikes are cars. Every bike is a vehicle. → some vehicles are bikes.* | invalid | **valid** |
| *No cats are dogs. Every cat is an animal. → some animals are cats.* | invalid | **valid** |
| *A chair is a table. A table cannot be a building. → a building is never a chair.* | invalid | **valid** |

**Rejected valid arguments (false‑invalid) — 2 VP, 1 VI:**

| Syllogism | Gold | Pred |
|---|---|---|
| *Every river flows to the sea. The Amazon is a river. → parts of the Amazon flow to the sea.* | valid | **invalid** |
| *Every cat is a feline. No feline is a canine. → some canines are not cats.* | valid | **invalid** |
| *No animal is a pet. All dogs are pets. → some dogs are not animals.* (Cesaro, EAO‑2) | valid | **invalid** |

Every error is consistent with judging by **content** rather than **form** — the
plausible invalids get waved through, the awkward‑sounding valids get rejected.

## Takeaway

Opus 4.8 is a strong reasoner: with deliberation enabled it scores ~100% on these
trap cases. But stripped of its scratchpad it falls back on plausibility, and the
content effect re‑emerges at **4.22** — roughly **4× our system's 1.02**, at
matched accuracy. This is the core argument of the paper restated empirically:
**content‑invariance is an architectural property, not a side effect of a bigger
model.** A deterministic validator that only ever sees the logical form cannot be
fooled by believable nonsense.

---

*Part of [pamaldi at SemEval‑2026 Task 11](../README.MD). Interactive pipeline
visualizer: <https://pamaldi.github.io/pamaldi_semeval_task11/>*
