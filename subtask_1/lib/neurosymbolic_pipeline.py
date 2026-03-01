"""
Main neuro-symbolic pipeline for syllogism validation.

Architecture:
1. LLM extracts syllogism structure (NLU task)
2. Python applies deterministic validity rules (no LLM reasoning)
3. If extraction fails, LLM fallback directly evaluates validity

This eliminates code generation errors and removes content effect from validity checking.
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from syllogism_structures import SyllogismStructure
from syllogism_extractor import SyllogismExtractor
from simplified_extractor import SimplifiedExtractor
from validity_checker import SyllogismValidityChecker
from extraction_reflexion import ExtractionReflexion
from llm_fallback import LLMFallbackEvaluator


class NeuroSymbolicPipeline:
    """
    Main pipeline combining LLM structure extraction with deterministic validity checking.
    Supports self-consistency with graduated temperatures, figure verification, and LLM fallback.
    """
    
    def __init__(
        self,
        bedrock_client,
        prompt_path: str = None,
        use_reflexion: bool = True,
        max_reflexion_attempts: int = 3,
        use_self_consistency: bool = False,
        num_consistency_samples: int = 3,
        temperature_schedule: List[float] = None,
        verify_figure: bool = False,
        use_fallback: bool = True,
        fallback_use_self_consistency: bool = False,
        fallback_num_samples: int = 3,
        results_dir: str = "neurosymbolic_results",
        run_name: str = None,
        verbose: bool = False,
        use_simplified_extractor: bool = False
    ):
        """
        Initialize the pipeline.
        
        Args:
            bedrock_client: BedrockClient instance
            prompt_path: Path to extraction prompt
            use_reflexion: Whether to use reflexion for extraction errors
            max_reflexion_attempts: Max attempts for reflexion
            use_self_consistency: Whether to use self-consistency voting for extraction
            num_consistency_samples: Number of samples for extraction self-consistency
            temperature_schedule: List of temperatures for each sample (default: [0.0, 0.3, 0.5, 0.7, 0.8])
            verify_figure: Whether to verify figure with a dedicated LLM call
            use_fallback: Whether to use LLM fallback when extraction fails
            fallback_use_self_consistency: Whether to use self-consistency for fallback
            fallback_num_samples: Number of samples for fallback self-consistency
            results_dir: Directory for results
            run_name: Optional name for this run (e.g., "train", "test")
            verbose: Whether to print debug information
            use_simplified_extractor: Whether to use SimplifiedExtractor (LLM extracts types+terms only,
                                      figure computed deterministically). Recommended for better accuracy.
        """
        self.client = bedrock_client
        self.use_reflexion = use_reflexion
        self.use_self_consistency = use_self_consistency
        self.num_consistency_samples = num_consistency_samples
        self.temperature_schedule = temperature_schedule
        self.verify_figure = verify_figure
        self.use_fallback = use_fallback
        self.fallback_use_self_consistency = fallback_use_self_consistency
        self.fallback_num_samples = fallback_num_samples
        self.verbose = verbose
        self.use_simplified_extractor = use_simplified_extractor
        
        # Initialize extractor based on mode
        if use_simplified_extractor:
            # Simplified extractor: LLM extracts types+terms, figure computed deterministically
            # Note: reflexion not yet supported with simplified extractor
            if use_reflexion:
                print("⚠ Warning: Reflexion not yet supported with simplified extractor. Disabling reflexion.")
                self.use_reflexion = False
            
            self.extractor = SimplifiedExtractor(
                bedrock_client,
                prompt_path,
                use_self_consistency=use_self_consistency,
                num_consistency_samples=num_consistency_samples,
                temperature_schedule=temperature_schedule,
                verbose=verbose
            )
        else:
            # Original extractor: LLM extracts everything including figure
            self.extractor = SyllogismExtractor(
                bedrock_client, 
                prompt_path,
                use_self_consistency=use_self_consistency if not use_reflexion else False,
                num_consistency_samples=num_consistency_samples,
                temperature_schedule=temperature_schedule,
                verify_figure=verify_figure if not use_reflexion else False,
                verbose=verbose
            )
        self.validity_checker = SyllogismValidityChecker()
        
        if use_reflexion:
            self.reflexion = ExtractionReflexion(
                bedrock_client, 
                self.extractor,
                max_reflexion_attempts,
                use_self_consistency=use_self_consistency,
                verify_figure=verify_figure,
                num_consistency_samples=num_consistency_samples,
                temperature_schedule=temperature_schedule,
                verbose=verbose
            )
        
        # Initialize fallback evaluator
        if use_fallback:
            self.fallback_evaluator = LLMFallbackEvaluator(
                bedrock_client,
                verbose=verbose
            )
        
        # Pipeline stats
        self.pipeline_stats = {
            "total": 0,
            "symbolic_success": 0,
            "fallback_used": 0,
            "fallback_correct": 0,
            "no_prediction": 0
        }
        
        # Setup results directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"neurosymbolic_{run_name}_{timestamp}" if run_name else f"neurosymbolic_{timestamp}"
        self.results_dir = os.path.join(results_dir, folder_name)
        # Results and logs in the same directory
        self.logs_dir = self.results_dir
        
        os.makedirs(self.results_dir, exist_ok=True)
        
        # File per debug in tempo reale (scritto via via durante training)
        self.debug_log_file = os.path.join(self.results_dir, "debug_failures.txt")
        self._init_debug_log()
        
        # Save the system prompt being used
        self._save_system_prompt()
        
        print(f"✓ NeuroSymbolic Pipeline initialized")
        print(f"  Extractor: {'Simplified (deterministic figure)' if use_simplified_extractor else 'Original (LLM figure)'}")
        print(f"  Use reflexion: {use_reflexion}")
        print(f"  Use self-consistency: {use_self_consistency}")
        if use_self_consistency:
            temps = temperature_schedule or [0.0, 0.3, 0.5, 0.7, 0.8]
            print(f"    Samples: {num_consistency_samples}, Temperatures: {temps[:num_consistency_samples]}")
        print(f"  Verify figure: {verify_figure}")
        print(f"  Use fallback: {use_fallback}")
        if use_fallback:
            print(f"    Fallback self-consistency: {fallback_use_self_consistency}")
            if fallback_use_self_consistency:
                print(f"    Fallback samples: {fallback_num_samples}")
        print(f"  Results dir: {self.results_dir}")
    
    def _save_system_prompt(self):
        """Save the system prompt being used to the results directory."""
        prompt_file = os.path.join(self.results_dir, "system_prompt.txt")
        
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("SYSTEM PROMPT USED FOR THIS RUN\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            # Get the extraction prompt from the extractor
            if hasattr(self.extractor, 'system_prompt'):
                f.write("EXTRACTION PROMPT:\n")
                f.write("-" * 40 + "\n")
                f.write(self.extractor.system_prompt)
                f.write("\n\n")
            
            # Get the figure verification prompt if used
            if hasattr(self.extractor, 'figure_verification_prompt') and self.extractor.figure_verification_prompt:
                f.write("=" * 80 + "\n")
                f.write("FIGURE VERIFICATION PROMPT:\n")
                f.write("-" * 40 + "\n")
                f.write(self.extractor.figure_verification_prompt)
                f.write("\n\n")
            
            # Get the fallback prompt if used
            if self.use_fallback and hasattr(self.fallback_evaluator, 'prompt_template'):
                f.write("=" * 80 + "\n")
                f.write("FALLBACK PROMPT:\n")
                f.write("-" * 40 + "\n")
                f.write(self.fallback_evaluator.prompt_template)
                f.write("\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("END OF PROMPTS\n")
            f.write("=" * 80 + "\n")
        
        print(f"  System prompt saved to: {prompt_file}")
        print(f"  Results dir: {self.results_dir}")
    
    def estimate_cost(self, num_syllogisms: int) -> Dict[str, Any]:
        """
        Estimate API costs for processing.
        
        Args:
            num_syllogisms: Number of syllogisms to process
            
        Returns:
            dict with cost estimates
        """
        base_calls = num_syllogisms
        
        if self.use_self_consistency:
            calls_per_attempt = self.num_consistency_samples
        else:
            calls_per_attempt = 1
        
        # Figure verification adds 1 call per syllogism
        verification_calls = base_calls if self.verify_figure else 0
        
        if self.use_reflexion:
            # Assume average 1.5 attempts per syllogism with reflexion
            avg_attempts = 1.5
            extraction_calls = int(base_calls * avg_attempts * calls_per_attempt)
            total_calls = extraction_calls + verification_calls
        else:
            extraction_calls = base_calls * calls_per_attempt
            total_calls = extraction_calls + verification_calls
        
        return {
            "num_syllogisms": num_syllogisms,
            "use_reflexion": self.use_reflexion,
            "use_self_consistency": self.use_self_consistency,
            "num_consistency_samples": self.num_consistency_samples if self.use_self_consistency else 1,
            "verify_figure": self.verify_figure,
            "extraction_calls": extraction_calls,
            "verification_calls": verification_calls,
            "estimated_api_calls": total_calls,
            "overhead_vs_baseline": total_calls / base_calls if base_calls > 0 else 0
        }
    
    def _init_debug_log(self):
        """Inizializza il file di debug per errori e mismatch."""
        with open(self.debug_log_file, 'w', encoding='utf-8') as f:
            f.write("=" * 100 + "\n")
            f.write("DEBUG LOG - ERRORI E MISMATCH (scritto in tempo reale)\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 100 + "\n\n")
    
    def _log_failure(self, result: Dict[str, Any], failure_type: str):
        """
        Scrive un errore o mismatch nel file di debug in tempo reale.
        
        Args:
            result: Il risultato del processing
            failure_type: "EXTRACTION_ERROR", "FALLBACK_USED", "MISMATCH_FALSE_VALID", "MISMATCH_FALSE_INVALID"
        """
        with open(self.debug_log_file, 'a', encoding='utf-8') as f:
            f.write("-" * 100 + "\n")
            f.write(f"[{failure_type}] ID: {result.get('id', 'N/A')}\n")
            f.write("-" * 100 + "\n\n")
            
            # 1. Sillogismo originale
            f.write("### SILLOGISMO:\n")
            f.write(f"{result.get('text', 'N/A')}\n\n")
            
            # 2. Ground truth (se disponibile)
            if result.get('ground_truth'):
                f.write("### GROUND TRUTH:\n")
                f.write(f"  Validity: {result.get('ground_truth')}\n")
                if result.get('plausibility'):
                    f.write(f"  Plausibility: {result.get('plausibility')}\n")
                f.write("\n")
            
            # 3. Method used
            f.write("### METODO:\n")
            f.write(f"  Method: {result.get('method', 'N/A')}\n")
            f.write(f"  Confidence: {result.get('confidence', 0):.2f}\n\n")
            
            # 4. Struttura estratta (JSON) - only if symbolic
            if result.get('structure'):
                f.write("### STRUTTURA ESTRATTA (JSON):\n")
                f.write(json.dumps(result['structure'], indent=2) + "\n\n")
            elif result.get('method') == 'fallback':
                f.write("### STRUTTURA ESTRATTA: FALLITA (usato fallback LLM)\n")
                f.write(f"  Errore estrazione: {result.get('error', 'Unknown')}\n")
                f.write(f"  Tentativi: {result.get('extraction_attempts', 1)}\n\n")
            else:
                f.write("### STRUTTURA ESTRATTA: FALLITA\n")
                f.write(f"  Errore: {result.get('error', 'Unknown')}\n")
                f.write(f"  Tentativi: {result.get('extraction_attempts', 1)}\n\n")
            
            # 5. Passi logici del validity checker (only if symbolic)
            if result.get('validity_details'):
                f.write("### PASSI LOGICI (Validity Checker):\n")
                details = result['validity_details']
                
                f.write(f"  Form: {details.get('form', 'N/A')}\n")
                f.write(f"  Figure: {details.get('figure', 'N/A')}\n")
                f.write(f"  Mood: {details.get('mood', 'N/A')}\n")
                f.write(f"  Valid: {details.get('valid', 'N/A')}\n")
                
                if details.get('valid'):
                    f.write(f"  Nome forma: {details.get('form_name', 'N/A')}\n")
                else:
                    f.write(f"  Ragione invalidità: {details.get('reason', 'N/A')}\n")
                
                if details.get('requires_existential_import'):
                    f.write(f"  Richiede existential import: Sì\n")
                f.write("\n")
            
            # 5.5 Fallback info (if used)
            if result.get('fallback_info'):
                f.write("### FALLBACK INFO:\n")
                fb = result['fallback_info']
                if fb.get('vote_counts'):
                    f.write(f"  Vote counts: {fb.get('vote_counts')}\n")
                    f.write(f"  Temperatures: {fb.get('temperatures_used', [])}\n")
                    if fb.get('had_disagreement'):
                        f.write(f"  ⚠ Disagreement in votes\n")
                f.write("\n")
            
            # 6. Prediction vs Ground Truth
            f.write("### RISULTATO:\n")
            f.write(f"  Prediction: {result.get('prediction', 'N/A')}\n")
            if result.get('ground_truth'):
                f.write(f"  Ground Truth: {result.get('ground_truth')}\n")
                if result.get('prediction') == result.get('ground_truth'):
                    f.write(f"  Match: ✓ CORRETTO\n")
                else:
                    f.write(f"  Match: ✗ ERRORE\n")
            f.write("\n")
            
            # 6.5 Self-consistency info (if used for extraction)
            if result.get('self_consistency'):
                sc = result['self_consistency']
                f.write("### SELF-CONSISTENCY (Extraction):\n")
                f.write(f"  Successful samples: {sc.get('successful_samples', 'N/A')}\n")
                f.write(f"  Failed samples: {sc.get('failed_samples', 'N/A')}\n")
                if sc.get('vote_counts'):
                    f.write(f"  Vote counts: {sc.get('vote_counts')}\n")
                f.write(f"  Selected form: {sc.get('selected_form', 'N/A')}\n")
                if sc.get('had_disagreement'):
                    f.write(f"  ⚠ Disagreement: {sc.get('all_forms', [])}\n")
                f.write("\n")
            
            # 7. Analisi dell'errore
            if failure_type == "EXTRACTION_ERROR":
                f.write("### ANALISI ERRORE:\n")
                f.write("  Il LLM non è riuscito a estrarre la struttura del sillogismo.\n")
                f.write("  Nessun fallback disponibile o fallback disabilitato.\n")
                f.write(f"  Errore specifico: {result.get('error', 'Unknown')}\n\n")
            
            elif failure_type == "FALLBACK_USED":
                f.write("### ANALISI:\n")
                f.write("  Estrazione fallita, usato fallback LLM per valutazione diretta.\n")
                if result.get('prediction') == result.get('ground_truth'):
                    f.write("  Il fallback ha predetto correttamente.\n\n")
                else:
                    f.write("  Il fallback ha predetto erroneamente.\n\n")
            
            elif failure_type == "MISMATCH_FALSE_VALID":
                f.write("### ANALISI ERRORE:\n")
                f.write("  Il sistema ha predetto VALID ma il ground truth è INVALID.\n")
                if result.get('method') == 'symbolic':
                    f.write("  Possibili cause:\n")
                    f.write("    - Estrazione errata della struttura (tipo proposizione sbagliato)\n")
                    f.write("    - Middle term identificato erroneamente\n")
                    f.write("    - Figura calcolata erroneamente\n\n")
                else:
                    f.write("  Il fallback LLM ha valutato erroneamente come VALID.\n\n")
            
            elif failure_type == "MISMATCH_FALSE_INVALID":
                f.write("### ANALISI ERRORE:\n")
                f.write("  Il sistema ha predetto INVALID ma il ground truth è VALID.\n")
                if result.get('method') == 'symbolic':
                    f.write("  Possibili cause:\n")
                    f.write("    - Estrazione errata della struttura (tipo proposizione sbagliato)\n")
                    f.write("    - Middle term identificato erroneamente\n")
                    f.write("    - Figura calcolata erroneamente\n")
                    f.write("    - Forma valida non riconosciuta (controllare le 24 forme)\n\n")
                else:
                    f.write("  Il fallback LLM ha valutato erroneamente come INVALID.\n\n")
            
            f.write("\n")
    
    def process_syllogism(self, syllogism_text: str, syllogism_id: str = None) -> Dict[str, Any]:
        """
        Process a single syllogism through the neuro-symbolic pipeline.
        Uses LLM fallback if extraction fails and fallback is enabled.
        
        Args:
            syllogism_text: The natural language syllogism
            syllogism_id: Optional identifier
            
        Returns:
            dict with extraction results and validity determination
        """
        self.pipeline_stats["total"] += 1
        
        result = {
            "id": syllogism_id,
            "text": syllogism_text,
            "extraction_success": False,
            "validity": None,
            "prediction": None,
            "method": None,  # "symbolic" or "fallback"
            "confidence": 0.0,
            "error": None,
            "structure": None,
            "validity_details": None,
            "extraction_attempts": 1,
            "self_consistency": None,
            "fallback_info": None
        }
        
        # Stage 1: Extract structure using LLM
        extraction_failed = False
        try:
            if self.use_reflexion:
                extraction = self.reflexion.extract_with_reflexion(syllogism_text)
                result["extraction_attempts"] = extraction.get("attempts", 1)
                # Get self-consistency info from last successful attempt
                if extraction.get("history"):
                    for attempt in reversed(extraction["history"]):
                        if attempt.get("self_consistency"):
                            result["self_consistency"] = attempt["self_consistency"]
                            break
            else:
                extraction = self.extractor.extract(syllogism_text)
                if extraction.get("self_consistency"):
                    result["self_consistency"] = extraction["self_consistency"]
            
            if extraction.get("success"):
                result["extraction_success"] = True
                structure = extraction["structure"]
                
                # Safety check: ensure structure is not None
                if structure is None:
                    extraction_failed = True
                    result["extraction_success"] = False
                    result["error"] = "BUG: extraction success but structure is None"
                else:
                    result["structure"] = structure.to_dict()
            else:
                extraction_failed = True
                result["error"] = extraction.get("error", "Extraction failed")
                
        except Exception as e:
            extraction_failed = True
            result["error"] = f"Extraction error: {str(e)}"
        
        # Stage 2: Check validity using deterministic rules (if extraction succeeded)
        if result["extraction_success"]:
            try:
                # For simplified extractor, validity is already computed by post-processor
                if self.use_simplified_extractor:
                    # Validity already computed during extraction
                    validity_str = extraction.get("validity")
                    if validity_str is True or validity_str == "VALID":
                        result["validity"] = "VALID"
                    elif validity_str is False or validity_str == "INVALID":
                        result["validity"] = "INVALID"
                    else:
                        result["validity"] = "VALID" if extraction.get("validity") else "INVALID"
                    
                    result["prediction"] = result["validity"]
                    result["validity_details"] = {
                        "valid": result["validity"] == "VALID",
                        "form": extraction.get("form"),
                        "figure": extraction.get("figure"),
                        "mood": extraction.get("mood"),
                        "reason": extraction.get("validity_reason"),
                        "form_name": extraction.get("form_name"),
                        "terms": extraction.get("terms"),
                        "postprocessor_corrections": extraction.get("corrections", [])
                    }
                else:
                    # Original extractor: use validity checker
                    validity_result = self.validity_checker.check_validity(structure)
                    result["validity"] = "VALID" if validity_result["valid"] else "INVALID"
                    result["prediction"] = result["validity"]
                    result["validity_details"] = validity_result
                
                result["method"] = "symbolic"
                result["confidence"] = 0.95  # High confidence for symbolic
                self.pipeline_stats["symbolic_success"] += 1
                
                if self.verbose:
                    print(f"  ✓ Symbolic validation: {result['prediction']}")
                
            except Exception as e:
                result["error"] = f"Validity check error: {str(e)}"
                extraction_failed = True  # Treat as extraction failure for fallback
        
        # Stage 3: Use LLM fallback if extraction failed and fallback is enabled
        if extraction_failed and self.use_fallback:
            if self.verbose:
                print(f"  ⚠ Extraction failed, using LLM fallback...")
            
            self.pipeline_stats["fallback_used"] += 1
            
            try:
                if self.fallback_use_self_consistency:
                    fallback_result = self.fallback_evaluator.evaluate_with_self_consistency(
                        syllogism_text,
                        num_samples=self.fallback_num_samples
                    )
                else:
                    fallback_result = self.fallback_evaluator.evaluate(syllogism_text)
                
                result["prediction"] = fallback_result["prediction"]
                result["validity"] = fallback_result["prediction"]
                result["method"] = "fallback"
                result["confidence"] = 0.70  # Lower confidence for fallback
                result["fallback_info"] = fallback_result
                
                if self.verbose:
                    print(f"  → Fallback prediction: {result['prediction']}")
                
            except Exception as e:
                result["error"] = f"Fallback error: {str(e)}"
                result["method"] = "failed"
                self.pipeline_stats["no_prediction"] += 1
        
        elif extraction_failed and not self.use_fallback:
            result["method"] = "failed"
            self.pipeline_stats["no_prediction"] += 1
        
        return result
    
    def run(self, syllogisms: List[Dict[str, Any]], verbose: bool = True) -> List[Dict[str, Any]]:
        """
        Process a batch of syllogisms.
        
        Args:
            syllogisms: List of syllogism dicts with 'id', 'syllogism'/'text', etc.
            verbose: Whether to show progress
            
        Returns:
            List of result dicts
        """
        results = []
        
        iterator = tqdm(syllogisms, desc="Processing") if verbose else syllogisms
        
        for item in iterator:
            # Get text (handle different field names)
            text = item.get("syllogism") or item.get("text", "")
            syllogism_id = item.get("id")
            
            # Process
            result = self.process_syllogism(text, syllogism_id)
            
            # Add ground truth if available
            if "validity" in item:
                gt = item["validity"]
                if isinstance(gt, bool):
                    result["ground_truth"] = "VALID" if gt else "INVALID"
                else:
                    result["ground_truth"] = gt
            elif "label" in item:
                result["ground_truth"] = item["label"]
            
            # Add plausibility if available
            if "plausibility" in item:
                plaus = item["plausibility"]
                if isinstance(plaus, bool):
                    result["plausibility"] = "PLAUSIBLE" if plaus else "IMPLAUSIBLE"
                else:
                    result["plausibility"] = plaus
            
            results.append(result)
            
            # Save individual log
            self._save_log(result)
            
            # Log errori e mismatch in tempo reale (solo durante training con ground truth)
            if result.get("ground_truth"):
                # Track fallback correctness
                if result.get("method") == "fallback":
                    if result["prediction"] == result["ground_truth"]:
                        self.pipeline_stats["fallback_correct"] += 1
                    # Log fallback usage
                    self._log_failure(result, "FALLBACK_USED")
                elif not result["extraction_success"] and result["prediction"] is None:
                    # Extraction failed and no fallback
                    self._log_failure(result, "EXTRACTION_ERROR")
                elif result["prediction"] != result["ground_truth"]:
                    # Mismatch prediction vs ground truth
                    if result["prediction"] == "VALID":
                        self._log_failure(result, "MISMATCH_FALSE_VALID")
                    else:
                        self._log_failure(result, "MISMATCH_FALSE_INVALID")
        
        # Generate summary
        self._generate_summary(results)
        
        return results
    
    def _save_log(self, result: Dict[str, Any]):
        """Save individual result log."""
        if not result.get("id"):
            return
        
        log_file = os.path.join(self.logs_dir, f"{result['id']}.json")
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
    
    def _generate_summary(self, results: List[Dict[str, Any]]):
        """Generate summary statistics."""
        total = len(results)
        extraction_success = sum(1 for r in results if r["extraction_success"])
        
        # Count by method
        symbolic_count = sum(1 for r in results if r.get("method") == "symbolic")
        fallback_count = sum(1 for r in results if r.get("method") == "fallback")
        failed_count = sum(1 for r in results if r.get("method") == "failed" or r["prediction"] is None)
        
        # Count predictions
        valid_pred = sum(1 for r in results if r["prediction"] == "VALID")
        invalid_pred = sum(1 for r in results if r["prediction"] == "INVALID")
        errors = sum(1 for r in results if r["prediction"] is None)
        
        # Count failures for debug log
        extraction_errors = sum(1 for r in results if not r["extraction_success"] and r.get("ground_truth") and r["prediction"] is None)
        false_valid = sum(1 for r in results if r.get("ground_truth") and r["prediction"] == "VALID" and r["ground_truth"] == "INVALID")
        false_invalid = sum(1 for r in results if r.get("ground_truth") and r["prediction"] == "INVALID" and r["ground_truth"] == "VALID")
        
        # =====================================================================
        # OFFICIAL EVALUATION METRICS (same as evaluation_script.py)
        # =====================================================================
        
        with_gt = [r for r in results if r.get("ground_truth")]
        
        # Initialize all metrics
        accuracy = None
        symbolic_accuracy = None
        fallback_accuracy = None
        
        # 4 Subgroup accuracies (for content effect)
        acc_valid_plausible = None      # VP
        acc_valid_implausible = None    # VI
        acc_invalid_plausible = None    # IP
        acc_invalid_implausible = None  # II
        
        # Content effect components
        ce_intra = None
        ce_inter = None
        total_content_effect = None
        combined_score = None
        
        # Subgroup counts
        n_vp = n_vi = n_ip = n_ii = 0
        
        if with_gt:
            # Overall accuracy
            correct = sum(1 for r in with_gt if r["prediction"] == r["ground_truth"])
            accuracy = (correct / len(with_gt)) * 100  # As percentage
            
            # Accuracy by method
            symbolic_with_gt = [r for r in with_gt if r.get("method") == "symbolic"]
            fallback_with_gt = [r for r in with_gt if r.get("method") == "fallback"]
            
            if symbolic_with_gt:
                symbolic_correct = sum(1 for r in symbolic_with_gt if r["prediction"] == r["ground_truth"])
                symbolic_accuracy = (symbolic_correct / len(symbolic_with_gt)) * 100
            
            if fallback_with_gt:
                fallback_correct = sum(1 for r in fallback_with_gt if r["prediction"] == r["ground_truth"])
                fallback_accuracy = (fallback_correct / len(fallback_with_gt)) * 100
            
            # =====================================================================
            # 4 SUBGROUP ACCURACIES (Official evaluation format)
            # =====================================================================
            
            # Helper function to calculate subgroup accuracy
            def calc_subgroup_acc(results_list, validity_val, plausibility_val):
                subgroup = [r for r in results_list 
                           if r.get("ground_truth") == validity_val 
                           and r.get("plausibility") == plausibility_val]
                if not subgroup:
                    return None, 0
                correct = sum(1 for r in subgroup if r["prediction"] == r["ground_truth"])
                return (correct / len(subgroup)) * 100, len(subgroup)
            
            # Calculate all 4 subgroups
            acc_valid_plausible, n_vp = calc_subgroup_acc(with_gt, "VALID", "PLAUSIBLE")
            acc_valid_implausible, n_vi = calc_subgroup_acc(with_gt, "VALID", "IMPLAUSIBLE")
            acc_invalid_plausible, n_ip = calc_subgroup_acc(with_gt, "INVALID", "PLAUSIBLE")
            acc_invalid_implausible, n_ii = calc_subgroup_acc(with_gt, "INVALID", "IMPLAUSIBLE")
            
            # =====================================================================
            # CONTENT EFFECT CALCULATION (Official formula)
            # =====================================================================
            
            # Check if we have all 4 subgroups
            subgroup_accs = [acc_valid_plausible, acc_valid_implausible, 
                           acc_invalid_plausible, acc_invalid_implausible]
            
            if all(acc is not None for acc in subgroup_accs):
                # CE_intra: within same validity label
                # |Acc(VP) - Acc(VI)| + |Acc(IP) - Acc(II)| / 2
                intra_valid_diff = abs(acc_valid_plausible - acc_valid_implausible)
                intra_invalid_diff = abs(acc_invalid_plausible - acc_invalid_implausible)
                ce_intra = (intra_valid_diff + intra_invalid_diff) / 2.0
                
                # CE_inter: across validity labels
                # |Acc(VP) - Acc(IP)| + |Acc(VI) - Acc(II)| / 2
                inter_plausible_diff = abs(acc_valid_plausible - acc_invalid_plausible)
                inter_implausible_diff = abs(acc_valid_implausible - acc_invalid_implausible)
                ce_inter = (inter_plausible_diff + inter_implausible_diff) / 2.0
                
                # Total content effect
                total_content_effect = (ce_intra + ce_inter) / 2.0
                
                # =====================================================================
                # COMBINED SCORE (Official formula)
                # Score = Accuracy / (1 + ln(1 + ContentEffect))
                # =====================================================================
                import math
                log_penalty = math.log(1 + total_content_effect)
                combined_score = accuracy / (1 + log_penalty)
        
        # =====================================================================
        # SAVE SUMMARY (JSON)
        # =====================================================================
        
        summary = {
            "total": total,
            "extraction_success": extraction_success,
            "extraction_rate": extraction_success / total if total > 0 else 0,
            "methods": {
                "symbolic": symbolic_count,
                "fallback": fallback_count,
                "failed": failed_count
            },
            "predictions": {
                "VALID": valid_pred,
                "INVALID": invalid_pred,
                "ERROR": errors
            },
            "failures_logged": {
                "extraction_errors": extraction_errors,
                "false_valid": false_valid,
                "false_invalid": false_invalid,
                "total_failures": extraction_errors + false_valid + false_invalid
            },
            # Official evaluation metrics
            "official_metrics": {
                "accuracy": round(accuracy, 4) if accuracy is not None else None,
                "content_effect": round(total_content_effect, 4) if total_content_effect is not None else None,
                "combined_score": round(combined_score, 4) if combined_score is not None else None
            },
            # Detailed breakdown
            "accuracy_by_method": {
                "overall": round(accuracy, 4) if accuracy is not None else None,
                "symbolic": round(symbolic_accuracy, 4) if symbolic_accuracy is not None else None,
                "fallback": round(fallback_accuracy, 4) if fallback_accuracy is not None else None
            },
            "subgroup_accuracies": {
                "valid_plausible": {"accuracy": round(acc_valid_plausible, 4) if acc_valid_plausible is not None else None, "n": n_vp},
                "valid_implausible": {"accuracy": round(acc_valid_implausible, 4) if acc_valid_implausible is not None else None, "n": n_vi},
                "invalid_plausible": {"accuracy": round(acc_invalid_plausible, 4) if acc_invalid_plausible is not None else None, "n": n_ip},
                "invalid_implausible": {"accuracy": round(acc_invalid_implausible, 4) if acc_invalid_implausible is not None else None, "n": n_ii}
            },
            "content_effect_breakdown": {
                "ce_intra": round(ce_intra, 4) if ce_intra is not None else None,
                "ce_inter": round(ce_inter, 4) if ce_inter is not None else None,
                "total": round(total_content_effect, 4) if total_content_effect is not None else None
            },
            "pipeline_stats": self.pipeline_stats,
            "timestamp": datetime.now().isoformat()
        }
        
        summary_file = os.path.join(self.results_dir, "summary.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        # =====================================================================
        # SAVE TEXT REPORT (Human readable)
        # =====================================================================
        
        report_file = os.path.join(self.results_dir, "report.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("NEURO-SYMBOLIC PIPELINE RESULTS\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            # Basic stats
            f.write(f"Total Syllogisms: {total}\n")
            f.write(f"Extraction Success: {extraction_success} ({extraction_success/total*100:.1f}%)\n\n")
            
            f.write("Methods Used:\n")
            f.write(f"  Symbolic: {symbolic_count} ({symbolic_count/total*100:.1f}%)\n")
            f.write(f"  Fallback: {fallback_count} ({fallback_count/total*100:.1f}%)\n")
            f.write(f"  Failed:   {failed_count} ({failed_count/total*100:.1f}%)\n\n")
            
            f.write("Predictions:\n")
            f.write(f"  VALID:   {valid_pred}\n")
            f.write(f"  INVALID: {invalid_pred}\n")
            f.write(f"  ERROR:   {errors}\n\n")
            
            # =====================================================================
            # OFFICIAL EVALUATION SECTION
            # =====================================================================
            
            f.write("=" * 80 + "\n")
            f.write("OFFICIAL EVALUATION METRICS\n")
            f.write("=" * 80 + "\n\n")
            
            if combined_score is not None:
                f.write("┌─────────────────────────────────────────────────────────────┐\n")
                f.write(f"│  COMBINED SCORE: {combined_score:>8.2f}                                │\n")
                f.write(f"│  Accuracy:       {accuracy:>8.2f}%                               │\n")
                f.write(f"│  Content Effect: {total_content_effect:>8.2f}                                │\n")
                f.write("└─────────────────────────────────────────────────────────────┘\n\n")
                
                f.write("Formula: Score = Accuracy / (1 + ln(1 + ContentEffect))\n\n")
            elif accuracy is not None:
                f.write(f"Overall Accuracy: {accuracy:.2f}%\n")
                f.write("(Content effect not available - missing plausibility labels)\n\n")
            else:
                f.write("(No ground truth available for evaluation)\n\n")
            
            # Accuracy by method
            if accuracy is not None:
                f.write("-" * 40 + "\n")
                f.write("ACCURACY BY METHOD:\n")
                f.write("-" * 40 + "\n")
                f.write(f"  Overall:  {accuracy:>6.2f}%\n")
                if symbolic_accuracy is not None:
                    f.write(f"  Symbolic: {symbolic_accuracy:>6.2f}% (n={len(symbolic_with_gt)})\n")
                if fallback_accuracy is not None:
                    f.write(f"  Fallback: {fallback_accuracy:>6.2f}% (n={len(fallback_with_gt)})\n")
                f.write("\n")
            
            # 4 Subgroup accuracies
            if all(acc is not None for acc in [acc_valid_plausible, acc_valid_implausible, 
                                                acc_invalid_plausible, acc_invalid_implausible]):
                f.write("-" * 40 + "\n")
                f.write("4 SUBGROUP ACCURACIES:\n")
                f.write("-" * 40 + "\n")
                f.write("                    PLAUSIBLE    IMPLAUSIBLE\n")
                f.write(f"  VALID:            {acc_valid_plausible:>6.2f}% (n={n_vp:>3})  {acc_valid_implausible:>6.2f}% (n={n_vi:>3})\n")
                f.write(f"  INVALID:          {acc_invalid_plausible:>6.2f}% (n={n_ip:>3})  {acc_invalid_implausible:>6.2f}% (n={n_ii:>3})\n")
                f.write("\n")
                
                # Content effect breakdown
                f.write("-" * 40 + "\n")
                f.write("CONTENT EFFECT BREAKDOWN:\n")
                f.write("-" * 40 + "\n")
                f.write(f"  CE_intra (within validity):  {ce_intra:>6.2f}\n")
                f.write(f"    |VP - VI| = |{acc_valid_plausible:.2f} - {acc_valid_implausible:.2f}| = {abs(acc_valid_plausible - acc_valid_implausible):.2f}\n")
                f.write(f"    |IP - II| = |{acc_invalid_plausible:.2f} - {acc_invalid_implausible:.2f}| = {abs(acc_invalid_plausible - acc_invalid_implausible):.2f}\n")
                f.write(f"\n")
                f.write(f"  CE_inter (across validity):  {ce_inter:>6.2f}\n")
                f.write(f"    |VP - IP| = |{acc_valid_plausible:.2f} - {acc_invalid_plausible:.2f}| = {abs(acc_valid_plausible - acc_invalid_plausible):.2f}\n")
                f.write(f"    |VI - II| = |{acc_valid_implausible:.2f} - {acc_invalid_implausible:.2f}| = {abs(acc_valid_implausible - acc_invalid_implausible):.2f}\n")
                f.write(f"\n")
                f.write(f"  Total Content Effect: {total_content_effect:>6.2f}\n")
                f.write(f"    = (CE_intra + CE_inter) / 2 = ({ce_intra:.2f} + {ce_inter:.2f}) / 2\n")
                f.write("\n")
            
            # Failures logged
            total_failures = extraction_errors + false_valid + false_invalid
            if total_failures > 0:
                f.write("-" * 40 + "\n")
                f.write("FAILURES (see debug_failures.txt):\n")
                f.write("-" * 40 + "\n")
                f.write(f"  Extraction Errors: {extraction_errors}\n")
                f.write(f"  False VALID:       {false_valid}\n")
                f.write(f"  False INVALID:     {false_invalid}\n")
                f.write(f"  Total:             {total_failures}\n\n")
            
            f.write("=" * 80 + "\n")
        
        # =====================================================================
        # CONSOLE OUTPUT
        # =====================================================================
        
        print(f"\n✓ Summary saved to: {self.results_dir}")
        print(f"  Methods: {symbolic_count} symbolic, {fallback_count} fallback, {failed_count} failed")
        
        if combined_score is not None:
            print("\n  ┌─────────────────────────────────────┐")
            print(f"  │  COMBINED SCORE: {combined_score:>8.2f}           │")
            print(f"  │  Accuracy:       {accuracy:>8.2f}%          │")
            print(f"  │  Content Effect: {total_content_effect:>8.2f}           │")
            print("  └─────────────────────────────────────┘")
            
            if symbolic_accuracy is not None and fallback_accuracy is not None:
                print(f"\n  Accuracy breakdown: Symbolic {symbolic_accuracy:.2f}%, Fallback {fallback_accuracy:.2f}%")
        elif accuracy is not None:
            print(f"  Accuracy: {accuracy:.2f}%")
        
        # Finalizza il debug log
        total_failures = extraction_errors + false_valid + false_invalid
        with open(self.debug_log_file, 'a', encoding='utf-8') as f:
            f.write("\n" + "=" * 100 + "\n")
            f.write("RIEPILOGO FINALE\n")
            f.write("=" * 100 + "\n")
            f.write(f"Methods: {symbolic_count} symbolic, {fallback_count} fallback, {failed_count} failed\n")
            if combined_score is not None:
                f.write(f"\nOFFICIAL METRICS:\n")
                f.write(f"  Combined Score:  {combined_score:.2f}\n")
                f.write(f"  Accuracy:        {accuracy:.2f}%\n")
                f.write(f"  Content Effect:  {total_content_effect:.2f}\n")
            f.write(f"\nFAILURES:\n")
            f.write(f"  Extraction Errors: {extraction_errors}\n")
            f.write(f"  False VALID:       {false_valid}\n")
            f.write(f"  False INVALID:     {false_invalid}\n")
            f.write(f"  TOTAL:             {total_failures}\n")
        
        if total_failures > 0:
            print(f"\n  Failures logged: {total_failures} (see debug_failures.txt)")
    
    def save_predictions(self, results: List[Dict[str, Any]], output_file: str = None):
        """
        Save predictions in official submission format.
        
        Official format requires:
        - "validity": boolean (true/false), NOT string "VALID"/"INVALID"
        """
        if output_file is None:
            output_file = os.path.join(self.results_dir, "predictions.json")
        
        predictions = []
        for r in results:
            if r["prediction"] is not None:
                # Convert string prediction to boolean for official format
                # "VALID" -> true, "INVALID" -> false
                validity_bool = r["prediction"] == "VALID"
                predictions.append({
                    "id": r["id"],
                    "validity": validity_bool  # Official format: boolean
                })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(predictions, f, indent=2)
        
        print(f"✓ Predictions saved to: {output_file} (official format: validity=boolean)")
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """
        Get pipeline statistics.
        
        Returns:
            dict with total, symbolic_success, fallback_used, etc.
        """
        total = self.pipeline_stats["total"]
        return {
            **self.pipeline_stats,
            "symbolic_rate": self.pipeline_stats["symbolic_success"] / max(1, total),
            "fallback_rate": self.pipeline_stats["fallback_used"] / max(1, total),
            "fallback_accuracy": (
                self.pipeline_stats["fallback_correct"] / max(1, self.pipeline_stats["fallback_used"])
                if self.pipeline_stats["fallback_used"] > 0 else None
            )
        }
    
    def reset_stats(self):
        """Reset pipeline statistics."""
        self.pipeline_stats = {
            "total": 0,
            "symbolic_success": 0,
            "fallback_used": 0,
            "fallback_correct": 0,
            "no_prediction": 0
        }
        if self.use_fallback:
            self.fallback_evaluator.reset_stats()


# Quick test
if __name__ == "__main__":
    print("NeuroSymbolic Pipeline module loaded.")
    print("Use with BedrockClient to process syllogisms.")
