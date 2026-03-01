#!/usr/bin/env python3
"""
Simplified Pipeline with Deterministic Figure — runnable script.
Same config and official evaluation as semeval_simplified_pipeline.ipynb.
Run from repo root or from pamaldi_semeval_2026_11_task1:
  python pamaldi_semeval_2026_11_task1/semeval_simplified_pipeline.py
  # or from task folder:
  python semeval_simplified_pipeline.py
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Setup path (same as notebooks)
_nb_dir = Path.cwd() / "pamaldi_semeval_2026_11_task1" if (Path.cwd() / "pamaldi_semeval_2026_11_task1").exists() else Path.cwd()
sys.path.insert(0, str(_nb_dir))
import setup_path  # noqa: E402

from load_credentials import load_credentials_from_file  # noqa: E402
_creds = _nb_dir / "aws_credentials.txt" if (_nb_dir / "aws_credentials.txt").exists() else _nb_dir.parent / "aws_credentials.txt"
load_credentials_from_file(str(_creds))
print("✓ Credentials loaded")

from bedrock_client_bearer import BedrockClientBearer as BedrockClient  # noqa: E402
from neurosymbolic_pipeline import NeuroSymbolicPipeline  # noqa: E402
from evaluation import NeuroSymbolicEvaluator  # noqa: E402

print("✓ Imports successful")

# ============================================================
# CONFIGURATION (same as notebook)
# ============================================================
MODEL_ID = "qwen.qwen3-32b-v1:0"
NUM_TRAIN = 1    # -1 for all, 0 to skip training
NUM_TEST = -1    # -1 for all, 0 to skip test

PIPELINE_CONFIG = {
    "use_simplified_extractor": True,
    "use_reflexion": False,
    "use_self_consistency": True,
    "num_consistency_samples": 3,
    "temperature_schedule": [0.1, 0.3, 0.5],
    "use_fallback": True,
    "fallback_use_self_consistency": False,
}

# Data paths (relative to task folder)
TRAIN_DATA_PATH = _nb_dir / "data" / "train_data.json"
TEST_DATA_PATH = _nb_dir / "data" / "test_data_subtask_1.json"
SIMPLIFIED_PROMPT_PATH = _nb_dir / "prompts" / "structure_extraction_simplified.txt"
RESULTS_DIR = _nb_dir.parent / "semeval_results"


def run_official_evaluation(reference_file, predictions_file, results_file, model_id, n_examples, phase_name="RESULTS"):
    """Run official Task 1 & 3 evaluation and print metrics."""
    _eval_kit = Path.cwd().parent / "evaluation_kit" / "task 1 & 3"
    if not _eval_kit.exists():
        _eval_kit = _nb_dir.parent / "evaluation_kit" / "task 1 & 3"
    if _eval_kit.exists() and str(_eval_kit) not in sys.path:
        sys.path.insert(0, str(_eval_kit))
    from evaluation_script import run_full_scoring
    run_full_scoring(str(reference_file), str(predictions_file), str(results_file))
    if Path(results_file).exists():
        print("\n" + "=" * 80)
        print(f"OFFICIAL EVALUATION {phase_name}")
        print("=" * 80)
        with open(results_file, "r") as f:
            eval_results = json.load(f)
        print(f"\nModel: {model_id}")
        print(f"Examples: {n_examples}")
        print(f"\nMetrics:")
        print(f"  Accuracy:        {eval_results.get('accuracy', 0):.2f}%")
        print(f"  Content Effect:  {eval_results.get('content_effect', 0):.2f}%")
        print(f"  Combined Score:  {eval_results.get('combined_score', 0):.2f}%")
        print("\n" + "=" * 80)

def main():
    print(f"Model: {MODEL_ID}")
    print(f"NUM_TRAIN: {NUM_TRAIN} {'(all)' if NUM_TRAIN == -1 else ''}")
    print(f"NUM_TEST: {NUM_TEST} {'(all)' if NUM_TEST == -1 else ''}")
    print("\nSimplified Pipeline: SimplifiedExtractor (deterministic figure)")
    print(f"  Self-consistency: {PIPELINE_CONFIG['use_self_consistency']}, Samples: {PIPELINE_CONFIG['num_consistency_samples']}")
    print(f"  Fallback: {PIPELINE_CONFIG['use_fallback']}\n")

    client = BedrockClient(model_id=MODEL_ID)
    evaluator = NeuroSymbolicEvaluator()

    train_data = []
    train_results = None
    pipeline = None

    # ----- Training -----
    if NUM_TRAIN != 0 and TRAIN_DATA_PATH.exists():
        with open(TRAIN_DATA_PATH, "r", encoding="utf-8") as f:
            train_data = json.load(f)
        if NUM_TRAIN > 0:
            train_data = train_data[:NUM_TRAIN]
        print(f"Loaded {len(train_data)} training examples")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = RESULTS_DIR / f"simplified_train_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)

        pipeline = NeuroSymbolicPipeline(
            bedrock_client=client,
            prompt_path=str(SIMPLIFIED_PROMPT_PATH),
            results_dir=str(output_dir),
            run_name="train",
            verbose=False,
            **PIPELINE_CONFIG,
        )
        print("Running training...")
        train_results = pipeline.run(train_data, verbose=True)
        print("✓ Training complete")

        # Internal evaluation
        train_metrics = evaluator.evaluate(train_results)
        evaluator.print_report(train_metrics)

        # Official evaluation (training)
        train_output_dir = Path(pipeline.results_dir)
        reference_file = train_output_dir / "reference.json"
        predictions_file = train_output_dir / "predictions_official.json"
        results_file = train_output_dir / "official_evaluation_results.json"
        print("\n[1] Building reference file...")
        reference_data = [
            {"id": item["id"], "validity": item.get("validity", False), "plausibility": item.get("plausibility", False)}
            for item in train_data
        ]
        with open(reference_file, "w", encoding="utf-8") as f:
            json.dump(reference_data, f, indent=2)
        print(f"✓ Reference file: {reference_file}")
        print("\n[2] Building predictions file...")
        predictions_official = [{"id": r["id"], "validity": (r.get("prediction") == "VALID")} for r in train_results]
        with open(predictions_file, "w", encoding="utf-8") as f:
            json.dump(predictions_official, f, indent=2)
        print(f"✓ Predictions file: {predictions_file}")
        print("\n[3] Running official evaluation...")
        print("-" * 80)
        run_official_evaluation(
            reference_file, predictions_file, results_file,
            MODEL_ID, len(train_data), phase_name="RESULTS (TRAINING)"
        )
    else:
        if NUM_TRAIN == 0:
            print("Skipping training (NUM_TRAIN = 0)")
        else:
            print(f"Training data not found: {TRAIN_DATA_PATH}")

    # ----- Test -----
    test_results = None
    test_pipeline = None
    test_data = []
    if NUM_TEST != 0 and TEST_DATA_PATH.exists():
        with open(TEST_DATA_PATH, "r", encoding="utf-8") as f:
            test_data = json.load(f)
        if NUM_TEST > 0:
            test_data = test_data[:NUM_TEST]
        print(f"\nLoaded {len(test_data)} test examples")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_output_dir = RESULTS_DIR / f"neurosymbolic_test_simplified_{timestamp}"
        test_output_dir.mkdir(parents=True, exist_ok=True)

        test_pipeline = NeuroSymbolicPipeline(
            bedrock_client=client,
            prompt_path=str(SIMPLIFIED_PROMPT_PATH),
            results_dir=str(test_output_dir),
            run_name="test_simplified",
            verbose=False,
            **PIPELINE_CONFIG,
        )
        print("Running test...")
        test_results = test_pipeline.run(test_data, verbose=True)
        test_pipeline.save_predictions(test_results)
        print("\n✓ Predictions saved!")

        # Official evaluation (test)
        print("\n" + "=" * 80)
        print("OFFICIAL EVALUATION — TEST (Task 1 & 3)")
        print("=" * 80)
        out_dir = Path(test_pipeline.results_dir)
        reference_file = out_dir / "reference.json"
        predictions_file = out_dir / "predictions_official.json"
        results_file = out_dir / "official_evaluation_results.json"
        print("\n[1] Building reference file...")
        reference_data = [
            {"id": item["id"], "validity": item.get("validity", False), "plausibility": item.get("plausibility", False)}
            for item in test_data
        ]
        with open(reference_file, "w", encoding="utf-8") as f:
            json.dump(reference_data, f, indent=2)
        print(f"✓ Reference file: {reference_file}")
        print("\n[2] Building predictions file...")
        predictions_official = [{"id": r["id"], "validity": (r.get("prediction") == "VALID")} for r in test_results]
        with open(predictions_file, "w", encoding="utf-8") as f:
            json.dump(predictions_official, f, indent=2)
        print(f"✓ Predictions file: {predictions_file}")
        print("\n[3] Running official evaluation...")
        print("-" * 80)
        run_official_evaluation(
            reference_file, predictions_file, results_file,
            MODEL_ID, len(test_data), phase_name="RESULTS (TEST)"
        )
    else:
        if NUM_TEST == 0:
            print("Skipping test (NUM_TEST = 0)")
        else:
            print(f"Test data not found: {TEST_DATA_PATH}")

    print("\n✓ Simplified pipeline script complete.")

if __name__ == "__main__":
    main()
