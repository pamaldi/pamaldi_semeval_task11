"""
LLM-based syllogism structure extractor using AWS Bedrock.
Supports self-consistency with graduated temperatures and figure verification.
"""

import os
import json
import re
from typing import Dict, Any, Optional, List, Tuple
from collections import Counter, defaultdict
from syllogism_structures import Proposition, SyllogismStructure
from proposition_validator import PropositionTypeValidator


class FigureVerificationStats:
    """Track figure verification statistics for analysis."""
    
    def __init__(self):
        self.total_verifications = 0
        self.corrections_made = 0
        self.verification_failures = 0
        self.corrections_by_type = defaultdict(int)  # e.g., "1->2": 5
    
    def record(self, original_figure: int, verified_figure: int, success: bool):
        """Record a verification result."""
        self.total_verifications += 1
        
        if not success:
            self.verification_failures += 1
            return
        
        if original_figure != verified_figure:
            self.corrections_made += 1
            self.corrections_by_type[f"{original_figure}->{verified_figure}"] += 1
    
    def report(self) -> Dict[str, Any]:
        """Generate a report of verification statistics."""
        return {
            "total_verifications": self.total_verifications,
            "corrections_made": self.corrections_made,
            "correction_rate": self.corrections_made / max(1, self.total_verifications),
            "verification_failures": self.verification_failures,
            "corrections_by_type": dict(self.corrections_by_type)
        }


class SyllogismExtractor:
    """
    Uses AWS Bedrock LLM to extract syllogism structure from natural language.
    Supports self-consistency with graduated temperatures and figure verification.
    """
    
    # Default temperature schedule for self-consistency
    # Sample 1: deterministic baseline, then increasing exploration
    DEFAULT_TEMPERATURE_SCHEDULE = [0.0, 0.3, 0.5, 0.7, 0.8]
    
    def __init__(
        self, 
        bedrock_client, 
        prompt_path: str = None,
        use_self_consistency: bool = False,
        num_consistency_samples: int = 3,
        temperature_schedule: List[float] = None,
        verify_figure: bool = False,
        verbose: bool = False
    ):
        """
        Initialize the extractor.
        
        Args:
            bedrock_client: BedrockClient instance
            prompt_path: Path to the extraction prompt file
            use_self_consistency: Whether to use self-consistency voting
            num_consistency_samples: Number of samples for self-consistency
            temperature_schedule: List of temperatures for each sample (default: [0.0, 0.3, 0.5, 0.7, 0.8])
            verify_figure: Whether to verify figure with a dedicated LLM call
            verbose: Whether to print debug information
        """
        self.client = bedrock_client
        self.use_self_consistency = use_self_consistency
        self.num_consistency_samples = num_consistency_samples
        self.verify_figure = verify_figure
        self.verbose = verbose
        
        # Use provided schedule or default graduated temperatures
        if temperature_schedule is not None:
            self.temperature_schedule = temperature_schedule
        else:
            self.temperature_schedule = self.DEFAULT_TEMPERATURE_SCHEDULE
        
        # Figure verification stats
        self.figure_stats = FigureVerificationStats()
        
        # Proposition type validator for I/O confusion correction
        self.type_validator = PropositionTypeValidator(
            log_corrections=verbose,
            verbose=verbose
        )
        
        # Validate parameters
        if num_consistency_samples < 1:
            raise ValueError("num_consistency_samples must be >= 1")
        
        # Load prompts
        prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
        
        if prompt_path is None:
            prompt_path = os.path.join(prompts_dir, "structure_extraction.txt")
        
        self.system_prompt = self._load_prompt(prompt_path)
        
        # Load figure verification prompt
        self.figure_verification_prompt = self._load_prompt(
            os.path.join(prompts_dir, "figure_verification.txt")
        )
    
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

    def _load_prompt(self, path: str) -> str:
        """Load the extraction prompt from file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"⚠ Warning: Prompt file not found: {path}")
            return self._get_fallback_prompt()
    
    def _get_fallback_prompt(self) -> str:
        """Fallback prompt if file not found."""
        return """You are a formal logic expert. Extract the syllogism structure.
Return JSON with: premise1, premise2, conclusion (each with type A/E/I/O, subject, predicate),
middle_term, major_term, minor_term, figure (1-4), mood (e.g., AAA)."""
    
    def extract(self, syllogism_text: str) -> Dict[str, Any]:
        """
        Extract structure from a syllogism.
        Uses self-consistency if enabled, then applies figure verification if enabled.
        
        Args:
            syllogism_text: Natural language syllogism
            
        Returns:
            dict with extraction result or error
        """
        # Step 1: Extract (with or without self-consistency)
        if self.use_self_consistency:
            result = self.extract_with_self_consistency(
                syllogism_text,
                num_samples=self.num_consistency_samples
            )
        else:
            result = self._extract_single(syllogism_text, temperature=0.0)
        
        # Step 2: Apply figure verification if enabled and extraction succeeded
        if result.get("success") and self.verify_figure:
            result = self._apply_figure_verification(result)
        
        return result
    
    def _apply_figure_verification(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply figure verification to an extraction result.
        
        Args:
            result: Extraction result with structure
            
        Returns:
            Updated result with verified figure
        """
        structure = result["structure"]
        original_figure = structure.figure
        
        # Verify figure
        verification = self._verify_figure(structure)
        
        if verification is None:
            # Verification failed
            self.figure_stats.record(original_figure, original_figure, success=False)
            if self.verbose:
                print(f"  ⚠ Figure verification failed, keeping original figure {original_figure}")
            result["figure_verification"] = {
                "success": False,
                "original_figure": original_figure,
                "verified_figure": None,
                "corrected": False
            }
            return result
        
        verified_figure = verification["figure"]
        corrected = verified_figure != original_figure
        
        # Record stats
        self.figure_stats.record(original_figure, verified_figure, success=True)
        
        if corrected:
            if self.verbose:
                print(f"  ✓ Figure corrected: {original_figure} -> {verified_figure}")
                print(f"    M in P1: {verification['m_in_premise1']}, M in P2: {verification['m_in_premise2']}")
            
            # Update structure with corrected figure
            structure.figure = verified_figure
        else:
            if self.verbose:
                print(f"  ✓ Figure verified: {verified_figure} (no correction needed)")
        
        result["figure_verification"] = {
            "success": True,
            "original_figure": original_figure,
            "verified_figure": verified_figure,
            "corrected": corrected,
            "m_in_premise1": verification.get("m_in_premise1"),
            "m_in_premise2": verification.get("m_in_premise2"),
            "reasoning": verification.get("reasoning")
        }
        
        return result
    
    def _verify_figure(self, structure: SyllogismStructure) -> Optional[Dict[str, Any]]:
        """
        Verify the figure of an extraction using a dedicated LLM call.
        
        Args:
            structure: The extraction to verify
            
        Returns:
            dict with verification result or None if failed
        """
        # Build verification prompt
        prompt = self._build_figure_verification_prompt(structure)
        
        try:
            # Call LLM with low temperature for deterministic verification
            response = self.client.generate(
                prompt=prompt,
                system_prompt="You are a formal logic expert verifying syllogism figure calculation.",
                temperature=0.0
            )
            
            # Parse response
            return self._parse_figure_verification_response(response)
            
        except Exception as e:
            if self.verbose:
                print(f"  ⚠ Figure verification error: {e}")
            return None
    
    def _build_figure_verification_prompt(self, structure: SyllogismStructure) -> str:
        """Build the figure verification prompt from an extraction."""
        return self.figure_verification_prompt.format(
            premise1_raw_text=structure.premise1.raw_text or f"{structure.premise1.type}: {structure.premise1.subject} - {structure.premise1.predicate}",
            premise1_subject=structure.premise1.subject,
            premise1_predicate=structure.premise1.predicate,
            premise2_raw_text=structure.premise2.raw_text or f"{structure.premise2.type}: {structure.premise2.subject} - {structure.premise2.predicate}",
            premise2_subject=structure.premise2.subject,
            premise2_predicate=structure.premise2.predicate,
            middle_term=structure.middle_term
        )
    
    def _parse_figure_verification_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse the JSON response from figure verification."""
        try:
            # Extract JSON from response
            json_str = self._extract_json(response)
            result = json.loads(json_str)
            
            # Validate figure is 1-4
            figure = result.get("figure")
            if figure not in [1, 2, 3, 4]:
                if self.verbose:
                    print(f"  ⚠ Invalid figure in verification: {figure}")
                return None
            
            # Validate m_in_premise fields
            m_in_p1 = result.get("m_in_premise1", "").upper()
            m_in_p2 = result.get("m_in_premise2", "").upper()
            
            if m_in_p1 not in ["SUBJECT", "PREDICATE"] or m_in_p2 not in ["SUBJECT", "PREDICATE"]:
                if self.verbose:
                    print(f"  ⚠ Invalid m_in_premise values: {m_in_p1}, {m_in_p2}")
                return None
            
            return {
                "figure": figure,
                "m_in_premise1": m_in_p1,
                "m_in_premise2": m_in_p2,
                "reasoning": result.get("reasoning", "")
            }
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            if self.verbose:
                print(f"  ⚠ Failed to parse figure verification: {e}")
            return None
    
    def compute_figure_from_positions(self, m_in_p1: str, m_in_p2: str) -> int:
        """
        Compute figure from middle term positions.
        
        | M in Premise 1 | M in Premise 2 | Figure |
        |----------------|----------------|--------|
        | SUBJECT        | PREDICATE      | 1      |
        | PREDICATE      | PREDICATE      | 2      |
        | SUBJECT        | SUBJECT        | 3      |
        | PREDICATE      | SUBJECT        | 4      |
        """
        m_in_p1 = m_in_p1.upper()
        m_in_p2 = m_in_p2.upper()
        
        if m_in_p1 == "SUBJECT" and m_in_p2 == "PREDICATE":
            return 1
        elif m_in_p1 == "PREDICATE" and m_in_p2 == "PREDICATE":
            return 2
        elif m_in_p1 == "SUBJECT" and m_in_p2 == "SUBJECT":
            return 3
        elif m_in_p1 == "PREDICATE" and m_in_p2 == "SUBJECT":
            return 4
        else:
            raise ValueError(f"Invalid positions: {m_in_p1}, {m_in_p2}")
    
    def _extract_single(self, syllogism_text: str, temperature: float = 0.0) -> Dict[str, Any]:
        """
        Extract structure from a syllogism (single attempt).
        
        Args:
            syllogism_text: Natural language syllogism
            temperature: LLM temperature
            
        Returns:
            dict with extraction result or error
        """
        try:
            # Call LLM
            response = self.client.generate(
                prompt=f"Extract the structure from this syllogism:\n\n{syllogism_text}",
                system_prompt=self.system_prompt,
                temperature=temperature
            )
            
            # Parse JSON from response
            json_str = self._extract_json(response)
            data = json.loads(json_str)
            
            # Validate and build structure
            structure = self._build_structure(data)
            
            return {
                "success": True,
                "structure": structure,
                "raw_response": response
            }
            
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON in response: {e}",
                "raw_response": response if 'response' in dir() else None
            }
        except KeyError as e:
            return {
                "success": False,
                "error": f"Missing required field: {e}",
                "raw_response": response if 'response' in dir() else None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "raw_response": None
            }
    
    def extract_with_self_consistency(
        self, 
        syllogism_text: str, 
        num_samples: int = None
    ) -> Dict[str, Any]:
        """
        Extract syllogism structure using self-consistency with graduated temperatures.
        
        Each sample uses a different temperature from the schedule:
        - Sample 1: temp=0.0 (deterministic baseline)
        - Sample 2: temp=0.3 (slight exploration)
        - Sample 3: temp=0.5 (moderate exploration)
        - etc.
        
        1. Run extraction num_samples times with graduated temperatures
        2. For each successful extraction, compute a canonical form
        3. Use majority voting on the canonical form
        4. Return the most voted extraction
        
        If there's a tie, prefer the extraction that appears first.
        If all extractions fail, return None.
        
        Args:
            syllogism_text: Natural language syllogism
            num_samples: Number of extraction attempts (default: self.num_consistency_samples)
            
        Returns:
            dict with extraction result, voting info, or error
        """
        if num_samples is None:
            num_samples = self.num_consistency_samples
            
        if num_samples < 1:
            raise ValueError("num_samples must be >= 1")
        
        # Get graduated temperatures for each sample
        temperatures = self._get_temperatures(num_samples)
        
        extractions: List[Tuple[SyllogismStructure, str, Dict, float]] = []  # (structure, form, raw_result, temp)
        failed_attempts = []
        forms_seen = []  # For logging
        
        # Run multiple extractions with graduated temperatures
        for i, temp in enumerate(temperatures):
            result = self._extract_single(syllogism_text, temperature=temp)
            
            if result["success"]:
                structure = result["structure"]
                form = self._get_canonical_form(structure)
                extractions.append((structure, form, result, temp))
                forms_seen.append(f"{form} (t={temp})")
                
                if self.verbose:
                    print(f"  Self-consistency sample {i+1}/{num_samples} (temp={temp}): {form}")
            else:
                failed_attempts.append({"temperature": temp, **result})
                forms_seen.append(f"FAILED (t={temp})")
                if self.verbose:
                    print(f"  Self-consistency sample {i+1}/{num_samples} (temp={temp}): FAILED - {result.get('error', 'Unknown')}")
        
        # Handle edge cases
        if len(extractions) == 0:
            # All samples failed
            if self.verbose:
                print(f"  Self-consistency: All {num_samples} samples failed")
            return {
                "success": False,
                "error": f"All {num_samples} extraction attempts failed",
                "failed_attempts": failed_attempts,
                "self_consistency": {
                    "num_samples": num_samples,
                    "successful_samples": 0,
                    "failed_samples": num_samples,
                    "temperatures_used": temperatures,
                    "forms_seen": forms_seen
                }
            }
        
        if len(extractions) == 1:
            # Only one success, return it without voting
            structure, form, raw_result, temp = extractions[0]
            if self.verbose:
                print(f"  Self-consistency: Only 1 successful sample, returning {form} (t={temp})")
            return {
                "success": True,
                "structure": structure,
                "raw_response": raw_result.get("raw_response"),
                "self_consistency": {
                    "num_samples": num_samples,
                    "successful_samples": 1,
                    "failed_samples": num_samples - 1,
                    "selected_form": form,
                    "vote_counts": {form: 1},
                    "no_voting_needed": True,
                    "temperatures_used": temperatures,
                    "forms_seen": forms_seen
                }
            }
        
        # Perform majority voting
        winning_structure, voting_info = self._majority_vote(extractions)
        
        if self.verbose:
            print(f"  Self-consistency voting: {voting_info['vote_counts']}")
            print(f"  Selected form: {voting_info['selected_form']} with {voting_info['max_votes']} votes")
            if voting_info.get('had_disagreement'):
                print(f"  ⚠ Disagreement detected: {forms_seen}")
        
        return {
            "success": True,
            "structure": winning_structure,
            "raw_response": None,  # Multiple responses, not returning single one
            "self_consistency": {
                "num_samples": num_samples,
                "successful_samples": len(extractions),
                "temperatures_used": temperatures,
                "forms_seen": forms_seen,
                "failed_samples": num_samples - len(extractions),
                **voting_info
            }
        }
    
    def _get_canonical_form(self, structure: SyllogismStructure) -> str:
        """
        Get the canonical form for voting.
        Format: "{mood}-{figure}" (e.g., "AAA-1", "EIO-3")
        """
        return f"{structure.mood}-{structure.figure}"
    
    def _majority_vote(
        self, 
        extractions: List[Tuple[SyllogismStructure, str, Dict, float]]
    ) -> Tuple[SyllogismStructure, Dict[str, Any]]:
        """
        Given a list of successful extractions, return the one with the most common form.
        
        Args:
            extractions: List of (structure, form, raw_result, temperature) tuples
            
        Returns:
            Tuple of (winning_structure, voting_info)
        """
        # Count votes for each form
        forms = [form for _, form, _, _ in extractions]
        vote_counts = Counter(forms)
        
        # Find the winning form (most votes, first occurrence for ties)
        max_votes = max(vote_counts.values())
        
        # Get the first extraction with the winning vote count
        winning_structure = None
        winning_form = None
        for structure, form, _, _ in extractions:
            if vote_counts[form] == max_votes:
                winning_structure = structure
                winning_form = form
                break
        
        # Check for disagreement
        unique_forms = set(forms)
        had_disagreement = len(unique_forms) > 1
        
        # Check for tie
        forms_with_max_votes = [f for f, count in vote_counts.items() if count == max_votes]
        had_tie = len(forms_with_max_votes) > 1
        
        voting_info = {
            "vote_counts": dict(vote_counts),
            "selected_form": winning_form,
            "max_votes": max_votes,
            "all_forms": forms,
            "had_disagreement": had_disagreement,
            "had_tie": had_tie,
            "unique_forms": list(unique_forms)
        }
        
        return winning_structure, voting_info
    
    def estimate_cost(self, num_syllogisms: int) -> Dict[str, Any]:
        """
        Estimate API costs for extraction.
        
        Args:
            num_syllogisms: Number of syllogisms to process
            
        Returns:
            dict with cost estimates
        """
        base_calls = num_syllogisms
        
        # Self-consistency multiplier
        if self.use_self_consistency:
            extraction_calls = base_calls * self.num_consistency_samples
        else:
            extraction_calls = base_calls
        
        # Figure verification adds 1 call per syllogism
        if self.verify_figure:
            verification_calls = base_calls
        else:
            verification_calls = 0
        
        total_calls = extraction_calls + verification_calls
        
        return {
            "num_syllogisms": num_syllogisms,
            "use_self_consistency": self.use_self_consistency,
            "num_consistency_samples": self.num_consistency_samples if self.use_self_consistency else 1,
            "verify_figure": self.verify_figure,
            "extraction_calls": extraction_calls,
            "verification_calls": verification_calls,
            "total_api_calls": total_calls,
            "overhead_vs_baseline": total_calls / base_calls if base_calls > 0 else 0
        }
    
    def get_figure_verification_stats(self) -> Dict[str, Any]:
        """Get figure verification statistics."""
        return self.figure_stats.report()
    
    def _extract_json(self, response: str) -> str:
        """Extract JSON from LLM response."""
        # Try to find JSON block in markdown
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        # Try to find JSON object directly
        match = re.search(r'\{[\s\S]*\}', response)
        if match:
            return match.group(0)
        
        # Assume entire response is JSON
        return response.strip()
    
    def _build_structure(self, data: Dict[str, Any]) -> SyllogismStructure:
        """Build SyllogismStructure from parsed JSON."""
        # Normalize terms to lowercase
        def normalize(term: str) -> str:
            return term.lower().strip() if term else ""
        
        # Post-process to fix I/O type confusion using the validator
        data = self.type_validator.validate_extraction(data)
        
        return SyllogismStructure(
            premise1=Proposition(
                type=data["premise1"]["type"].upper(),
                subject=normalize(data["premise1"]["subject"]),
                predicate=normalize(data["premise1"]["predicate"]),
                raw_text=data["premise1"].get("raw_text", "")
            ),
            premise2=Proposition(
                type=data["premise2"]["type"].upper(),
                subject=normalize(data["premise2"]["subject"]),
                predicate=normalize(data["premise2"]["predicate"]),
                raw_text=data["premise2"].get("raw_text", "")
            ),
            conclusion=Proposition(
                type=data["conclusion"]["type"].upper(),
                subject=normalize(data["conclusion"]["subject"]),
                predicate=normalize(data["conclusion"]["predicate"]),
                raw_text=data["conclusion"].get("raw_text", "")
            ),
            middle_term=normalize(data["middle_term"]),
            major_term=normalize(data["major_term"]),
            minor_term=normalize(data["minor_term"]),
            figure=int(data["figure"]),
            mood=data["mood"].upper()
        )
    
    def get_type_validator_stats(self) -> Dict[str, int]:
        """Get statistics from the proposition type validator."""
        return self.type_validator.get_stats()
    
    def validate_structure(self, structure: SyllogismStructure) -> Dict[str, Any]:
        """
        Validate the extracted structure for consistency.
        
        Returns:
            dict with valid: bool and errors: list
        """
        errors = []
        
        # Check proposition types are valid
        valid_types = {"A", "E", "I", "O"}
        for name, prop in [("premise1", structure.premise1), 
                          ("premise2", structure.premise2),
                          ("conclusion", structure.conclusion)]:
            if prop.type not in valid_types:
                errors.append(f"{name} has invalid type: {prop.type}")
        
        # Check figure is valid
        if structure.figure not in [1, 2, 3, 4]:
            errors.append(f"Invalid figure: {structure.figure}")
        
        # Check mood matches proposition types
        expected_mood = (
            structure.premise1.type +
            structure.premise2.type +
            structure.conclusion.type
        )
        if structure.mood != expected_mood:
            errors.append(f"Mood '{structure.mood}' doesn't match types '{expected_mood}'")
        
        # Check middle term appears in both premises
        p1_terms = {structure.premise1.subject, structure.premise1.predicate}
        p2_terms = {structure.premise2.subject, structure.premise2.predicate}
        if structure.middle_term not in p1_terms:
            errors.append(f"Middle term '{structure.middle_term}' not in premise1")
        if structure.middle_term not in p2_terms:
            errors.append(f"Middle term '{structure.middle_term}' not in premise2")
        
        # Check middle term doesn't appear in conclusion
        c_terms = {structure.conclusion.subject, structure.conclusion.predicate}
        if structure.middle_term in c_terms:
            errors.append(f"Middle term '{structure.middle_term}' should not be in conclusion")
        
        # Check major term is predicate of conclusion
        if structure.major_term != structure.conclusion.predicate:
            errors.append(f"Major term '{structure.major_term}' should be conclusion predicate")
        
        # Check minor term is subject of conclusion
        if structure.minor_term != structure.conclusion.subject:
            errors.append(f"Minor term '{structure.minor_term}' should be conclusion subject")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
