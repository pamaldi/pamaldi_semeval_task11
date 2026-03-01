"""
LLM Fallback Evaluator for when structure extraction fails.

When the neuro-symbolic pipeline cannot extract the syllogism structure,
this fallback uses the LLM to directly evaluate validity.
"""

import os
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class LLMFallbackEvaluator:
    """
    Fallback evaluator that uses LLM to directly assess validity
    when structure extraction fails.
    
    This is a "pure neural" backup for the neuro-symbolic approach.
    Less accurate than symbolic validation, but better than no prediction.
    """
    
    # Default temperature schedule for self-consistency
    DEFAULT_TEMPERATURE_SCHEDULE = [0.0, 0.3, 0.5]
    
    def __init__(
        self, 
        llm_client, 
        prompt_path: str = None,
        verbose: bool = False
    ):
        """
        Initialize the fallback evaluator.
        
        Args:
            llm_client: BedrockClient instance
            prompt_path: Path to the fallback prompt file
            verbose: Whether to print debug information
        """
        self.client = llm_client
        self.verbose = verbose
        
        # Stats tracking
        self.stats = {
            "total_evaluations": 0,
            "valid_predictions": 0,
            "invalid_predictions": 0,
            "parse_failures": 0
        }
        
        # Load prompt
        if prompt_path is None:
            prompt_path = os.path.join(
                os.path.dirname(__file__),
                "prompts",
                "validity_fallback.txt"
            )
        
        self.prompt_template = self._load_prompt(prompt_path)
    
    def _load_prompt(self, path: str) -> str:
        """Load the fallback prompt from file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Fallback prompt not found: {path}, using default")
            return self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Default fallback prompt if file not found."""
        return """You are a formal logic expert. Determine if this syllogism is logically VALID or INVALID.

## Syllogism

{syllogism_text}

## Instructions

A syllogism is VALID if the conclusion NECESSARILY follows from the premises.
Focus ONLY on logical structure, NOT on real-world truth.

Analyze the syllogism step by step, then respond with ONLY one word:

VALID

or

INVALID"""
    
    def evaluate(
        self, 
        syllogism_text: str, 
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        Directly evaluate syllogism validity using LLM.
        
        Args:
            syllogism_text: The syllogism to evaluate
            temperature: LLM temperature (0.0 for deterministic)
            
        Returns:
            dict with prediction, raw_response, and success flag
        """
        self.stats["total_evaluations"] += 1
        
        prompt = self.prompt_template.format(syllogism_text=syllogism_text)
        
        try:
            response = self.client.generate(
                prompt=prompt,
                system_prompt="You are a formal logic expert specializing in syllogistic reasoning.",
                temperature=temperature
            )
            
            prediction = self._parse_response(response)
            
            if prediction == "VALID":
                self.stats["valid_predictions"] += 1
            else:
                self.stats["invalid_predictions"] += 1
            
            if self.verbose:
                print(f"  Fallback evaluation (t={temperature}): {prediction}")
            
            return {
                "success": True,
                "prediction": prediction,
                "raw_response": response,
                "temperature": temperature
            }
            
        except Exception as e:
            logger.error(f"Fallback evaluation error: {e}")
            return {
                "success": False,
                "prediction": "INVALID",  # Conservative default
                "error": str(e),
                "temperature": temperature
            }
    
    def _parse_response(self, response: str) -> str:
        """
        Extract VALID or INVALID from response.
        
        Strategy (in order of priority):
        1. Check last few lines for standalone VALID/INVALID (most reliable)
        2. Look for conclusion markers ("Final determination:", etc.)
        3. Find the LAST occurrence of VALID/INVALID (conclusion comes last)
        4. Default to INVALID if unclear (conservative)
        """
        import re
        
        response_clean = response.strip()
        response_upper = response_clean.upper()
        lines = response_clean.split('\n')
        
        # Strategy 1: Check last few lines for standalone VALID/INVALID
        for line in reversed(lines[-5:]):
            # Clean the line: remove markdown, asterisks, hashes, whitespace
            line_clean = line.strip().upper()
            line_clean = re.sub(r'[*#\-_]', '', line_clean).strip()
            
            if line_clean == "INVALID":
                return "INVALID"
            if line_clean == "VALID":
                return "VALID"
        
        # Strategy 2: Look for conclusion markers
        markers = [
            "FINAL DETERMINATION:",
            "FINAL ANSWER:",
            "CONCLUSION:",
            "THEREFORE:",
            "ANSWER:",
            "THE SYLLOGISM IS"
        ]
        
        for marker in markers:
            if marker in response_upper:
                # Get text after the marker
                after_marker = response_upper.split(marker)[-1]
                # Check first 50 chars after marker for the answer
                after_marker_short = after_marker[:50]
                
                # Check for INVALID first (more specific)
                if re.search(r'\bINVALID\b', after_marker_short):
                    return "INVALID"
                if re.search(r'\bVALID\b', after_marker_short):
                    return "VALID"
        
        # Strategy 3: Find the LAST occurrence of VALID/INVALID
        # Use word boundaries to match whole words only
        
        # Find all INVALID matches (whole word)
        invalid_matches = list(re.finditer(r'\bINVALID\b', response_upper))
        
        # Find all VALID matches that are NOT part of INVALID
        # We need to exclude "VALID" that appears inside "INVALID"
        valid_matches = []
        for m in re.finditer(r'\bVALID\b', response_upper):
            # Check if this VALID is part of an INVALID
            start = m.start()
            # INVALID contains VALID at position 2 (IN-VALID)
            # So check if there's "IN" before this VALID
            if start >= 2 and response_upper[start-2:start] == "IN":
                continue  # Skip, this is part of INVALID
            valid_matches.append(m)
        
        # Get positions of last occurrences
        last_invalid_pos = invalid_matches[-1].start() if invalid_matches else -1
        last_valid_pos = valid_matches[-1].start() if valid_matches else -1
        
        # The one that appears LAST is the answer (conclusion comes at the end)
        if last_invalid_pos > last_valid_pos:
            return "INVALID"
        elif last_valid_pos > last_invalid_pos:
            return "VALID"
        elif last_invalid_pos != -1:
            return "INVALID"
        elif last_valid_pos != -1:
            return "VALID"
        
        # Strategy 4: Default to INVALID if unclear (conservative approach)
        self.stats["parse_failures"] += 1
        logger.warning(f"Could not parse fallback response, defaulting to INVALID: {response_clean[-100:]}")
        return "INVALID"
    
    def evaluate_with_self_consistency(
        self,
        syllogism_text: str,
        num_samples: int = 3,
        temperature_schedule: List[float] = None
    ) -> Dict[str, Any]:
        """
        Evaluate using self-consistency voting for higher accuracy.
        
        Args:
            syllogism_text: The syllogism to evaluate
            num_samples: Number of samples for voting
            temperature_schedule: List of temperatures for each sample
            
        Returns:
            dict with prediction, votes, and voting info
        """
        if temperature_schedule is None:
            temperature_schedule = self.DEFAULT_TEMPERATURE_SCHEDULE
        
        # Get temperatures for requested samples
        if num_samples <= len(temperature_schedule):
            temperatures = temperature_schedule[:num_samples]
        else:
            # Extend with last temperature
            extra = num_samples - len(temperature_schedule)
            temperatures = temperature_schedule + [temperature_schedule[-1]] * extra
        
        votes = []
        responses = []
        
        if self.verbose:
            print(f"  Fallback self-consistency with {num_samples} samples...")
        
        for temp in temperatures:
            result = self.evaluate(syllogism_text, temperature=temp)
            votes.append(result["prediction"])
            responses.append(result)
            
            if self.verbose:
                print(f"    Sample (t={temp}): {result['prediction']}")
        
        # Majority vote
        valid_count = votes.count("VALID")
        invalid_count = votes.count("INVALID")
        
        winner = "VALID" if valid_count > invalid_count else "INVALID"
        
        if self.verbose:
            print(f"  Fallback voting: VALID={valid_count}, INVALID={invalid_count} -> {winner}")
        
        logger.info(f"Fallback self-consistency: VALID={valid_count}, INVALID={invalid_count} -> {winner}")
        
        return {
            "success": True,
            "prediction": winner,
            "votes": votes,
            "vote_counts": {
                "VALID": valid_count,
                "INVALID": invalid_count
            },
            "temperatures_used": temperatures,
            "had_disagreement": valid_count > 0 and invalid_count > 0
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get fallback evaluator statistics."""
        total = self.stats["total_evaluations"]
        return {
            **self.stats,
            "valid_rate": self.stats["valid_predictions"] / max(1, total),
            "invalid_rate": self.stats["invalid_predictions"] / max(1, total),
            "parse_failure_rate": self.stats["parse_failures"] / max(1, total)
        }
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            "total_evaluations": 0,
            "valid_predictions": 0,
            "invalid_predictions": 0,
            "parse_failures": 0
        }
