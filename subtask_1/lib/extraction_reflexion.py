"""
Reflexion module for correcting structure extraction errors.
Supports self-consistency and figure verification for improved extraction accuracy.
"""

import os
import json
from typing import Dict, Any, List, Optional
from syllogism_extractor import SyllogismExtractor
from syllogism_structures import SyllogismStructure


class ExtractionReflexion:
    """
    Reflexion module for correcting structure extraction errors.
    Uses self-correction when validation fails.
    Supports self-consistency with graduated temperatures and figure verification.
    """
    
    # Default temperature schedule for self-consistency
    DEFAULT_TEMPERATURE_SCHEDULE = [0.0, 0.3, 0.5, 0.7, 0.8]
    
    def __init__(
        self, 
        bedrock_client, 
        extractor: SyllogismExtractor, 
        max_attempts: int = 3,
        use_self_consistency: bool = False,
        num_consistency_samples: int = 3,
        temperature_schedule: List[float] = None,
        verify_figure: bool = False,
        verbose: bool = False
    ):
        """
        Initialize the reflexion module.
        
        Args:
            bedrock_client: BedrockClient instance
            extractor: SyllogismExtractor instance
            max_attempts: Maximum extraction attempts
            use_self_consistency: Whether to use self-consistency voting
            num_consistency_samples: Number of samples for self-consistency
            temperature_schedule: List of temperatures for each sample (default: [0.0, 0.3, 0.5, 0.7, 0.8])
            verify_figure: Whether to verify figure with a dedicated LLM call
            verbose: Whether to print debug information
        """
        self.client = bedrock_client
        self.extractor = extractor
        self.max_attempts = max_attempts
        self.use_self_consistency = use_self_consistency
        self.num_consistency_samples = num_consistency_samples
        self.verify_figure = verify_figure
        self.verbose = verbose
        
        # Use provided schedule or default graduated temperatures
        if temperature_schedule is not None:
            self.temperature_schedule = temperature_schedule
        else:
            self.temperature_schedule = self.DEFAULT_TEMPERATURE_SCHEDULE
        
        # Load reflexion prompt
        self.reflexion_system_prompt = self._load_reflexion_prompt()
    
    def _get_temperatures(self, num_samples: int) -> List[float]:
        """
        Get the temperature schedule for the given number of samples.
        
        If num_samples exceeds schedule length, repeat the last temperature.
        
        Args:
            num_samples: Number of samples to generate
            
        Returns:
            List of temperatures for each sample
        """
        schedule = self.temperature_schedule
        
        if num_samples <= len(schedule):
            return schedule[:num_samples]
        else:
            # Extend with last temperature if needed
            extra = num_samples - len(schedule)
            return schedule + [schedule[-1]] * extra
    
    def _load_reflexion_prompt(self) -> str:
        """Load the reflexion system prompt from file."""
        prompt_path = os.path.join(
            os.path.dirname(__file__),
            "prompts",
            "extraction_reflexion.txt"
        )
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            # Fallback prompt
            return """You are a formal logic expert. Your previous extraction attempt had errors.
Fix the errors and provide a correct JSON extraction.
Remember: middle_term must appear in both premises but NOT in conclusion.
Mood = premise1.type + premise2.type + conclusion.type."""
    
    def extract_with_reflexion(self, syllogism_text: str) -> Dict[str, Any]:
        """
        Extract structure with self-correction on validation failures.
        Optionally uses self-consistency for each attempt.
        
        Args:
            syllogism_text: Natural language syllogism
            
        Returns:
            dict with success, structure, attempts, etc.
        """
        attempts = []
        
        for attempt_num in range(1, self.max_attempts + 1):
            # Build prompt
            if attempt_num == 1:
                prompt = f"Extract the structure from this syllogism:\n\n{syllogism_text}"
            else:
                # Include previous attempts and errors
                prompt = self._build_reflexion_prompt(syllogism_text, attempts)
            
            # Generate extraction - use reflexion prompt for retries
            try:
                system_prompt = self.extractor.system_prompt if attempt_num == 1 else self.reflexion_system_prompt
                
                # Use self-consistency if enabled
                if self.use_self_consistency:
                    validation_result = self._extract_with_self_consistency(
                        prompt, 
                        system_prompt, 
                        syllogism_text,
                        attempt_num
                    )
                else:
                    response = self.client.generate(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=0.0
                    )
                    validation_result = self._validate_extraction(response, syllogism_text)
                
                attempts.append({
                    "attempt": attempt_num,
                    "validation": validation_result,
                    "self_consistency": validation_result.get("self_consistency")
                })
                
                # DEBUG: Log the validation result
                if self.verbose:
                    print(f"    Attempt {attempt_num} validation_result['valid'] = {validation_result.get('valid')}")
                    if validation_result.get('self_consistency'):
                        sc = validation_result['self_consistency']
                        print(f"    Self-consistency: {sc.get('successful_samples')} successful, selected: {sc.get('selected_form')}")
                
                if validation_result["valid"]:
                    structure = validation_result["structure"]
                    
                    # Safety check: ensure structure is not None
                    if structure is None:
                        # Update the attempt to indicate the bug
                        attempts[-1]["validation"]["errors"] = ["BUG: valid=True but structure is None"]
                        attempts[-1]["validation"]["valid"] = False
                        if attempts[-1].get("self_consistency"):
                            attempts[-1]["self_consistency"]["bug_structure_none"] = True
                        if self.verbose:
                            print(f"    ⚠ BUG: valid=True but structure is None, trying next attempt")
                        continue  # Try next attempt
                    
                    figure_verification = None
                    
                    # Apply figure verification if enabled
                    if self.verify_figure:
                        try:
                            figure_verification = self._apply_figure_verification(structure)
                        except Exception as fig_err:
                            if self.verbose:
                                print(f"    ⚠ Figure verification error: {fig_err}")
                            # Don't fail the extraction, just skip figure verification
                            figure_verification = {"error": str(fig_err)}
                    
                    if self.verbose:
                        print(f"    ✓ Extraction successful: {structure.mood}-{structure.figure}")
                    
                    return {
                        "success": True,
                        "structure": structure,
                        "attempts": attempt_num,
                        "history": attempts,
                        "used_self_consistency": self.use_self_consistency,
                        "figure_verification": figure_verification
                    }
                else:
                    # validation_result["valid"] is False
                    if self.verbose:
                        errors = validation_result.get("errors", [])
                        print(f"    ✗ Validation failed: {errors[:2]}...")  # Show first 2 errors
                    
            except Exception as e:
                if self.verbose:
                    print(f"    ✗ Exception in attempt {attempt_num}: {e}")
                    import traceback
                    traceback.print_exc()
                attempts.append({
                    "attempt": attempt_num,
                    "error": str(e),
                    "validation": {"valid": False, "errors": [str(e)]}
                })
        
        # All attempts failed
        return {
            "success": False,
            "error": "Max attempts reached",
            "attempts": self.max_attempts,
            "history": attempts,
            "used_self_consistency": self.use_self_consistency
        }
    
    def _apply_figure_verification(self, structure: SyllogismStructure) -> Optional[Dict[str, Any]]:
        """
        Apply figure verification to a structure using the extractor's verification method.
        
        Args:
            structure: The structure to verify
            
        Returns:
            Figure verification result or None
        """
        if not hasattr(self.extractor, '_verify_figure'):
            return None
        
        original_figure = structure.figure
        verification = self.extractor._verify_figure(structure)
        
        if verification is None:
            if self.verbose:
                print(f"    ⚠ Figure verification failed")
            return {
                "success": False,
                "original_figure": original_figure,
                "verified_figure": None,
                "corrected": False
            }
        
        verified_figure = verification["figure"]
        corrected = verified_figure != original_figure
        
        if corrected:
            if self.verbose:
                print(f"    ✓ Figure corrected: {original_figure} -> {verified_figure}")
            structure.figure = verified_figure
        else:
            if self.verbose:
                print(f"    ✓ Figure verified: {verified_figure}")
        
        return {
            "success": True,
            "original_figure": original_figure,
            "verified_figure": verified_figure,
            "corrected": corrected,
            "m_in_premise1": verification.get("m_in_premise1"),
            "m_in_premise2": verification.get("m_in_premise2"),
            "reasoning": verification.get("reasoning")
        }
    
    def _extract_with_self_consistency(
        self, 
        prompt: str, 
        system_prompt: str, 
        syllogism_text: str,
        attempt_num: int
    ) -> Dict[str, Any]:
        """
        Run extraction with self-consistency voting using graduated temperatures.
        
        Each sample uses a different temperature from the schedule:
        - Sample 1: temp=0.0 (deterministic baseline)
        - Sample 2: temp=0.3 (slight exploration)
        - Sample 3: temp=0.5 (moderate exploration)
        - etc.
        
        Args:
            prompt: The extraction prompt
            system_prompt: The system prompt to use
            syllogism_text: Original syllogism text
            attempt_num: Current attempt number
            
        Returns:
            Validation result with self-consistency info
        """
        from collections import Counter
        
        extractions = []  # List of (structure, form, validation_result, temperature)
        failed_samples = []
        forms_seen = []  # For logging
        
        # Get graduated temperatures
        temperatures = self._get_temperatures(self.num_consistency_samples)
        
        if self.verbose:
            print(f"    Running self-consistency with {self.num_consistency_samples} samples (graduated temps)...")
        
        for i, temp in enumerate(temperatures):
            try:
                response = self.client.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temp
                )
                
                validation = self._validate_extraction(response, syllogism_text)
                
                if validation["valid"]:
                    structure = validation["structure"]
                    form = f"{structure.mood}-{structure.figure}"
                    extractions.append((structure, form, validation, temp))
                    forms_seen.append(f"{form} (t={temp})")
                    
                    if self.verbose:
                        print(f"      Sample {i+1}/{self.num_consistency_samples} (temp={temp}): {form}")
                else:
                    failed_samples.append({"temperature": temp, **validation})
                    forms_seen.append(f"FAILED (t={temp})")
                    if self.verbose:
                        print(f"      Sample {i+1}/{self.num_consistency_samples} (temp={temp}): FAILED")
                        
            except Exception as e:
                failed_samples.append({"temperature": temp, "valid": False, "errors": [str(e)]})
                forms_seen.append(f"ERROR (t={temp})")
                if self.verbose:
                    print(f"      Sample {i+1}/{self.num_consistency_samples} (temp={temp}): ERROR - {e}")
        
        # Handle results
        if len(extractions) == 0:
            return {
                "valid": False,
                "errors": [f"All {self.num_consistency_samples} self-consistency samples failed"],
                "self_consistency": {
                    "successful_samples": 0,
                    "failed_samples": self.num_consistency_samples,
                    "temperatures_used": temperatures,
                    "forms_seen": forms_seen
                }
            }
        
        if len(extractions) == 1:
            structure, form, validation, temp = extractions[0]
            return {
                "valid": True,
                "structure": structure,
                "errors": [],
                "self_consistency": {
                    "successful_samples": 1,
                    "failed_samples": self.num_consistency_samples - 1,
                    "selected_form": form,
                    "vote_counts": {form: 1},
                    "no_voting_needed": True,
                    "temperatures_used": temperatures,
                    "forms_seen": forms_seen
                }
            }
        
        # Majority voting
        forms = [form for _, form, _, _ in extractions]
        vote_counts = Counter(forms)
        max_votes = max(vote_counts.values())
        
        # Select first extraction with max votes
        winning_structure = None
        winning_form = None
        for structure, form, _, _ in extractions:
            if vote_counts[form] == max_votes:
                winning_structure = structure
                winning_form = form
                break
        
        # Defensive check: if somehow no winner was found, use first extraction
        if winning_structure is None and len(extractions) > 0:
            winning_structure, winning_form, _, _ = extractions[0]
            if self.verbose:
                print(f"      ⚠ No winner found in voting, using first extraction: {winning_form}")
        
        had_disagreement = len(set(forms)) > 1
        had_tie = len([f for f, c in vote_counts.items() if c == max_votes]) > 1
        
        if self.verbose:
            print(f"      Voting: {dict(vote_counts)} → Selected: {winning_form}")
            if had_disagreement:
                print(f"      ⚠ Disagreement detected")
        
        # Final safety check
        if winning_structure is None:
            # This should NEVER happen if we have extractions
            error_msg = f"BUG: No winning structure despite having {len(extractions)} extractions"
            if self.verbose:
                print(f"      ⚠ {error_msg}")
                print(f"      extractions: {[(f, t) for _, f, _, t in extractions]}")
            return {
                "valid": False,
                "errors": [error_msg],
                "self_consistency": {
                    "successful_samples": len(extractions),
                    "failed_samples": self.num_consistency_samples - len(extractions),
                    "vote_counts": dict(vote_counts),
                    "bug_detected": True,
                    "temperatures_used": temperatures,
                    "forms_seen": forms_seen
                }
            }
        
        # CRITICAL: Verify structure is not None before returning
        if self.verbose:
            print(f"      ✓ Returning structure: {winning_structure.mood}-{winning_structure.figure}")
        
        return {
            "valid": True,
            "structure": winning_structure,
            "errors": [],
            "self_consistency": {
                "successful_samples": len(extractions),
                "failed_samples": self.num_consistency_samples - len(extractions),
                "selected_form": winning_form,
                "vote_counts": dict(vote_counts),
                "max_votes": max_votes,
                "all_forms": forms,
                "had_disagreement": had_disagreement,
                "had_tie": had_tie,
                "temperatures_used": temperatures,
                "forms_seen": forms_seen
            }
        }
    
    def _validate_extraction(self, response: str, syllogism_text: str) -> Dict[str, Any]:
        """Validate the extracted structure."""
        errors = []
        
        # Try to parse JSON
        try:
            json_str = self.extractor._extract_json(response)
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return {"valid": False, "errors": [f"Invalid JSON: {e}"]}
        
        # Check required fields
        required = ["premise1", "premise2", "conclusion", "middle_term", 
                   "major_term", "minor_term", "figure", "mood"]
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return {"valid": False, "errors": errors}
        
        # Check proposition structure
        for prop_name in ["premise1", "premise2", "conclusion"]:
            prop = data.get(prop_name, {})
            if not isinstance(prop, dict):
                errors.append(f"{prop_name} must be an object")
                continue
            for field in ["type", "subject", "predicate"]:
                if field not in prop:
                    errors.append(f"{prop_name} missing '{field}'")
        
        if errors:
            return {"valid": False, "errors": errors}
        
        # Check proposition types are valid
        valid_types = {"A", "E", "I", "O"}
        for prop_name in ["premise1", "premise2", "conclusion"]:
            prop = data.get(prop_name, {})
            ptype = prop.get("type", "").upper()
            if ptype not in valid_types:
                errors.append(f"{prop_name} has invalid type: {ptype}")
        
        # Check figure is valid
        figure = data.get("figure")
        if figure not in [1, 2, 3, 4]:
            errors.append(f"Invalid figure: {figure}")
        
        # Check mood matches proposition types
        expected_mood = (
            data.get("premise1", {}).get("type", "").upper() +
            data.get("premise2", {}).get("type", "").upper() +
            data.get("conclusion", {}).get("type", "").upper()
        )
        actual_mood = data.get("mood", "").upper()
        if actual_mood != expected_mood:
            errors.append(f"Mood '{actual_mood}' doesn't match types '{expected_mood}'")
        
        # Check middle term appears in both premises
        p1_terms = {
            data["premise1"].get("subject", "").lower(),
            data["premise1"].get("predicate", "").lower()
        }
        p2_terms = {
            data["premise2"].get("subject", "").lower(),
            data["premise2"].get("predicate", "").lower()
        }
        middle = data.get("middle_term", "").lower()
        
        if middle not in p1_terms:
            errors.append(f"Middle term '{middle}' not found in premise1 terms: {p1_terms}")
        if middle not in p2_terms:
            errors.append(f"Middle term '{middle}' not found in premise2 terms: {p2_terms}")
        
        # Check middle term doesn't appear in conclusion
        c_terms = {
            data["conclusion"].get("subject", "").lower(),
            data["conclusion"].get("predicate", "").lower()
        }
        if middle in c_terms:
            errors.append(f"Middle term '{middle}' should not appear in conclusion")
        
        if errors:
            return {"valid": False, "errors": errors}
        
        # Build structure
        try:
            structure = self.extractor._build_structure(data)
            return {"valid": True, "structure": structure, "errors": []}
        except Exception as e:
            return {"valid": False, "errors": [f"Failed to build structure: {e}"]}
    
    def _build_reflexion_prompt(self, syllogism_text: str, attempts: List[Dict]) -> str:
        """Build prompt with previous attempts and errors."""
        prompt = f"Extract the structure from this syllogism:\n\n{syllogism_text}\n\n"
        prompt += "=" * 60 + "\n"
        prompt += "PREVIOUS ATTEMPTS HAD ERRORS - PLEASE CORRECT:\n"
        prompt += "=" * 60 + "\n\n"
        
        for attempt in attempts:
            prompt += f"### Attempt {attempt['attempt']}:\n"
            validation = attempt.get('validation', {})
            errors = validation.get('errors', [])
            if errors:
                prompt += "Errors found:\n"
                for err in errors:
                    prompt += f"  - {err}\n"
            prompt += "\n"
        
        prompt += "Please fix these errors and provide a correct extraction.\n"
        
        return prompt
