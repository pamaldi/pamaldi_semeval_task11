"""
Simplified Syllogism Extractor with Deterministic Post-Processing.

This module splits the extraction into two phases:
1. LLM extracts ONLY types and terms (the "fuzzy" NLU task)
2. Post-processor computes figure, mood, form, validity (deterministic)

This separation fixes figure calculation errors that the LLM was making.
"""

import os
import json
import re
from typing import Dict, Any, Optional, List, Tuple
from collections import Counter

from syllogism_structures import Proposition, SyllogismStructure
from postprocessor import DeterministicPostProcessor
from proposition_validator import PropositionTypeValidator


class SimplifiedExtractor:
    """
    Simplified extractor that only asks LLM for types and terms.
    Figure, mood, form, and validity are computed deterministically.
    """
    
    def __init__(
        self,
        bedrock_client,
        prompt_path: str = None,
        use_self_consistency: bool = False,
        num_consistency_samples: int = 3,
        temperature_schedule: List[float] = None,
        verbose: bool = False
    ):
        """
        Initialize the simplified extractor.
        
        Args:
            bedrock_client: BedrockClient instance
            prompt_path: Path to the simplified extraction prompt
            use_self_consistency: Whether to use self-consistency voting
            num_consistency_samples: Number of samples for self-consistency
            temperature_schedule: List of temperatures for each sample
            verbose: Whether to print debug information
        """
        self.client = bedrock_client
        self.use_self_consistency = use_self_consistency
        self.num_consistency_samples = num_consistency_samples
        self.verbose = verbose
        
        # Temperature schedule for self-consistency
        if temperature_schedule is not None:
            self.temperature_schedule = temperature_schedule
        else:
            self.temperature_schedule = [0.0, 0.3, 0.5, 0.7, 0.8]
        
        # Load simplified prompt
        prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
        if prompt_path is None:
            prompt_path = os.path.join(prompts_dir, "structure_extraction_simplified.txt")
        
        self.system_prompt = self._load_prompt(prompt_path)
        
        # Initialize post-processor
        self.postprocessor = DeterministicPostProcessor(verbose=verbose)
        
        # Initialize type validator for additional I/O correction
        self.type_validator = PropositionTypeValidator(
            log_corrections=verbose,
            verbose=verbose
        )
    
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
Return JSON with: premise1, premise2, conclusion (each with type A/E/I/O, subject, predicate, raw_text).
Do NOT include figure, mood, or middle_term - these will be computed automatically."""
    
    def extract(self, syllogism_text: str, syllogism_id: str = None) -> Dict[str, Any]:
        """
        Extract structure from a syllogism using simplified LLM + deterministic post-processing.
        
        Args:
            syllogism_text: Natural language syllogism
            syllogism_id: Optional ID for logging
            
        Returns:
            dict with extraction result including computed figure, mood, form, validity
        """
        # Step 1: LLM extracts types and terms only
        if self.use_self_consistency:
            llm_result = self._extract_with_self_consistency(syllogism_text)
        else:
            llm_result = self._extract_single(syllogism_text, temperature=0.0)
        
        if not llm_result.get("success"):
            return llm_result
        
        extraction = llm_result["extraction"]
        
        # DEBUG: Log types BEFORE type validation
        before_mood = (extraction["premise1"]["type"] + 
                      extraction["premise2"]["type"] + 
                      extraction["conclusion"]["type"])
        if self.verbose:
            print(f"  [DEBUG] Before type validation: {before_mood}")
        
        # Step 2: Apply type validation (I/O correction)
        # NOTE: This should NOT override correctly voted types!
        extraction = self.type_validator.validate_extraction(extraction)
        
        # DEBUG: Log types AFTER type validation
        after_mood = (extraction["premise1"]["type"] + 
                     extraction["premise2"]["type"] + 
                     extraction["conclusion"]["type"])
        if self.verbose:
            print(f"  [DEBUG] After type validation: {after_mood}")
            if before_mood != after_mood:
                print(f"  [DEBUG] ⚠️ Type validation CHANGED mood: {before_mood} → {after_mood}")
        
        # Step 3: Deterministic post-processing (figure, mood, form, validity)
        post_result = self.postprocessor.process(extraction, syllogism_id)
        
        if not post_result.get("success"):
            return {
                "success": False,
                "error": f"Post-processing failed: {post_result.get('errors', [])}",
                "raw_extraction": extraction,
                "postprocessor_log": post_result.get("log")
            }
        
        # Step 4: Build SyllogismStructure
        try:
            structure = self._build_structure(extraction, post_result)
            
            return {
                "success": True,
                "structure": structure,
                "extraction": extraction,
                "postprocessor_result": post_result,
                "terms": post_result["terms"],
                "figure": post_result["figure"],
                "mood": post_result["mood"],
                "form": post_result["form"],
                "validity": post_result["validity"],
                "validity_reason": post_result["validity_reason"],
                "form_name": post_result.get("form_name"),
                "corrections": post_result.get("warnings", []),
                "self_consistency": llm_result.get("self_consistency"),
                "raw_response": llm_result.get("raw_response")
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Structure building failed: {str(e)}",
                "raw_extraction": extraction,
                "postprocessor_result": post_result
            }
    
    def _extract_single(self, syllogism_text: str, temperature: float = 0.0) -> Dict[str, Any]:
        """
        Extract types and terms from a syllogism (single attempt).
        
        Args:
            syllogism_text: Natural language syllogism
            temperature: LLM temperature
            
        Returns:
            dict with extraction result
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
            extraction = json.loads(json_str)
            
            # Validate required fields
            self._validate_extraction(extraction)
            
            return {
                "success": True,
                "extraction": extraction,
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
    
    def _extract_with_self_consistency(self, syllogism_text: str) -> Dict[str, Any]:
        """
        Extract using self-consistency voting on types.
        
        Args:
            syllogism_text: Natural language syllogism
            
        Returns:
            dict with extraction result and voting info
        """
        num_samples = self.num_consistency_samples
        temperatures = self._get_temperatures(num_samples)
        
        extractions = []
        failed_attempts = []
        
        # Run multiple extractions
        for i, temp in enumerate(temperatures):
            result = self._extract_single(syllogism_text, temperature=temp)
            
            if result["success"]:
                extractions.append((result["extraction"], temp))
                if self.verbose:
                    types = self._get_types_key(result["extraction"])
                    print(f"  Self-consistency sample {i+1}/{num_samples} (temp={temp}): {types}")
            else:
                failed_attempts.append({"temperature": temp, **result})
                if self.verbose:
                    print(f"  Self-consistency sample {i+1}/{num_samples} (temp={temp}): FAILED")
        
        if len(extractions) == 0:
            return {
                "success": False,
                "error": f"All {num_samples} extraction attempts failed",
                "failed_attempts": failed_attempts,
                "self_consistency": {
                    "num_samples": num_samples,
                    "successful_samples": 0,
                    "failed_samples": num_samples
                }
            }
        
        if len(extractions) == 1:
            extraction, temp = extractions[0]
            return {
                "success": True,
                "extraction": extraction,
                "self_consistency": {
                    "num_samples": num_samples,
                    "successful_samples": 1,
                    "failed_samples": num_samples - 1,
                    "no_voting_needed": True
                }
            }
        
        # Vote on types
        voted_extraction = self._vote_on_types(extractions)
        
        # Build voting info
        types_seen = [self._get_types_key(ext) for ext, _ in extractions]
        vote_counts = Counter(types_seen)
        
        return {
            "success": True,
            "extraction": voted_extraction,
            "self_consistency": {
                "num_samples": num_samples,
                "successful_samples": len(extractions),
                "failed_samples": num_samples - len(extractions),
                "vote_counts": dict(vote_counts),
                "types_seen": types_seen,
                "had_disagreement": len(set(types_seen)) > 1
            }
        }
    
    def _vote_on_types(self, extractions: List[Tuple[Dict, float]]) -> Dict[str, Any]:
        """
        Vote on proposition types across multiple extractions.
        
        CRITICAL: This method MUST apply the voted types to the extraction.
        The voted mood is often correct even when individual extractions are wrong.
        
        Args:
            extractions: List of (extraction_dict, temperature) tuples
            
        Returns:
            Extraction with voted types APPLIED
        """
        import copy
        
        # CRITICAL: Deep copy to avoid modifying original extractions
        result = copy.deepcopy(extractions[0][0])
        
        # Vote on each proposition's type independently
        for prop_name in ["premise1", "premise2", "conclusion"]:
            types = [ext[prop_name]["type"].upper() for ext, _ in extractions]
            vote_counts = Counter(types)
            voted_type = vote_counts.most_common(1)[0][0]
            
            original_type = result[prop_name]["type"].upper()
            
            # CRITICAL: Always apply the voted type
            result[prop_name]["type"] = voted_type
            
            if original_type != voted_type:
                result[prop_name]["type_voted"] = True
                result[prop_name]["original_type"] = original_type
                if self.verbose:
                    print(f"    ⚠ {prop_name}: {original_type} → {voted_type} (voted)")
        
        # Log the final voted mood
        voted_mood = result["premise1"]["type"] + result["premise2"]["type"] + result["conclusion"]["type"]
        if self.verbose:
            print(f"    → Applied voted mood: {voted_mood}")
        
        return result
    
    def _get_types_key(self, extraction: Dict[str, Any]) -> str:
        """Get a string key representing the types (e.g., 'AAA', 'EIO')."""
        return (
            extraction["premise1"]["type"] +
            extraction["premise2"]["type"] +
            extraction["conclusion"]["type"]
        )
    
    def _get_temperatures(self, num_samples: int) -> List[float]:
        """Get temperature schedule for given number of samples."""
        schedule = self.temperature_schedule
        if num_samples <= len(schedule):
            return schedule[:num_samples]
        else:
            extra = num_samples - len(schedule)
            return schedule + [schedule[-1]] * extra
    
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
        
        return response.strip()
    
    def _validate_extraction(self, extraction: Dict[str, Any]):
        """Validate that extraction has required fields."""
        required_props = ["premise1", "premise2", "conclusion"]
        required_fields = ["type", "subject", "predicate"]
        
        for prop in required_props:
            if prop not in extraction:
                raise KeyError(f"Missing {prop}")
            for field in required_fields:
                if field not in extraction[prop]:
                    raise KeyError(f"Missing {prop}.{field}")
    
    def _build_structure(self, extraction: Dict[str, Any], 
                         post_result: Dict[str, Any]) -> SyllogismStructure:
        """Build SyllogismStructure from extraction and post-processor result."""
        
        def normalize(term: str) -> str:
            return term.lower().strip() if term else ""
        
        terms = post_result["terms"]
        
        return SyllogismStructure(
            premise1=Proposition(
                type=extraction["premise1"]["type"].upper(),
                subject=normalize(extraction["premise1"]["subject"]),
                predicate=normalize(extraction["premise1"]["predicate"]),
                raw_text=extraction["premise1"].get("raw_text", "")
            ),
            premise2=Proposition(
                type=extraction["premise2"]["type"].upper(),
                subject=normalize(extraction["premise2"]["subject"]),
                predicate=normalize(extraction["premise2"]["predicate"]),
                raw_text=extraction["premise2"].get("raw_text", "")
            ),
            conclusion=Proposition(
                type=extraction["conclusion"]["type"].upper(),
                subject=normalize(extraction["conclusion"]["subject"]),
                predicate=normalize(extraction["conclusion"]["predicate"]),
                raw_text=extraction["conclusion"].get("raw_text", "")
            ),
            middle_term=terms["M"],
            major_term=terms["P"],
            minor_term=terms["S"],
            figure=post_result["figure"],
            mood=post_result["mood"]
        )
    
    def get_postprocessor_stats(self) -> Dict[str, Any]:
        """Get statistics from the type validator."""
        return self.type_validator.get_stats()


# Convenience function
def create_simplified_extractor(bedrock_client, **kwargs) -> SimplifiedExtractor:
    """Create a SimplifiedExtractor with default settings."""
    return SimplifiedExtractor(bedrock_client, **kwargs)
