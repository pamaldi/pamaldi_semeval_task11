# pamaldi at SemEval-2026 Task 11: Neuro-Symbolic Syllogistic Reasoning

**Pasquale Grimaldi** — Università di Firenze

This repository contains the code, notebooks, and system description paper for our participation in [SemEval-2026 Task 11](https://neuro-symbolic-ai.github.io/SemEval2026-Task11/): *Disentangling Content and Formal Reasoning in Language Models* (Subtask 1 — English syllogistic validity classification).

## Results

| Metric | Official Score |
|--------|---------------|
| **Combined Score** | **56.57** |
| Accuracy | 96.34% (184/191) |
| Total Content Effect (TCE) | 1.02 |

The near-zero TCE confirms that our system is virtually immune to content bias — it does not confuse logical validity with real-world plausibility.

## Approach

Our system implements a **neuro-symbolic pipeline** that strictly separates language understanding from logical reasoning:

1. **Neural Extraction** — An LLM (Qwen3-32B) extracts the formal structure of natural language syllogisms: proposition types (A, E, I, O) and the three terms (subject, predicate, middle).
2. **Deterministic Figure Computation** — The syllogistic figure (1–4) is computed deterministically from the middle term's position in the premises, eliminating the most error-prone LLM step.
3. **Symbolic Validation** — A deterministic checker verifies whether the extracted mood–figure pair belongs to the 24 classically valid Aristotelian forms (with existential import).
4. **Self-Consistency Voting** — Three extraction samples at temperatures [0.1, 0.3, 0.5] are aggregated via majority vote.
5. **Post-Processing** — Rule-based corrections for I/O proposition confusion, double negation, and compound term normalization.
6. **LLM Fallback** — When extraction fails entirely, a direct LLM validity judgment is used (~4% of cases).

All errors originate in the neural extraction stage; the symbolic validator introduces zero content-dependent failures.

## Repository Structure

```
pamaldi_semeval_2026_11_task1/
│
├── 📄 05_semeval_task11_1_simplified_deterministic_figure_submitted.py  # Submitted system (56.57)
│
├── 📓 Notebooks (development & evaluation)
│   ├── 01_semeval_task11_1_prolog_reflexion.ipynb              # Prolog code gen + Reflexion
│   ├── 02_semeval_task11_1_incremental_meta_learning.ipynb     # Incremental meta-learning
│   ├── 03_semeval_task11_1_neurosymbolic_full_extraction.ipynb # Full LLM extraction + det. validity
│   └── 04_semeval_task11_1_simplified_deterministic_figure.ipynb # Simplified extractor + det. figure
│
├── 🔧 Core modules
│   ├── neurosymbolic_pipeline.py              # Main pipeline orchestrator
│   ├── simplified_extractor.py                # Simplified extractor (types + terms only)
│   ├── syllogism_extractor.py                 # Full extractor (types + terms + figure)
│   ├── validity_checker.py                    # Deterministic 24-form validity checker
│   ├── postprocessor.py                       # Deterministic figure computation & corrections
│   ├── proposition_validator.py               # Rule-based I/O type correction
│   ├── extraction_reflexion.py                # Self-correction via error feedback
│   ├── llm_fallback.py                        # Direct LLM validity fallback
│   ├── syllogism_structures.py                # Data models (Proposition, SyllogismStructure)
│   ├── evaluation.py                          # Metrics computation
│   ├── meta_learning.py                       # Error-driven prompt enhancement
│   ├── incremental_meta_learning.py           # Online checkpoint-based learning
│   ├── bedrock_client_bearer.py               # AWS Bedrock API client
│   └── setup_path.py                          # Path configuration for imports
│
├── 📊 Data
│   ├── data/train_data.json                   # 200 training syllogisms (English)
│   └── data/test_data_subtask_1.json          # 191 test syllogisms (English)
│
├── 📝 Prompts
│   └── prompts/structure_extraction_simplified.txt  # Extraction prompt for submitted system
│
├── 📄 Paper
│   ├── paper/semeval2026_paper.tex             # System description paper (LaTeX)
│   ├── paper/semeval2026_paper.pdf             # Compiled PDF
│   └── paper/references.bib                   # Bibliography
│
├── requirements.txt
└── README.md
```

## Approaches Explored

We explored four architectures during development, all re-evaluated on the 191-instance test set:

| Approach | Test Acc | TCE | Combined Score |
|----------|----------|-----|----------------|
| Prolog + Reflexion | 90.58% | 8.49 | 27.87 |
| Incremental Meta-Learning | 95.29% | 6.25 | 31.97 |
| Full LLM Extraction + Det. Validity | 97.91% | 2.13 | 45.74 |
| Simplified Extraction + Det. Figure | 97.38% | 2.08 | 45.81 |
| **Submitted System** | **96.34%** | **1.02** | **56.57** |

The submitted system uses the **Simplified Extraction** architecture. The key insight across all iterations: **more deterministic components → lower content effect → higher combined score**.

## Quick Start

### Prerequisites

- Python 3.11+
- AWS credentials with access to Amazon Bedrock (Qwen3-32B model)

### Installation

```bash
git clone https://github.com/[your-username]/pamaldi-semeval-2026-task11.git
cd pamaldi-semeval-2026-task11/pamaldi_semeval_2026_11_task1
pip install -r requirements.txt
```

### Configuration

Create `aws_credentials.txt` in the project root with your AWS Bedrock credentials:

```
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=us-east-1
```

### Run the Submitted System

```bash
python 05_semeval_task11_1_simplified_deterministic_figure_submitted.py
```

This runs the exact configuration that produced the official 56.57 score:
- Model: Qwen3-32B via AWS Bedrock
- Simplified extractor (types + terms only, deterministic figure)
- Self-consistency voting (k=3, temperatures [0.1, 0.3, 0.5])
- LLM fallback when extraction fails

Set `NUM_TRAIN` and `NUM_TEST` in the script to control how many examples to process (`-1` for all, `0` to skip).

### Run Individual Notebooks

```bash
cd pamaldi_semeval_2026_11_task1
jupyter notebook
```

Open any notebook (`01_` through `04_`) to explore different approaches. Each notebook is self-contained with its own configuration and evaluation.

## Key Design Decisions

**Why neuro-symbolic instead of end-to-end LLM?** End-to-end approaches consistently showed higher content effects because the LLM's world knowledge interferes with purely structural validity judgments. Our strict separation guarantees content-agnostic validation.

**Why 24 Aristotelian forms, not 15 modern forms?** The task dataset adopts the traditional Aristotelian interpretation with existential import. Switching from 15 to 24 forms yielded one of the largest accuracy gains (+4%).

**Why deterministic figure computation?** Figure identification was the most error-prone LLM step. Computing it deterministically from term positions eliminated an entire class of errors.

**Why self-consistency voting?** Sampling k=3 extractions at varied temperatures and taking majority vote smooths sporadic extraction errors. Improved training accuracy from 94% to 97%.

## Citation

```bibtex
@inproceedings{grimaldi-2026-pamaldi,
    title = "pamaldi at {S}em{E}val-2026 Task 11: Neuro-Symbolic Syllogistic
             Reasoning via {LLM}-Guided Structure Extraction and Deterministic
             Validation",
    author = "Grimaldi, Pasquale",
    booktitle = "Proceedings of the 20th International Workshop on Semantic
                 Evaluation (SemEval-2026)",
    year = "2026"
}
```

## Task Reference

```bibtex
@inproceedings{valentino-etal-2026-semeval,
    title = "{S}em{E}val-2026 Task 11: Disentangling Content and Formal
             Reasoning in Language Models",
    author = "Valentino, Marco and Ranaldi, Leonardo and Pucci, Giulia
              and Ranaldi, Federico and Freitas, Andr{\'e}",
    booktitle = "Proceedings of the 20th International Workshop on Semantic
                 Evaluation (SemEval-2026)"
}
```

## License

This project is released for academic and research purposes.