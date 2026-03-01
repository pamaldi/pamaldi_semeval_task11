"""
Post-processing validator for proposition types.
Automatically corrects I/O confusion based on text analysis.

This is the most common extraction error: O-type propositions
("Some S are NOT P") being misclassified as I-type ("Some S are P").
"""

import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PropositionTypeValidator:
    """
    Validates and corrects proposition types after LLM extraction.
    Focuses on I/O confusion which is the most common error.
    """
    
    # Patterns that indicate O-type (particular NEGATIVE: "Some S are NOT P")
    O_TYPE_PATTERNS = [
        # Direct negation patterns
        r'\bsome\b.+\bare\s+not\b',
        r'\bsome\b.+\bis\s+not\b',
        r'\bsome\b.+\bdo\s+not\b',
        r'\bsome\b.+\bdoes\s+not\b',
        r'\bsome\b.+\bcannot\b',
        r'\bsome\b.+\bcan\s*not\b',
        
        # "Not all" patterns (equivalent to O-type)
        r'\bnot\s+all\b',
        r'\bnot\s+every\b',
        
        # "There are X that are not Y" patterns
        r'\bthere\s+are\b.+\bthat\s+are\s+not\b',
        r'\bthere\s+are\b.+\bwhich\s+are\s+not\b',
        r'\bthere\s+are\b.+\bwho\s+are\s+not\b',
        r'\bthere\s+exist\b.+\bthat\s+are\s+not\b',
        r'\bthere\s+exist\b.+\bwhich\s+are\s+not\b',
        
        # "At least one X is not Y" patterns
        r'\bat\s+least\s+one\b.+\bis\s+not\b',
        r'\bat\s+least\s+one\b.+\bare\s+not\b',
        r'\bat\s+least\s+one\b.+\bwhich\s+is\s+not\b',
        
        # "A portion/number of X are not Y" patterns
        r'\ba\s+portion\s+of\b.+\bare\s+not\b',
        r'\ba\s+number\s+of\b.+\bare\s+not\b',
        r'\ba\s+certain\s+amount\b.+\bare\s+not\b',
        r'\ba\s+certain\s+amount\b.+\bdo\s+not\b',
        r'\ba\s+few\b.+\bare\s+not\b',
        r'\bcertain\b.+\bare\s+not\b',
        
        # "Fail to be" pattern
        r'\bfail\s+to\s+be\b',
        r'\bfails\s+to\s+be\b',
        
        # Contraction patterns
        r"\bsome\b.+\baren't\b",
        r"\bsome\b.+\bisn't\b",
        r"\bsome\b.+\bdon't\b",
        r"\bsome\b.+\bdoesn't\b",
        r"\bthere\s+are\b.+\baren't\b",
        r"\bthere\s+are\b.+\bisn't\b",
        
        # Additional patterns from real errors
        r'\bthere\s+are\s+some\b.+\bthat\s+are\s+not\b',
        r'\bthere\s+are\s+a\s+number\s+of\b.+\bwho\s+are\s+not\b',
        r'\bthere\s+are\s+a\s+number\s+of\b.+\bthat\s+are\s+not\b',
        r'\bsome\s+bodies\s+of\b.+\bare\s+not\b',
        r'\bdo\s+not\s+live\b',  # "salmons do not live in the sea"
    ]
    
    # Patterns that indicate E-type (universal NEGATIVE: "No S is P")
    # CRITICAL: These must be checked BEFORE O-type patterns!
    E_TYPE_PATTERNS = [
        # Standard "No X is Y" patterns
        r'\bno\s+\w+\s+(?:is|are)\b',  # "No X is/are Y"
        r'\bnothing\s+(?:that\s+)?is\b',
        r'\bthere\s+(?:is|are)\s+no\b',
        r'\bin\s+no\s+way\b',
        r'\bnever\b',
        r'\bcannot\s+be\b',
        r'\bno\s+\w+\s+can\s+be\b',
        
        # CRITICAL: "Not a single" = Universal Negative (E)
        # "Not a single X is Y" = "No X is Y"
        r'\bnot\s+a\s+single\b',
        r'\bthere\s+is\s+not\s+a\s+single\b',
        r'\bthere\s+are\s+not\s+a\s+single\b',
    ]
    
    # CRITICAL: Universal negatives with "anything/everything...is not"
    # These are E-type, NOT O-type!
    # "Anything that is X is not Y" = "No X is Y" (Universal Negative)
    UNIVERSAL_NEGATIVE_PATTERNS = [
        # "Anything/Everything...is not" = E (universal negative)
        r'\banything\s+(?:that\s+)?(?:is\s+)?.*?\bis\s+not\b',
        r'\beverything\s+(?:that\s+)?(?:is\s+)?.*?\bis\s+not\b',
        r'\bany\s+\w+\s+(?:that\s+)?(?:is\s+)?.*?\bis\s+not\b',
        r'\bevery\s+\w+\s+(?:that\s+)?(?:is\s+)?.*?\bis\s+not\b',
        r'\ball\s+\w+\s+(?:that\s+)?(?:are\s+)?.*?\bare\s+not\b',
        # "Anything that is X is also not Y"
        r'\banything\s+.*?\bis\s+also\s+not\b',
        r'\beverything\s+.*?\bis\s+also\s+not\b',
        # "Things that are X are not Y" (no "some" quantifier) = E
        # This means ALL things that are X, not just some
        r'^things\s+that\s+are\s+[\w\s]+\s+are\s+not\b',
        r'\bthings\s+that\s+are\s+[\w\s]+\s+are\s+not\b',
    ]
    
    # Patterns for explicit falsity markers → E
    FALSITY_PATTERNS = [
        # "It is (completely/entirely/totally) false that any X is Y" → E
        r'\bit\s+is\s+(?:\w+\s+)?false\s+that\s+(?:any|every|all)\b',
        # "It is not true that any X is Y" → E
        r'\bit\s+is\s+not\s+true\s+that\s+(?:any|every|all)\b',
    ]
    
    # Patterns that indicate A-type (universal AFFIRMATIVE: "All S are P")
    A_TYPE_PATTERNS = [
        r'\ball\b.+\bare\b',
        r'\bevery\b.+\bis\b',
        r'\bany\b.+\bis\b',
        r'\beach\b.+\bis\b',
        r'\bwithout\s+exception\b',
        r'\balways\b',
        r'\bevery\s+single\b',
    ]
    
    # Double negative patterns that convert E to A
    # "No X are not Y" = "All X are Y"
    DOUBLE_NEGATIVE_PATTERNS = [
        r'\bno\b.+\bare\s+not\b',
        r'\bno\b.+\bis\s+not\b',
        r'\bno\b.+\bwho\s+are\s+not\b',
        r'\bno\b.+\bthat\s+are\s+not\b',
        r'\bthere\s+are\s+no\b.+\bwho\s+are\s+not\b',
        r'\bthere\s+are\s+no\b.+\bthat\s+are\s+not\b',
        r'\bthere\s+is\s+no\b.+\bthat\s+is\s+not\b',
    ]
    
    def __init__(self, log_corrections: bool = True, verbose: bool = False):
        """
        Initialize the validator.
        
        Args:
            log_corrections: Whether to log when corrections are made
            verbose: Whether to print corrections to console
        """
        self.log_corrections = log_corrections
        self.verbose = verbose
        self.correction_stats = {
            "total_checked": 0,
            "i_to_o": 0,
            "o_to_i": 0,
            "e_to_a": 0,
            "other_corrections": 0,
        }
    
    def validate_proposition(self, proposition: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and potentially correct a proposition's type.
        
        Args:
            proposition: Dict with keys 'type', 'subject', 'predicate', 'raw_text'
            
        Returns:
            The proposition dict, potentially with corrected 'type'
        """
        self.correction_stats["total_checked"] += 1
        
        raw_text = proposition.get("raw_text", "").lower()
        declared_type = proposition.get("type", "").upper()
        
        if not raw_text or not declared_type:
            return proposition
        
        # Detect actual type from text
        detected_type = self._detect_type_from_text(raw_text, declared_type)
        
        # If detection is confident and differs from declared, correct it
        if detected_type and detected_type != declared_type:
            old_type = declared_type
            proposition["type"] = detected_type
            proposition["type_corrected"] = True
            proposition["original_type"] = old_type
            
            # Update stats
            if old_type == "I" and detected_type == "O":
                self.correction_stats["i_to_o"] += 1
            elif old_type == "O" and detected_type == "I":
                self.correction_stats["o_to_i"] += 1
            elif old_type == "E" and detected_type == "A":
                self.correction_stats["e_to_a"] += 1
            else:
                self.correction_stats["other_corrections"] += 1
            
            if self.log_corrections:
                logger.warning(
                    f"Type corrected: {old_type} → {detected_type} | "
                    f"Text: '{raw_text[:60]}...'"
                )
            
            if self.verbose:
                print(f"  ⚠ Type corrected: {old_type} → {detected_type}")
                print(f"    Text: '{raw_text[:60]}...'")
        
        return proposition
    
    def _detect_type_from_text(self, text: str, declared_type: str) -> Optional[str]:
        """
        Detect proposition type from text using pattern matching.
        
        PRIORITY ORDER (critical for correct detection):
        1. Double negatives (E → A): "No X are not Y" = "All X are Y"
        2. "Not all/every" (O): "Not all X are Y" = particular negative
        3. Explicit falsity (E): "It is false that any X is Y"
        4. Universal negatives (E): "Anything...is not", "Not a single", "Things that are X are not Y"
        5. Standard E-type: "No X is Y"
        6. O-type (particular negative): "Some X are not Y"
        7. A-type (universal affirmative): "All X are Y"
        8. I-type (particular affirmative): "Some X are Y"
        
        Args:
            text: The raw text of the proposition (lowercase)
            declared_type: The type declared by the LLM
            
        Returns:
            Detected type (A, E, I, O) or None if uncertain
        """
        text = text.lower().strip()
        
        # PRIORITY 1: Check for double negatives (E → A conversion)
        # "No X are not Y" = "All X are Y"
        if self._matches_any_pattern(text, self.DOUBLE_NEGATIVE_PATTERNS):
            return "A"
        
        # PRIORITY 2: "Not all/every" = O (particular negative)
        # This must come BEFORE universal negative check!
        if re.search(r'\bnot\s+all\b', text) or re.search(r'\bnot\s+every\b', text):
            return "O"
        
        # PRIORITY 3: Explicit falsity markers → E
        # "It is false that any X is Y" = "No X is Y"
        if self._matches_any_pattern(text, self.FALSITY_PATTERNS):
            return "E"
        
        # PRIORITY 4: Check for universal negatives with "anything/everything...is not"
        # CRITICAL: These are E-type, NOT O-type!
        # "Anything that is X is not Y" = "No X is Y" (Universal Negative)
        # "Things that are X are not Y" = "No X is Y" (Universal Negative)
        if self._matches_any_pattern(text, self.UNIVERSAL_NEGATIVE_PATTERNS):
            # Make sure it's not "some things that are X are not Y" (which is O)
            if not re.search(r'\bsome\s+things\b', text):
                return "E"
        
        # PRIORITY 5: Check for standard E-type patterns
        if self._matches_any_pattern(text, self.E_TYPE_PATTERNS):
            return "E"
        
        # PRIORITY 6: Check for O-type (most common error is I→O)
        # But only if NOT a universal statement
        if self._matches_any_pattern(text, self.O_TYPE_PATTERNS):
            # Make sure it's not a universal statement being misclassified
            if not self._is_universal_statement(text):
                return "O"
        
        # PRIORITY 7: Check for A-type
        if self._matches_any_pattern(text, self.A_TYPE_PATTERNS):
            # Make sure there's no negation
            if not self._has_negation(text):
                return "A"
        
        # PRIORITY 8: Check for I-type (particular affirmative - NO negation)
        # Only correct O→I if we're confident there's no negation
        if declared_type == "O" and self._is_particular_proposition(text):
            if not self._has_negation(text):
                return "I"
        
        return None  # Uncertain, don't change
    
    def _is_universal_statement(self, text: str) -> bool:
        """Check if the text is a universal statement (all/every/any/anything).
        
        Note: "Not all" is NOT a universal statement - it's particular (O-type).
        """
        # First check if it's "not all/every" - these are NOT universal
        if re.search(r'\bnot\s+all\b', text) or re.search(r'\bnot\s+every\b', text):
            return False
        
        universal_indicators = [
            r'\ball\b',
            r'\bevery\b',
            r'\bany\b',
            r'\banything\b',
            r'\beverything\b',
            r'\beach\b',
            r'\bwithout\s+exception\b',
        ]
        return self._matches_any_pattern(text, universal_indicators)
    
    def _matches_any_pattern(self, text: str, patterns: list) -> bool:
        """Check if text matches any of the given patterns."""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def _is_particular_proposition(self, text: str) -> bool:
        """Check if the proposition is particular (some/a few/at least one)."""
        particular_indicators = [
            r'\bsome\b',
            r'\ba\s+few\b',
            r'\bat\s+least\s+one\b',
            r'\ba\s+portion\b',
            r'\ba\s+number\b',
            r'\bcertain\b',
            r'\bthere\s+(?:are|exist)\b',
        ]
        return self._matches_any_pattern(text, particular_indicators)
    
    def _has_negation(self, text: str) -> bool:
        """Check if the text contains negation AFTER the copula."""
        # Look for negation patterns
        negation_patterns = [
            r'\bare\s+not\b',
            r'\bis\s+not\b',
            r'\bdo\s+not\b',
            r'\bdoes\s+not\b',
            r'\bnot\s+all\b',
            r'\bnot\s+every\b',
            r"\baren't\b",
            r"\bisn't\b",
            r"\bdon't\b",
            r"\bdoesn't\b",
            r'\bcannot\b',
            r'\bcan\s*not\b',
            r'\bfail\s+to\b',
            r'\bfails\s+to\b',
        ]
        return self._matches_any_pattern(text, negation_patterns)
    
    def validate_extraction(self, extraction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate all propositions in an extraction result.
        
        Args:
            extraction: Full extraction dict with premise1, premise2, conclusion
            
        Returns:
            Extraction with validated/corrected proposition types
        """
        if not extraction:
            return extraction
        
        # Validate each proposition
        for key in ["premise1", "premise2", "conclusion"]:
            if key in extraction and extraction[key]:
                extraction[key] = self.validate_proposition(extraction[key])
        
        # Recalculate mood if any type was corrected
        types_corrected = any(
            extraction.get(key, {}).get("type_corrected", False)
            for key in ["premise1", "premise2", "conclusion"]
        )
        
        if types_corrected:
            # Recalculate mood
            old_mood = extraction.get("mood", "")
            new_mood = (
                extraction.get("premise1", {}).get("type", "") +
                extraction.get("premise2", {}).get("type", "") +
                extraction.get("conclusion", {}).get("type", "")
            )
            
            if new_mood != old_mood:
                extraction["mood"] = new_mood
                extraction["mood_corrected"] = True
                extraction["original_mood"] = old_mood
                
                # Update form
                figure = extraction.get("figure", "")
                extraction["form"] = f"{new_mood}-{figure}"
                
                if self.log_corrections:
                    logger.info(
                        f"Mood recalculated: {old_mood} → {new_mood} | "
                        f"Form: {extraction['form']}"
                    )
                
                if self.verbose:
                    print(f"  ⚠ Mood recalculated: {old_mood} → {new_mood}")
                    print(f"    New form: {extraction['form']}")
        
        return extraction
    
    def get_stats(self) -> Dict[str, int]:
        """Return correction statistics."""
        return self.correction_stats.copy()
    
    def reset_stats(self):
        """Reset correction statistics."""
        self.correction_stats = {
            "total_checked": 0,
            "i_to_o": 0,
            "o_to_i": 0,
            "e_to_a": 0,
            "other_corrections": 0,
        }


# Singleton instance for easy access
_validator_instance = None


def get_validator(log_corrections: bool = True, verbose: bool = False) -> PropositionTypeValidator:
    """Get the singleton validator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = PropositionTypeValidator(
            log_corrections=log_corrections,
            verbose=verbose
        )
    return _validator_instance


def validate_extraction(extraction: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to validate an extraction."""
    return get_validator().validate_extraction(extraction)
