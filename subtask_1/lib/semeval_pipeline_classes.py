"""
PrologExecutor, CotExecutor, Evaluator for Bedrock pipeline (no torch/transformers).
Extracted from repo semeval_pipeline_classes.py for use in pamaldi_semeval_2026_11_task1/lib.
"""
import os
import json
import math
import traceback
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from tqdm import tqdm


class PrologExecutor:
    """Execute SWI-Prolog programs using pyswip"""

    def __init__(self, config: Any, prompt_builder=None, save_execution_files: bool = True):
        self.config = config
        self.save_execution_files = save_execution_files

        if save_execution_files:
            # Create timestamped execution folder (results and logs in same dir)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.execution_dir = os.path.join(config.results_dir, f"execution_prolog_{timestamp}")
            self.programs_dir = self.execution_dir
            self.logs_dir = self.execution_dir

            os.makedirs(self.execution_dir, exist_ok=True)

            # Save the system prompt if provided
            if prompt_builder:
                self._save_system_prompt(prompt_builder.system_prompt)

            print(f"✓ Execution directory: {self.execution_dir}")
        else:
            self.execution_dir = None
            self.programs_dir = None
            self.logs_dir = None

    def _save_system_prompt(self, system_prompt: str):
        """Save the system prompt to a file"""
        prompt_file = os.path.join(self.execution_dir, "system_prompt.txt")

        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("SYSTEM PROMPT FOR PROLOG CONVERSION\n")
            f.write("=" * 80 + "\n\n")
            f.write("This is the prompt used to instruct the LLM to convert syllogisms\n")
            f.write("into executable SWI-Prolog code.\n\n")
            f.write("=" * 80 + "\n")
            f.write("PROMPT CONTENT\n")
            f.write("=" * 80 + "\n\n")
            f.write(system_prompt)
            f.write("\n\n" + "=" * 80 + "\n")
            f.write("END OF PROMPT\n")
            f.write("=" * 80 + "\n")

        print(f"✓ System prompt saved to: {prompt_file}")

    def extract_code(self, response: str) -> Optional[str]:
        """Extract Prolog code from model response"""
        if "```prolog" in response:
            start = response.find("```prolog") + 9
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()

        # Look for Prolog patterns
        if ":-" in response or "valid_syllogism" in response:
            # Try to extract from first predicate to end
            lines = response.split('\n')
            code_lines = []
            in_code = False
            for line in lines:
                if ':-' in line or line.strip().endswith('.'):
                    in_code = True
                if in_code:
                    code_lines.append(line)
            if code_lines:
                return '\n'.join(code_lines).strip()

        return None

    def save_program(self, code: str, program_id: str) -> str:
        """Save Prolog program to file"""
        if not self.save_execution_files:
            return ""
        filepath = os.path.join(self.programs_dir, f"program_{program_id}.pl")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)
        return filepath

    def execute_program(self, filepath: str) -> Tuple[str, str, str]:
        """Execute a Prolog program using subprocess to avoid PySwip singleton issues"""
        try:
            import subprocess

            # Create a wrapper script that loads the file and queries valid_syllogism
            # Using subprocess ensures complete isolation between executions
            query_script = f'''
consult('{filepath.replace(chr(92), "/")}'),
(valid_syllogism -> writeln('RESULT:VALID') ; writeln('RESULT:INVALID')),
halt.
'''

            # Run swipl with the query
            result = subprocess.run(
                ['swipl', '-g', query_script.strip(), '-t', 'halt'],
                capture_output=True,
                text=True,
                timeout=30
            )

            stdout = result.stdout
            stderr = result.stderr

            # Parse result
            if 'RESULT:VALID' in stdout:
                prediction = "VALID"
            elif 'RESULT:INVALID' in stdout:
                prediction = "INVALID"
            else:
                # Check for errors
                if result.returncode != 0 or stderr:
                    prediction = "ERROR"
                else:
                    prediction = "INVALID"  # Default if no clear result

            return prediction, stdout, stderr

        except subprocess.TimeoutExpired:
            return "ERROR", "", "Execution timed out after 30 seconds"
        except FileNotFoundError:
            # swipl not found, fall back to pyswip
            return self._execute_program_pyswip(filepath)
        except Exception as e:
            error_trace = traceback.format_exc()
            return "ERROR", "", error_trace

    def _execute_program_pyswip(self, filepath: str) -> Tuple[str, str, str]:
        """Fallback: Execute using pyswip (has singleton issues)"""
        try:
            from pyswip import Prolog

            prolog = Prolog()

            # Clear any previous state
            try:
                for pred in ['valid_syllogism', 'invalid_syllogism']:
                    try:
                        list(prolog.query(f"abolish({pred}/0)"))
                    except:
                        pass
            except:
                pass

            prolog.consult(filepath)
            result = list(prolog.query("valid_syllogism"))

            if result:
                prediction = "VALID"
                stdout = "Query valid_syllogism succeeded"
                stderr = ""
            else:
                prediction = "INVALID"
                stdout = "Query valid_syllogism failed"
                stderr = ""

            return prediction, stdout, stderr

        except Exception as e:
            error_trace = traceback.format_exc()
            return "ERROR", "", error_trace

    def _execute_code_temp(self, code: str) -> Tuple[str, str, str]:
        """Execute Prolog code using a temporary file"""
        import tempfile
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.pl', delete=False, encoding='utf-8') as f:
                f.write(code)
                temp_path = f.name

            result = self.execute_program(temp_path)

            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass

            return result
        except Exception as e:
            error_trace = traceback.format_exc()
            return "ERROR", "", error_trace

    def save_execution_log(
        self,
        program_id: str,
        syllogism: str,
        label: Optional[str],
        code: Optional[str],
        prediction: str,
        stdout: str,
        stderr: str
    ):
        """Save detailed execution log for a program"""
        if not self.save_execution_files:
            return
        log_filepath = os.path.join(self.logs_dir, f"log_{program_id}.txt")

        with open(log_filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"EXECUTION LOG - {program_id}\n")
            f.write("=" * 80 + "\n\n")

            # Syllogism
            f.write("SYLLOGISM:\n")
            f.write("-" * 80 + "\n")
            f.write(syllogism + "\n\n")

            # Label (if available)
            if label:
                f.write("GROUND TRUTH LABEL:\n")
                f.write("-" * 80 + "\n")
                f.write(label + "\n\n")

            # Generated Program
            f.write("GENERATED PROLOG PROGRAM:\n")
            f.write("-" * 80 + "\n")
            if code:
                f.write(code + "\n\n")
            else:
                f.write("ERROR: No code extracted from model response\n\n")

            # Execution Result
            f.write("EXECUTION RESULT:\n")
            f.write("-" * 80 + "\n")
            f.write(f"Prediction: {prediction}\n\n")

            # Standard Output
            if stdout:
                f.write("STDOUT:\n")
                f.write("-" * 80 + "\n")
                f.write(stdout + "\n\n")

            # Standard Error / Stack Trace
            if stderr:
                f.write("STDERR / STACK TRACE:\n")
                f.write("-" * 80 + "\n")
                f.write(stderr + "\n\n")

            # Summary
            f.write("=" * 80 + "\n")
            f.write("SUMMARY\n")
            f.write("=" * 80 + "\n")
            f.write(f"ID: {program_id}\n")
            f.write(f"Prediction: {prediction}\n")
            if label:
                f.write(f"Ground Truth: {label}\n")
                f.write(f"Correct: {'✓' if prediction == label else '✗'}\n")
            f.write("=" * 80 + "\n")

    def process_results(self, inference_results: List[Dict]) -> List[Dict]:
        """Process inference results and execute Prolog programs"""
        predictions = []

        print(f"\nProcessing {len(inference_results)} Prolog programs...")
        if self.save_execution_files:
            print(f"Execution logs will be saved to: {self.execution_dir}")

        for item in tqdm(inference_results, desc="Executing Prolog"):
            program_id = item['id']
            syllogism = item['text']
            label = item.get('label', None)
            response = item['response']

            # Extract code
            code = self.extract_code(response)

            if code:
                # Save and execute program
                if self.save_execution_files:
                    filepath = self.save_program(code, program_id)
                    prediction, stdout, stderr = self.execute_program(filepath)
                else:
                    # Use temp file when not saving
                    prediction, stdout, stderr = self._execute_code_temp(code)
            else:
                # No code extracted
                prediction = "ERROR"
                stdout = ""
                stderr = "Failed to extract Prolog code from model response"

            # Save detailed execution log
            self.save_execution_log(
                program_id=program_id,
                syllogism=syllogism,
                label=label,
                code=code,
                prediction=prediction,
                stdout=stdout,
                stderr=stderr
            )

            predictions.append({
                'id': program_id,
                'prediction': prediction,
                'label': label
            })

        # Create summary file
        if self.save_execution_files:
            self._create_summary(predictions, inference_results)
            print(f"✓ Prolog programs saved to: {self.programs_dir}")
            print(f"✓ Logs saved to: {self.logs_dir}")

        print(f"✓ Execution complete")

        return predictions

    def _create_summary(self, predictions: List[Dict], inference_results: List[Dict]):
        """Create a summary file for the execution batch"""
        if not self.save_execution_files:
            return
        summary_file = os.path.join(self.execution_dir, "execution_summary.txt")

        total = len(predictions)
        valid_count = sum(1 for p in predictions if p['prediction'] == 'VALID')
        invalid_count = sum(1 for p in predictions if p['prediction'] == 'INVALID')
        error_count = sum(1 for p in predictions if p['prediction'] == 'ERROR')

        # Calculate accuracy if labels available
        has_labels = any(p['label'] is not None for p in predictions)
        if has_labels:
            correct = sum(1 for p in predictions if p['label'] and p['prediction'] == p['label'])
            total_with_labels = sum(1 for p in predictions if p['label'] is not None)
            accuracy = correct / total_with_labels if total_with_labels > 0 else 0.0

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("PROLOG EXECUTION SUMMARY\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Execution Directory: {self.execution_dir}\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("STATISTICS:\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total Programs: {total}\n")
            f.write(f"VALID Predictions: {valid_count} ({valid_count/total*100:.1f}%)\n")
            f.write(f"INVALID Predictions: {invalid_count} ({invalid_count/total*100:.1f}%)\n")
            f.write(f"Errors: {error_count} ({error_count/total*100:.1f}%)\n\n")

            if has_labels:
                f.write("ACCURACY:\n")
                f.write("-" * 80 + "\n")
                f.write(f"Correct: {correct}/{total_with_labels}\n")
                f.write(f"Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)\n\n")

            f.write("FILES:\n")
            f.write("-" * 80 + "\n")
            f.write(f"Output (programs & logs): {self.execution_dir}/\n")
            f.write(f"Summary: {summary_file}\n\n")

            f.write("INDIVIDUAL RESULTS:\n")
            f.write("-" * 80 + "\n")
            for i, pred in enumerate(predictions, 1):
                status = "✓" if pred['label'] and pred['prediction'] == pred['label'] else "✗" if pred['label'] else "-"
                f.write(f"{i:3d}. {pred['id']}: {pred['prediction']:8s}")
                if pred['label']:
                    f.write(f" (GT: {pred['label']:8s}) {status}")
                f.write("\n")

            f.write("\n" + "=" * 80 + "\n")

        print(f"✓ Summary saved to: {summary_file}")


class Evaluator:
    """Calculate evaluation metrics - compatible with official SemEval evaluation"""

    def __init__(self, use_percentage_scale: bool = False):
        """
        Args:
            use_percentage_scale: If True, use 0-100 scale (official format).
                                 If False, use 0-1 scale (default for backward compatibility).
        """
        self.use_percentage_scale = use_percentage_scale

    def _scale(self, value: float) -> float:
        """Apply scaling based on configuration"""
        return value * 100 if self.use_percentage_scale else value

    def convert_to_official_format(self, predictions: List[Dict]) -> List[Dict]:
        """Convert from our format to official CodaBench format

        Our format: {'id': str, 'prediction': 'VALID'/'INVALID'/'ERROR'}
        Official format: {'id': str, 'validity': bool}
        """
        return [
            {
                'id': pred['id'],
                'validity': pred['prediction'] == 'VALID'
            }
            for pred in predictions
            if pred['prediction'] != 'ERROR'  # Skip ERROR predictions
        ]

    def calculate_accuracy(
        self,
        ground_truth: List[Dict],
        predictions: List[Dict]
    ) -> Dict[str, Any]:
        """Calculate accuracy metrics with plausibility-based content effect"""
        gt_map = {}
        for item in ground_truth:
            # Handle both 'label' and 'validity' keys
            label = item.get('label')
            if label is None and 'validity' in item:
                label = "VALID" if item['validity'] else "INVALID"
            gt_map[item['id']] = {
                'id': item['id'],
                'label': label,
                'validity': item.get('validity'),
                'plausibility': item.get('plausibility')
            }

        pred_map = {item['id']: item for item in predictions}

        # Overall accuracy
        correct = 0
        total = 0

        # For F1 calculation
        y_true_binary = []
        y_pred_binary = []

        for item_id, gt_item in gt_map.items():
            if item_id in pred_map:
                pred = pred_map[item_id]['prediction']
                label = gt_item['label']

                if pred == label:
                    correct += 1
                total += 1

                # Convert to binary for F1 (VALID=1, INVALID=0, ERROR=0)
                y_true_binary.append(1 if label == "VALID" else 0)
                y_pred_binary.append(1 if pred == "VALID" else 0)

        overall_accuracy = correct / total if total > 0 else 0.0

        # Calculate Macro F1
        if len(y_true_binary) > 0:
            # Calculate precision and recall for each class
            tp_valid = sum(1 for t, p in zip(y_true_binary, y_pred_binary) if t == 1 and p == 1)
            fp_valid = sum(1 for t, p in zip(y_true_binary, y_pred_binary) if t == 0 and p == 1)
            fn_valid = sum(1 for t, p in zip(y_true_binary, y_pred_binary) if t == 1 and p == 0)
            tn_valid = sum(1 for t, p in zip(y_true_binary, y_pred_binary) if t == 0 and p == 0)

            # F1 for VALID class
            precision_valid = tp_valid / (tp_valid + fp_valid) if (tp_valid + fp_valid) > 0 else 0
            recall_valid = tp_valid / (tp_valid + fn_valid) if (tp_valid + fn_valid) > 0 else 0
            f1_valid = 2 * precision_valid * recall_valid / (precision_valid + recall_valid) if (precision_valid + recall_valid) > 0 else 0

            # F1 for INVALID class
            precision_invalid = tn_valid / (tn_valid + fn_valid) if (tn_valid + fn_valid) > 0 else 0
            recall_invalid = tn_valid / (tn_valid + fp_valid) if (tn_valid + fp_valid) > 0 else 0
            f1_invalid = 2 * precision_invalid * recall_invalid / (precision_invalid + recall_invalid) if (precision_invalid + recall_invalid) > 0 else 0

            # Macro F1
            macro_f1 = (f1_valid + f1_invalid) / 2
        else:
            macro_f1 = 0.0

        # Subgroup accuracies (validity only - simplified)
        valid_correct = 0
        valid_total = 0
        invalid_correct = 0
        invalid_total = 0

        for item_id, gt_item in gt_map.items():
            if item_id in pred_map:
                pred = pred_map[item_id]['prediction']
                label = gt_item['label']

                if label == "VALID":
                    if pred == label:
                        valid_correct += 1
                    valid_total += 1
                elif label == "INVALID":
                    if pred == label:
                        invalid_correct += 1
                    invalid_total += 1

        valid_accuracy = valid_correct / valid_total if valid_total > 0 else 0.0
        invalid_accuracy = invalid_correct / invalid_total if invalid_total > 0 else 0.0

        # Check if plausibility data is available
        has_plausibility = any(gt_item.get('plausibility') is not None for gt_item in gt_map.values())

        if has_plausibility:
            # Calculate plausibility-based subgroup accuracies
            subgroup_metrics = self._calculate_plausibility_subgroups(gt_map, pred_map)
            content_effect = subgroup_metrics['tot_content_effect']

            # Calculate overall plausibility accuracies
            plausibility_metrics = self._calculate_plausibility_accuracies(gt_map, pred_map)
        else:
            # Simplified content effect (no plausibility)
            content_effect = abs(valid_accuracy - invalid_accuracy)
            subgroup_metrics = {}
            plausibility_metrics = {}

        # Apply scaling
        overall_accuracy_scaled = self._scale(overall_accuracy)
        valid_accuracy_scaled = self._scale(valid_accuracy)
        invalid_accuracy_scaled = self._scale(invalid_accuracy)
        content_effect_scaled = self._scale(content_effect)
        macro_f1_scaled = self._scale(macro_f1)

        # Combined metric (uses scaled values)
        combined_metric = overall_accuracy_scaled / (1 + math.log(1 + content_effect_scaled))

        result = {
            'overall_accuracy': overall_accuracy_scaled,
            'macro_f1': macro_f1_scaled,
            'valid_accuracy': valid_accuracy_scaled,
            'invalid_accuracy': invalid_accuracy_scaled,
            'content_effect_bias': content_effect_scaled,
            'combined_metric': combined_metric,
            'correct': correct,
            'total': total,
            'n_samples': total,
            'n_valid': valid_total,
            'n_invalid': invalid_total
        }

        # Add plausibility metrics if available (also scaled)
        if has_plausibility:
            # Scale subgroup metrics
            scaled_subgroup = {
                k: (self._scale(v) if isinstance(v, float) and k.startswith('acc_') else v)
                for k, v in subgroup_metrics.items()
            }
            # Scale content effect components
            if 'content_effect_intra' in scaled_subgroup:
                scaled_subgroup['content_effect_intra'] = self._scale(subgroup_metrics['content_effect_intra'])
            if 'content_effect_inter' in scaled_subgroup:
                scaled_subgroup['content_effect_inter'] = self._scale(subgroup_metrics['content_effect_inter'])
            if 'tot_content_effect' in scaled_subgroup:
                scaled_subgroup['tot_content_effect'] = self._scale(subgroup_metrics['tot_content_effect'])

            result.update(scaled_subgroup)

            # Scale plausibility metrics
            scaled_plausibility = {
                k: (self._scale(v) if k.startswith('acc_') else v)
                for k, v in plausibility_metrics.items()
            }
            result.update(scaled_plausibility)

        return result

    def evaluate_official(
        self,
        ground_truth: List[Dict],
        predictions: List[Dict]
    ) -> Dict[str, float]:
        """Evaluate using official CodaBench format and scale (0-100)

        Returns dict with keys matching official evaluation script:
        - accuracy: Overall accuracy (0-100)
        - content_effect: Total content effect (0-100)
        - combined_score: Primary ranking metric (0-100)
        """
        # Temporarily switch to percentage scale
        original_scale = self.use_percentage_scale
        self.use_percentage_scale = True

        try:
            # Calculate metrics
            metrics = self.calculate_accuracy(ground_truth, predictions)

            # Return in official format
            return {
                'accuracy': round(metrics['overall_accuracy'], 4),
                'content_effect': round(metrics.get('tot_content_effect', metrics['content_effect_bias']), 4),
                'combined_score': round(metrics['combined_metric'], 4)
            }
        finally:
            # Restore original scale
            self.use_percentage_scale = original_scale

    def _calculate_plausibility_accuracies(
        self,
        gt_map: Dict[str, Dict],
        pred_map: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """Calculate overall accuracies by plausibility (ignoring validity)"""
        plausible_correct = 0
        plausible_total = 0
        implausible_correct = 0
        implausible_total = 0

        for item_id, gt_item in gt_map.items():
            if item_id not in pred_map:
                continue

            pred = pred_map[item_id]['prediction']
            label = gt_item['label']
            plausibility = gt_item.get('plausibility')

            if plausibility is None:
                continue

            if plausibility:  # Plausible
                plausible_total += 1
                if pred == label:
                    plausible_correct += 1
            else:  # Implausible
                implausible_total += 1
                if pred == label:
                    implausible_correct += 1

        acc_plausible = plausible_correct / plausible_total if plausible_total > 0 else 0.0
        acc_implausible = implausible_correct / implausible_total if implausible_total > 0 else 0.0

        return {
            'acc_plausible': acc_plausible,
            'acc_implausible': acc_implausible,
            'n_plausible': plausible_total,
            'n_implausible': implausible_total
        }

    def _calculate_plausibility_subgroups(
        self,
        gt_map: Dict[str, Dict],
        pred_map: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """Calculate accuracies for plausibility x validity subgroups"""

        # Initialize counters for each subgroup
        subgroups = {
            'plausible_valid': {'correct': 0, 'total': 0},
            'implausible_valid': {'correct': 0, 'total': 0},
            'plausible_invalid': {'correct': 0, 'total': 0},
            'implausible_invalid': {'correct': 0, 'total': 0}
        }

        for item_id, gt_item in gt_map.items():
            if item_id not in pred_map:
                continue

            pred = pred_map[item_id]['prediction']
            label = gt_item['label']
            plausibility = gt_item.get('plausibility')

            if plausibility is None:
                continue

            # Determine subgroup
            if label == "VALID" and plausibility:
                subgroup = 'plausible_valid'
            elif label == "VALID" and not plausibility:
                subgroup = 'implausible_valid'
            elif label == "INVALID" and plausibility:
                subgroup = 'plausible_invalid'
            elif label == "INVALID" and not plausibility:
                subgroup = 'implausible_invalid'
            else:
                continue

            subgroups[subgroup]['total'] += 1
            if pred == label:
                subgroups[subgroup]['correct'] += 1

        # Calculate accuracies
        acc_plausible_valid = (subgroups['plausible_valid']['correct'] /
                               subgroups['plausible_valid']['total']
                               if subgroups['plausible_valid']['total'] > 0 else 0.0)

        acc_implausible_valid = (subgroups['implausible_valid']['correct'] /
                                  subgroups['implausible_valid']['total']
                                  if subgroups['implausible_valid']['total'] > 0 else 0.0)

        acc_plausible_invalid = (subgroups['plausible_invalid']['correct'] /
                                 subgroups['plausible_invalid']['total']
                                 if subgroups['plausible_invalid']['total'] > 0 else 0.0)

        acc_implausible_invalid = (subgroups['implausible_invalid']['correct'] /
                                   subgroups['implausible_invalid']['total']
                                   if subgroups['implausible_invalid']['total'] > 0 else 0.0)

        # Calculate content effect components
        # Intra-validity: difference within same validity label
        intra_valid_diff = abs(acc_plausible_valid - acc_implausible_valid)
        intra_invalid_diff = abs(acc_plausible_invalid - acc_implausible_invalid)
        content_effect_intra = (intra_valid_diff + intra_invalid_diff) / 2.0

        # Inter-validity: difference across validity labels
        inter_plausible_diff = abs(acc_plausible_valid - acc_plausible_invalid)
        inter_implausible_diff = abs(acc_implausible_valid - acc_implausible_invalid)
        content_effect_inter = (inter_plausible_diff + inter_implausible_diff) / 2.0

        # Total content effect
        tot_content_effect = (content_effect_intra + content_effect_inter) / 2.0

        return {
            'acc_plausible_valid': acc_plausible_valid,
            'acc_implausible_valid': acc_implausible_valid,
            'acc_plausible_invalid': acc_plausible_invalid,
            'acc_implausible_invalid': acc_implausible_invalid,
            'count_plausible_valid': f"{subgroups['plausible_valid']['correct']}/{subgroups['plausible_valid']['total']}",
            'count_implausible_valid': f"{subgroups['implausible_valid']['correct']}/{subgroups['implausible_valid']['total']}",
            'count_plausible_invalid': f"{subgroups['plausible_invalid']['correct']}/{subgroups['plausible_invalid']['total']}",
            'count_implausible_invalid': f"{subgroups['implausible_invalid']['correct']}/{subgroups['implausible_invalid']['total']}",
            'content_effect_intra': content_effect_intra,
            'content_effect_inter': content_effect_inter,
            'tot_content_effect': tot_content_effect
        }

    def print_results(self, metrics: Dict[str, Any], model_name: str = "Model"):
        """Print evaluation results with official SemEval metric names"""
        print(f"\n{'='*60}")
        print(f"Results for {model_name}")
        print(f"{'='*60}")

        # Determine scale for display
        scale_suffix = "%" if self.use_percentage_scale else ""
        scale_factor = 1 if self.use_percentage_scale else 100

        # Official Metric 1: ACC (Overall Accuracy)
        acc_display = metrics['overall_accuracy']
        print(f"ACC (Overall Accuracy): {acc_display:.2f}{scale_suffix} ({metrics['correct']}/{metrics['total']})")

        # Official Metric 2: TCE (Total Content Effect)
        tce = metrics['content_effect_bias']
        print(f"TCE (Total Content Effect): {tce:.4f}{scale_suffix}")

        # Official Metric 3: Primary Ranking Metric
        print(f"Primary Ranking Metric: {metrics['combined_metric']:.4f}")

        # Additional breakdown
        print(f"\nValidity Breakdown:")
        print(f"  Valid Accuracy: {metrics['valid_accuracy']:.4f}{scale_suffix}")
        print(f"  Invalid Accuracy: {metrics['invalid_accuracy']:.4f}{scale_suffix}")

        # Print plausibility metrics if available
        if 'acc_plausible_valid' in metrics:
            print(f"\nPlausibility × Validity Subgroups:")
            print(f"  Plausible + Valid: {metrics['acc_plausible_valid']:.4f}{scale_suffix} ({metrics['count_plausible_valid']})")
            print(f"  Implausible + Valid: {metrics['acc_implausible_valid']:.4f}{scale_suffix} ({metrics['count_implausible_valid']})")
            print(f"  Plausible + Invalid: {metrics['acc_plausible_invalid']:.4f}{scale_suffix} ({metrics['count_plausible_invalid']})")
            print(f"  Implausible + Invalid: {metrics['acc_implausible_invalid']:.4f}{scale_suffix} ({metrics['count_implausible_invalid']})")
            print(f"\nContent Effect Components:")
            print(f"  Intra-validity: {metrics['content_effect_intra']:.4f}{scale_suffix}")
            print(f"  Inter-validity: {metrics['content_effect_inter']:.4f}{scale_suffix}")
            print(f"  Total (TCE): {metrics['tot_content_effect']:.4f}{scale_suffix}")

        # Print overall plausibility metrics if available
        if 'acc_plausible' in metrics:
            print(f"\nOverall Plausibility Breakdown:")
            print(f"  Plausible Accuracy: {metrics['acc_plausible']:.4f}{scale_suffix} ({metrics['n_plausible']} examples)")
            print(f"  Implausible Accuracy: {metrics['acc_implausible']:.4f}{scale_suffix} ({metrics['n_implausible']} examples)")

        # Print Macro F1
        if 'macro_f1' in metrics:
            print(f"\nMacro F1 Score: {metrics['macro_f1']:.4f}{scale_suffix}")

        # Print sample counts
        print(f"\nSample Counts:")
        print(f"  Total: {metrics['n_samples']}")
        print(f"  Valid: {metrics['n_valid']}")
        print(f"  Invalid: {metrics['n_invalid']}")

        print(f"{'='*60}")


class CotExecutor:
    """Chain-of-Thought Executor - extracts VALID/INVALID from LLM response directly"""

    def __init__(self, config: Any, prompt_builder: Any):
        self.config = config
        self.prompt_builder = prompt_builder

        # Create execution directory with timestamp (results and logs in same dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.execution_dir = os.path.join(config.results_dir, f"execution_cot_{timestamp}")
        self.logs_dir = self.execution_dir

        os.makedirs(self.execution_dir, exist_ok=True)

        # Save system prompt
        prompt_file = os.path.join(self.execution_dir, "system_prompt.txt")
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(self.prompt_builder.system_prompt)

        print(f"✓ CotExecutor initialized")
        print(f"  Execution folder: {self.execution_dir}")
        print(f"  System prompt saved to: system_prompt.txt")

    def extract_prediction(self, response: str) -> str:
        """Extract VALID or INVALID from LLM response"""
        response_upper = response.upper()

        # Look for "Step 5 - Answer: VALID" or "Step 5 - Answer: INVALID"
        if "STEP 5" in response_upper and "ANSWER:" in response_upper:
            # Extract the line with Step 5
            lines = response.split('\n')
            for line in lines:
                if "STEP 5" in line.upper() and "ANSWER:" in line.upper():
                    if "VALID" in line.upper():
                        return "INVALID" if "INVALID" in line.upper() else "VALID"

        # Fallback: look for final VALID or INVALID
        # Check last occurrence
        valid_pos = response_upper.rfind("VALID")
        invalid_pos = response_upper.rfind("INVALID")

        if invalid_pos > valid_pos:
            return "INVALID"
        elif valid_pos >= 0:
            return "VALID"

        return "ERROR"

    def save_execution_log(self, item_id: str, syllogism: str, label: str,
                          response: str, prediction: str):
        """Save detailed log for each example"""
        log_file = os.path.join(self.logs_dir, f"{item_id}.txt")

        is_correct = (prediction == label) if label else "N/A"

        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"CHAIN-OF-THOUGHT EXECUTION LOG\n")
            f.write("="*80 + "\n\n")

            f.write(f"ID: {item_id}\n\n")

            f.write("SYLLOGISM:\n")
            f.write(f"{syllogism}\n\n")

            if label:
                f.write(f"GROUND TRUTH: {label}\n\n")

            f.write("LLM RESPONSE:\n")
            f.write("-"*80 + "\n")
            f.write(f"{response}\n")
            f.write("-"*80 + "\n\n")

            f.write(f"EXTRACTED PREDICTION: {prediction}\n\n")

            if label:
                f.write(f"CORRECT: {is_correct}\n\n")

            f.write("="*80 + "\n")

    def process_results(self, results: List[Dict]) -> List[Dict]:
        """Process LLM responses and extract predictions"""
        predictions = []

        print(f"\nProcessing {len(results)} responses...")

        for result in tqdm(results, desc="Extracting predictions"):
            item_id = result['id']
            response = result['response']
            syllogism = result.get('syllogism', result.get('text', ''))
            label = result.get('label', result.get('validity', None))

            # Convert boolean to string if needed
            if isinstance(label, bool):
                label = "VALID" if label else "INVALID"

            # Extract prediction from response
            prediction = self.extract_prediction(response)

            # Save log
            self.save_execution_log(item_id, syllogism, label, response, prediction)

            predictions.append({
                'id': item_id,
                'prediction': prediction
            })

        # Create summary
        self._create_summary(predictions, results)

        print(f"✓ Predictions extracted and saved to {self.logs_dir}")

        return predictions

    def _create_summary(self, predictions: List[Dict], results: List[Dict]):
        """Create execution summary"""
        summary_file = os.path.join(self.execution_dir, "execution_summary.txt")

        valid_count = sum(1 for p in predictions if p['prediction'] == 'VALID')
        invalid_count = sum(1 for p in predictions if p['prediction'] == 'INVALID')
        error_count = sum(1 for p in predictions if p['prediction'] == 'ERROR')

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("CHAIN-OF-THOUGHT EXECUTION SUMMARY\n")
            f.write("="*80 + "\n\n")

            f.write(f"Total examples: {len(predictions)}\n\n")

            f.write("Prediction Distribution:\n")
            f.write(f"  VALID:   {valid_count} ({valid_count/len(predictions)*100:.1f}%)\n")
            f.write(f"  INVALID: {invalid_count} ({invalid_count/len(predictions)*100:.1f}%)\n")
            f.write(f"  ERROR:   {error_count} ({error_count/len(predictions)*100:.1f}%)\n\n")

            f.write(f"Output directory: {self.execution_dir}\n\n")

            f.write("="*80 + "\n")
