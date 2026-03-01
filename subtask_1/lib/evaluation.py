"""
Evaluation module for the neuro-symbolic pipeline.
"""

from typing import List, Dict, Any
from collections import Counter


class NeuroSymbolicEvaluator:
    """Evaluate the neuro-symbolic pipeline results."""
    
    def evaluate(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute evaluation metrics.
        
        Args:
            results: List of result dicts from pipeline
            
        Returns:
            dict with accuracy, content effect, and breakdown by plausibility
        """
        total = len(results)
        
        if total == 0:
            return {"error": "No results to evaluate"}
        
        # Filter to only successfully processed items
        valid_results = [r for r in results if r.get("prediction") is not None]
        
        if not valid_results:
            return {"error": "No valid results to evaluate"}
        
        # Extraction success rate
        extraction_success = sum(1 for r in results if r.get("extraction_success"))
        extraction_rate = extraction_success / total
        
        # Filter to items with ground truth
        with_gt = [r for r in valid_results if r.get("ground_truth")]
        
        if not with_gt:
            return {
                "total_items": total,
                "processed_items": len(valid_results),
                "extraction_success_rate": extraction_rate,
                "overall_accuracy": None,
                "note": "No ground truth available for accuracy calculation"
            }
        
        # Overall accuracy
        correct = sum(1 for r in with_gt if r["prediction"] == r["ground_truth"])
        accuracy = correct / len(with_gt)
        
        # Breakdown by plausibility
        plausible_results = [r for r in with_gt if r.get("plausibility") == "PLAUSIBLE"]
        implausible_results = [r for r in with_gt if r.get("plausibility") == "IMPLAUSIBLE"]
        
        plausible_acc = self._compute_accuracy(plausible_results)
        implausible_acc = self._compute_accuracy(implausible_results)
        
        # Content effect (difference between plausible and implausible accuracy)
        content_effect = None
        if plausible_acc is not None and implausible_acc is not None:
            content_effect = abs(plausible_acc - implausible_acc)
        
        # Breakdown by ground truth validity
        valid_gt = [r for r in with_gt if r.get("ground_truth") == "VALID"]
        invalid_gt = [r for r in with_gt if r.get("ground_truth") == "INVALID"]
        
        valid_acc = self._compute_accuracy(valid_gt)
        invalid_acc = self._compute_accuracy(invalid_gt)
        
        # Error analysis
        errors = [r for r in with_gt if r["prediction"] != r["ground_truth"]]
        error_types = Counter()
        for e in errors:
            if e["prediction"] == "VALID" and e["ground_truth"] == "INVALID":
                error_types["false_valid"] += 1
            elif e["prediction"] == "INVALID" and e["ground_truth"] == "VALID":
                error_types["false_invalid"] += 1
        
        # Form analysis (which forms are being misclassified)
        form_errors = Counter()
        for e in errors:
            if e.get("validity_details"):
                form = e["validity_details"].get("form", "unknown")
                form_errors[form] += 1
        
        return {
            "total_items": total,
            "processed_items": len(valid_results),
            "items_with_ground_truth": len(with_gt),
            "extraction_success_rate": extraction_rate,
            "overall_accuracy": accuracy,
            "correct": correct,
            "incorrect": len(with_gt) - correct,
            "content_effect": content_effect,
            "plausible_accuracy": plausible_acc,
            "plausible_count": len(plausible_results),
            "implausible_accuracy": implausible_acc,
            "implausible_count": len(implausible_results),
            "valid_gt_accuracy": valid_acc,
            "valid_gt_count": len(valid_gt),
            "invalid_gt_accuracy": invalid_acc,
            "invalid_gt_count": len(invalid_gt),
            "error_breakdown": dict(error_types),
            "form_errors": dict(form_errors.most_common(10))
        }
    
    def _compute_accuracy(self, results: List[Dict]) -> float:
        """Compute accuracy for a subset of results."""
        if not results:
            return None
        correct = sum(1 for r in results if r["prediction"] == r.get("ground_truth"))
        return correct / len(results)
    
    def print_report(self, metrics: Dict[str, Any]):
        """Print a formatted evaluation report."""
        print("\n" + "=" * 60)
        print("NEURO-SYMBOLIC EVALUATION REPORT")
        print("=" * 60)
        
        print(f"\nTotal Items: {metrics.get('total_items', 'N/A')}")
        print(f"Processed: {metrics.get('processed_items', 'N/A')}")
        print(f"Extraction Rate: {metrics.get('extraction_success_rate', 0)*100:.1f}%")
        
        if metrics.get('overall_accuracy') is not None:
            print(f"\nOverall Accuracy: {metrics['overall_accuracy']*100:.2f}%")
            print(f"  Correct: {metrics.get('correct', 0)}")
            print(f"  Incorrect: {metrics.get('incorrect', 0)}")
        
        if metrics.get('content_effect') is not None:
            print(f"\nContent Effect: {metrics['content_effect']*100:.2f}%")
            if metrics.get('plausible_accuracy') is not None:
                print(f"  Plausible Accuracy: {metrics['plausible_accuracy']*100:.2f}% (n={metrics.get('plausible_count', 0)})")
            if metrics.get('implausible_accuracy') is not None:
                print(f"  Implausible Accuracy: {metrics['implausible_accuracy']*100:.2f}% (n={metrics.get('implausible_count', 0)})")
        
        if metrics.get('valid_gt_accuracy') is not None:
            print(f"\nBy Ground Truth:")
            print(f"  VALID accuracy: {metrics['valid_gt_accuracy']*100:.2f}% (n={metrics.get('valid_gt_count', 0)})")
        if metrics.get('invalid_gt_accuracy') is not None:
            print(f"  INVALID accuracy: {metrics['invalid_gt_accuracy']*100:.2f}% (n={metrics.get('invalid_gt_count', 0)})")
        
        if metrics.get('error_breakdown'):
            print(f"\nError Breakdown:")
            for error_type, count in metrics['error_breakdown'].items():
                print(f"  {error_type}: {count}")
        
        if metrics.get('form_errors'):
            print(f"\nMost Common Form Errors:")
            for form, count in list(metrics['form_errors'].items())[:5]:
                print(f"  {form}: {count}")
        
        print("\n" + "=" * 60)


# Quick test
if __name__ == "__main__":
    evaluator = NeuroSymbolicEvaluator()
    
    # Test with sample data
    sample_results = [
        {"prediction": "VALID", "ground_truth": "VALID", "plausibility": "PLAUSIBLE", "extraction_success": True},
        {"prediction": "INVALID", "ground_truth": "INVALID", "plausibility": "IMPLAUSIBLE", "extraction_success": True},
        {"prediction": "VALID", "ground_truth": "INVALID", "plausibility": "PLAUSIBLE", "extraction_success": True},
    ]
    
    metrics = evaluator.evaluate(sample_results)
    evaluator.print_report(metrics)
