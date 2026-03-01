"""
Deterministic Post-Processor for Syllogism Figure Calculation

This module takes the LLM's extraction output (types and terms only) and
mechanically computes the figure, mood, form, and validity.

This removes the error-prone figure calculation from the LLM.

Pipeline:
1. Validate Types - Check type matches raw_text patterns
2. Normalize Terms - Standardize terms for comparison
3. Identify Terms - Find S, P, M from extraction
4. Validate Distribution - Check term placement rules
5. Compute Figure - THE KEY FIX! Deterministic figure calculation
6. Build Mood & Form - Combine types and figure
7. Check Validity - Against 24 valid forms
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple, List, Set

logger = logging.getLogger(__name__)


class DeterministicPostProcessor:
    """
    Deterministic post-processor for syllogism extractions.
    
    Takes LLM extraction (types + terms) and computes figure, mood, form, validity.
    """
    
    # Type patterns for validation
    TYPE_PATTERNS = {
        'A': [r'\ball\b', r'\bevery\b', r'\bany\b', r'\beach\b', r'\bwhatever\b',
              r'\banything\s+that\b', r'\bwithout\s+exception\b', r'\balways\b',
              r'\bevery\s+single\b'],
        'E': [r'\bno\s+\w+\s+(?:is|are)\b', r'\bnone\b', r'\bnever\b', r'\bnothing\b',
              r'\bnot\s+a\s+single\b', r'\bthere\s+(?:is|are)\s+no\b',
              r'\bcannot\s+be\b', r'\bin\s+no\s+way\b'],
        'I': [r'\bsome\b(?!.*\bnot\b)', r'\ba\s+few\b', r'\bthere\s+are\b(?!.*\bnot\b)',
              r'\bcertain\b', r'\bat\s+least\s+one\b(?!.*\bnot\b)',
              r'\ba\s+portion\s+of\b', r'\bthere\s+exist\b', r'\ba\s+number\s+of\b'],
        'O': [r'\bsome\b.*\bnot\b', r'\bnot\s+all\b', r'\bnot\s+every\b',
              r'\bthere\s+are\b.*\bnot\b', r'\bfail\s+to\s+be\b',
              r'\bat\s+least\s+one\b.*\bnot\b', r'\ba\s+portion\b.*\bnot\b',
              r'\bdo\s+not\b', r'\bdoes\s+not\b', r'\bare\s+not\b', r'\bis\s+not\b']
    }
    
    # All 24 valid syllogistic forms (Aristotelian interpretation)
    VALID_FORMS = {
        # Figure 1: M-P, S-M
        "AAA-1", "EAE-1", "AII-1", "EIO-1", "AAI-1", "EAO-1",
        # Figure 2: P-M, S-M
        "EAE-2", "AEE-2", "EIO-2", "AOO-2", "EAO-2", "AEO-2",
        # Figure 3: M-P, M-S
        "IAI-3", "AII-3", "OAO-3", "EIO-3", "AAI-3", "EAO-3",
        # Figure 4: P-M, M-S
        "AEE-4", "IAI-4", "EIO-4", "AEO-4", "EAO-4", "AAI-4"
    }
    
    # Traditional Latin names
    FORM_NAMES = {
        "AAA-1": "Barbara", "EAE-1": "Celarent", "AII-1": "Darii",
        "EIO-1": "Ferio", "AAI-1": "Barbari", "EAO-1": "Celaront",
        "EAE-2": "Cesare", "AEE-2": "Camestres", "EIO-2": "Festino",
        "AOO-2": "Baroco", "EAO-2": "Cesaro", "AEO-2": "Camestrop",
        "IAI-3": "Disamis", "AII-3": "Datisi", "OAO-3": "Bocardo",
        "EIO-3": "Ferison", "AAI-3": "Darapti", "EAO-3": "Felapton",
        "AEE-4": "Camenes", "IAI-4": "Dimaris", "EIO-4": "Fresison",
        "AEO-4": "Camenop", "EAO-4": "Fesapo", "AAI-4": "Bramantip"
    }
    
    # Figure lookup table
    FIGURE_TABLE = {
        ("SUBJECT", "PREDICATE"): 1,
        ("PREDICATE", "PREDICATE"): 2,
        ("SUBJECT", "SUBJECT"): 3,
        ("PREDICATE", "SUBJECT"): 4
    }
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the post-processor.
        
        Args:
            verbose: Whether to print detailed logs
        """
        self.verbose = verbose
        self.log_lines = []
    
    def _log(self, message: str, level: str = "INFO"):
        """Add a log line."""
        self.log_lines.append(f"[{level}] {message}")
        if self.verbose:
            print(message)
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.debug(message)
    
    def process(self, extraction: Dict[str, Any], syllogism_id: str = None) -> Dict[str, Any]:
        """
        Process an LLM extraction to compute figure, mood, form, and validity.
        
        Args:
            extraction: Dict with premise1, premise2, conclusion (each with type, subject, predicate, raw_text)
            syllogism_id: Optional ID for logging
            
        Returns:
            Dict with success, terms, m_positions, figure, mood, form, validity, validity_reason, warnings, errors
        """
        self.log_lines = []
        warnings = []
        errors = []
        
        self._log("=" * 80)
        self._log(f"DETERMINISTIC POST-PROCESSOR")
        if syllogism_id:
            self._log(f"Syllogism ID: {syllogism_id}")
        self._log("=" * 80)
        
        # Store original LLM values for comparison
        llm_figure = extraction.get("figure")
        llm_mood = extraction.get("mood")
        llm_form = extraction.get("form")
        
        # PHASE 1: Validate Types
        self._log("\n[PHASE 1] Type Validation")
        type_results = self._phase1_validate_types(extraction)
        for prop_name, result in type_results.items():
            if result["corrected"]:
                warnings.append(f"Type corrected for {prop_name}: {result['original']} → {result['corrected_to']}")
                extraction[prop_name]["type"] = result["corrected_to"]
        
        # PHASE 2: Normalize Terms
        self._log("\n[PHASE 2] Term Normalization")
        normalized = self._phase2_normalize_terms(extraction)
        
        # PHASE 3: Identify S, P, M
        self._log("\n[PHASE 3] Term Identification")
        S, P, M, term_errors = self._phase3_identify_terms(normalized)
        if term_errors:
            errors.extend(term_errors)
        
        if M is None:
            self._log("  ✗ Could not identify middle term!", "ERROR")
            return {
                "success": False,
                "errors": errors,
                "warnings": warnings,
                "log": "\n".join(self.log_lines)
            }
        
        # PHASE 4: Validate Distribution
        self._log("\n[PHASE 4] Distribution Validation")
        dist_errors = self._phase4_validate_distribution(normalized, S, P, M)
        if dist_errors:
            errors.extend(dist_errors)
        
        # PHASE 5: Compute Figure (THE KEY FIX!)
        self._log("\n[PHASE 5] Figure Computation ⭐ KEY STEP")
        figure, m_positions = self._phase5_compute_figure(normalized, M)
        
        if figure is None:
            self._log("  ✗ Could not compute figure!", "ERROR")
            errors.append("Could not determine figure from M positions")
            return {
                "success": False,
                "errors": errors,
                "warnings": warnings,
                "log": "\n".join(self.log_lines)
            }
        
        # Check if figure was corrected
        if llm_figure is not None and llm_figure != figure:
            self._log(f"  ⚠️ LLM had: Figure {llm_figure}")
            self._log(f"  ✓ Corrected: Figure {figure}")
            warnings.append(f"Figure corrected: {llm_figure} → {figure}")
        
        # PHASE 6: Build Mood & Form
        self._log("\n[PHASE 6] Mood & Form Construction")
        mood, form = self._phase6_build_mood_and_form(extraction, figure)
        
        if llm_mood and llm_mood != mood:
            warnings.append(f"Mood corrected: {llm_mood} → {mood}")
        if llm_form and llm_form != form:
            self._log(f"  ⚠️ LLM had: {llm_form}")
            self._log(f"  ✓ Corrected: {form}")
            warnings.append(f"Form corrected: {llm_form} → {form}")
        
        # PHASE 7: Check Validity
        self._log("\n[PHASE 7] Validity Check")
        validity, validity_reason = self._phase7_check_validity(form)
        
        # Final summary
        self._log("\n" + "=" * 80)
        self._log("FINAL RESULT")
        self._log("=" * 80)
        self._log(f"  Terms: S={S}, P={P}, M={M}")
        self._log(f"  M positions: P1={m_positions['in_premise1']}, P2={m_positions['in_premise2']}")
        self._log(f"  Figure: {figure}" + (f" (was {llm_figure})" if llm_figure and llm_figure != figure else ""))
        self._log(f"  Mood: {mood}")
        self._log(f"  Form: {form}" + (f" (was {llm_form})" if llm_form and llm_form != form else ""))
        self._log(f"  Valid: {validity}")
        self._log(f"  Reason: {validity_reason}")
        if warnings:
            self._log(f"  Corrections Made: {len(warnings)}")
        self._log("=" * 80)
        
        return {
            "success": True,
            "warnings": warnings,
            "errors": errors,
            "terms": {
                "S": S,
                "P": P,
                "M": M
            },
            "m_positions": m_positions,
            "figure": figure,
            "mood": mood,
            "form": form,
            "validity": validity,
            "validity_reason": validity_reason,
            "form_name": self.FORM_NAMES.get(form),
            "log": "\n".join(self.log_lines)
        }
    
    # =========================================================================
    # PHASE 1: Type Validation
    # =========================================================================
    
    def _phase1_validate_types(self, extraction: Dict[str, Any]) -> Dict[str, Dict]:
        """Validate that declared types match raw_text patterns."""
        results = {}
        
        for prop_name in ["premise1", "premise2", "conclusion"]:
            prop = extraction.get(prop_name, {})
            declared_type = prop.get("type", "").upper()
            raw_text = prop.get("raw_text", "")
            
            is_valid, suggested = self._validate_single_type(declared_type, raw_text)
            
            results[prop_name] = {
                "declared": declared_type,
                "valid": is_valid,
                "corrected": not is_valid and suggested is not None,
                "corrected_to": suggested,
                "original": declared_type if not is_valid else None
            }
            
            if is_valid:
                self._log(f"  {prop_name}: type={declared_type} ✓")
            else:
                if suggested:
                    self._log(f"  {prop_name}: type={declared_type} → {suggested} (corrected)")
                else:
                    self._log(f"  {prop_name}: type={declared_type} (could not validate)")
        
        return results
    
    def _validate_single_type(self, prop_type: str, raw_text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a single proposition type against its raw text.
        
        PRIORITY ORDER (critical for correct detection):
        1. Double negatives (E → A): "No X are not Y" = "All X are Y"
        2. "Not all/every" (O): "Not all X are Y" = particular negative
        3. Explicit falsity (E): "It is false that any X is Y"
        4. Universal negatives (E): "Anything...is not", "Not a single", "Things that are X are not Y"
        5. Standard E-type: "No X is Y"
        6. O-type (particular negative): "Some X are not Y"
        7. A-type (universal affirmative): "All X are Y"
        8. I-type (particular affirmative): "Some X are Y"
        
        Returns (is_valid, suggested_correction_or_None)
        """
        if not raw_text:
            return True, None  # Can't validate without text
        
        raw_lower = raw_text.lower()
        
        # PRIORITY 1: Double negatives (E → A)
        # "No X are not Y" = "All X are Y"
        double_neg_patterns = [
            r'\bno\b.+\bare\s+not\b',
            r'\bno\b.+\bis\s+not\b',
            r'\bthere\s+are\s+no\b.+\bwho\s+are\s+not\b',
            r'\bthere\s+are\s+no\b.+\bthat\s+are\s+not\b',
        ]
        for pattern in double_neg_patterns:
            if re.search(pattern, raw_lower):
                if prop_type == 'A':
                    return True, None
                else:
                    return False, 'A'
        
        # PRIORITY 2: "Not all/every" = O (particular negative)
        if re.search(r'\bnot\s+all\b', raw_lower) or re.search(r'\bnot\s+every\b', raw_lower):
            if prop_type == 'O':
                return True, None
            else:
                return False, 'O'
        
        # PRIORITY 3: Explicit falsity markers → E
        # "It is (completely/entirely) false that any X is Y" = "No X is Y"
        falsity_patterns = [
            r'\bit\s+is\s+(?:\w+\s+)?false\s+that\s+(?:any|every|all)\b',
            r'\bit\s+is\s+not\s+true\s+that\s+(?:any|every|all)\b',
        ]
        for pattern in falsity_patterns:
            if re.search(pattern, raw_lower):
                if prop_type == 'E':
                    return True, None
                else:
                    return False, 'E'
        
        # PRIORITY 4: Universal negatives with "anything/everything...is not"
        # CRITICAL: These are E-type, NOT O-type!
        universal_neg_patterns = [
            r'\banything\s+(?:that\s+)?(?:is\s+)?.*?\bis\s+not\b',
            r'\beverything\s+(?:that\s+)?(?:is\s+)?.*?\bis\s+not\b',
            r'\bany\s+\w+\s+(?:that\s+)?(?:is\s+)?.*?\bis\s+not\b',
            r'\bevery\s+\w+\s+(?:that\s+)?(?:is\s+)?.*?\bis\s+not\b',
            r'\ball\s+\w+\s+(?:that\s+)?(?:are\s+)?.*?\bare\s+not\b',
            # "Things that are X are not Y" (no "some" quantifier) = E
            r'^things\s+that\s+are\s+[\w\s]+\s+are\s+not\b',
        ]
        for pattern in universal_neg_patterns:
            if re.search(pattern, raw_lower):
                # Make sure it's not "some things that are X are not Y" (which is O)
                if not re.search(r'\bsome\s+things\b', raw_lower):
                    if prop_type == 'E':
                        return True, None
                    else:
                        return False, 'E'
        
        # PRIORITY 5: Standard E-type patterns (including "not a single")
        e_patterns = [
            r'\bnot\s+a\s+single\b',
            r'\bthere\s+is\s+not\s+a\s+single\b',
        ]
        for pattern in e_patterns:
            if re.search(pattern, raw_lower):
                if prop_type == 'E':
                    return True, None
                else:
                    return False, 'E'
        
        # Check standard E patterns
        for pattern in self.TYPE_PATTERNS['E']:
            if re.search(pattern, raw_lower):
                if prop_type == 'E':
                    return True, None
                # Don't immediately correct - might be other type
        
        # PRIORITY 6: Check O (particular negative with negation)
        # But only if NOT a universal statement
        is_universal = any(re.search(p, raw_lower) for p in [
            r'\ball\b', r'\bevery\b', r'\bany\b', r'\banything\b', r'\beverything\b',
            r'^things\s+that\s+are\b'  # "Things that are X" without "some" is universal
        ])
        
        if not is_universal:
            for pattern in self.TYPE_PATTERNS['O']:
                if re.search(pattern, raw_lower):
                    if prop_type == 'O':
                        return True, None
                    else:
                        return False, 'O'
        
        # PRIORITY 7: Check A (universal affirmative)
        for pattern in self.TYPE_PATTERNS['A']:
            if re.search(pattern, raw_lower):
                if prop_type == 'A':
                    return True, None
        
        # PRIORITY 8: Check I (particular affirmative - no negation)
        for pattern in self.TYPE_PATTERNS['I']:
            if re.search(pattern, raw_lower):
                if prop_type == 'I':
                    return True, None
        
        return True, None  # Can't determine, trust LLM
    
    # =========================================================================
    # PHASE 2: Term Normalization
    # =========================================================================
    
    def _phase2_normalize_terms(self, extraction: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize all terms in the extraction."""
        normalized = {}
        
        for prop_name in ["premise1", "premise2", "conclusion"]:
            prop = extraction.get(prop_name, {})
            orig_subj = prop.get("subject", "")
            orig_pred = prop.get("predicate", "")
            
            norm_subj = self._normalize_term(orig_subj)
            norm_pred = self._normalize_term(orig_pred)
            
            normalized[prop_name] = {
                "type": prop.get("type", "").upper(),
                "subject": norm_subj,
                "predicate": norm_pred,
                "raw_text": prop.get("raw_text", ""),
                "original_subject": orig_subj,
                "original_predicate": orig_pred
            }
            
            self._log(f"  {prop_name}: subj=\"{orig_subj}\" → \"{norm_subj}\", pred=\"{orig_pred}\" → \"{norm_pred}\"")
        
        return normalized
    
    def _normalize_term(self, term: str) -> str:
        """Normalize a term for comparison."""
        if not term:
            return ""
        
        # Lowercase
        term = term.lower().strip()
        
        # Remove articles
        term = re.sub(r'^(the|a|an)\s+', '', term)
        
        # Normalize "things that are X" → "X"
        term = re.sub(
            r'^(things?|creatures?|items?|objects?|persons?|people|beings?)\s+'
            r'(that|which|who)\s+(are|is)\s+',
            '', term
        )
        
        # Normalize "person who is a X" → "X"
        term = re.sub(r'^person\s+who\s+is\s+(a\s+)?', '', term)
        
        # Remove leading articles again (in case they were exposed)
        term = re.sub(r'^(the|a|an)\s+', '', term)
        
        # Normalize spaces
        term = re.sub(r'\s+', ' ', term).strip()
        
        return term
    
    # =========================================================================
    # PHASE 3: Term Identification
    # =========================================================================
    
    def _phase3_identify_terms(self, normalized: Dict[str, Any]) -> Tuple[str, str, Optional[str], List[str]]:
        """
        Identify S, P, M from the normalized extraction.
        
        Returns (S, P, M, errors)
        """
        errors = []
        
        # S and P come from conclusion
        S = normalized["conclusion"]["subject"]
        P = normalized["conclusion"]["predicate"]
        
        self._log(f"  From conclusion:")
        self._log(f"    S (minor term) = \"{S}\"")
        self._log(f"    P (major term) = \"{P}\"")
        
        # Get all terms from premises
        p1_terms = {
            normalized["premise1"]["subject"],
            normalized["premise1"]["predicate"]
        }
        p2_terms = {
            normalized["premise2"]["subject"],
            normalized["premise2"]["predicate"]
        }
        conclusion_terms = {S, P}
        
        self._log(f"  P1 terms: {p1_terms}")
        self._log(f"  P2 terms: {p2_terms}")
        self._log(f"  Conclusion terms: {conclusion_terms}")
        
        # M = intersection of premise terms, minus conclusion terms
        common_terms = p1_terms & p2_terms
        self._log(f"  Common in premises: {common_terms}")
        
        M_candidates = common_terms - conclusion_terms
        self._log(f"  After removing S,P: {M_candidates}")
        
        if len(M_candidates) == 0:
            # Try fuzzy matching
            M = self._fuzzy_find_middle_term(p1_terms, p2_terms, conclusion_terms)
            if M:
                self._log(f"  M (middle term) = \"{M}\" (found via fuzzy match)")
            else:
                errors.append("No middle term found")
                self._log(f"  ✗ No middle term found!", "ERROR")
        elif len(M_candidates) == 1:
            M = list(M_candidates)[0]
            self._log(f"  M (middle term) = \"{M}\" ✓")
        else:
            errors.append(f"Multiple middle term candidates: {M_candidates}")
            M = list(M_candidates)[0]
            self._log(f"  ⚠ Multiple candidates, using: \"{M}\"", "WARNING")
        
        return S, P, M, errors
    
    def _fuzzy_find_middle_term(self, p1_terms: Set[str], p2_terms: Set[str], 
                                 conclusion_terms: Set[str]) -> Optional[str]:
        """Try to find middle term via fuzzy matching."""
        # Look for terms that appear in both premises but not conclusion
        # using substring matching
        
        for t1 in p1_terms:
            for t2 in p2_terms:
                # Check if one contains the other
                if t1 in t2 or t2 in t1:
                    candidate = t1 if len(t1) <= len(t2) else t2
                    # Make sure it's not in conclusion
                    if candidate not in conclusion_terms:
                        in_conclusion = any(candidate in ct or ct in candidate 
                                           for ct in conclusion_terms)
                        if not in_conclusion:
                            return candidate
        
        return None
    
    # =========================================================================
    # PHASE 4: Distribution Validation
    # =========================================================================
    
    def _phase4_validate_distribution(self, normalized: Dict[str, Any], 
                                       S: str, P: str, M: str) -> List[str]:
        """Validate term distribution rules."""
        errors = []
        
        p1_subj = normalized["premise1"]["subject"]
        p1_pred = normalized["premise1"]["predicate"]
        p2_subj = normalized["premise2"]["subject"]
        p2_pred = normalized["premise2"]["predicate"]
        c_subj = normalized["conclusion"]["subject"]
        c_pred = normalized["conclusion"]["predicate"]
        
        # M must be in both premises
        m_in_p1 = M in {p1_subj, p1_pred} or self._term_matches(M, p1_subj) or self._term_matches(M, p1_pred)
        m_in_p2 = M in {p2_subj, p2_pred} or self._term_matches(M, p2_subj) or self._term_matches(M, p2_pred)
        
        if m_in_p1:
            pos = "subject" if (M == p1_subj or self._term_matches(M, p1_subj)) else "predicate"
            self._log(f"  ✓ M \"{M}\" in P1: YES (as {pos})")
        else:
            self._log(f"  ✗ M \"{M}\" in P1: NO", "ERROR")
            errors.append(f"M '{M}' not found in premise1")
        
        if m_in_p2:
            pos = "subject" if (M == p2_subj or self._term_matches(M, p2_subj)) else "predicate"
            self._log(f"  ✓ M \"{M}\" in P2: YES (as {pos})")
        else:
            self._log(f"  ✗ M \"{M}\" in P2: NO", "ERROR")
            errors.append(f"M '{M}' not found in premise2")
        
        # M must NOT be in conclusion
        m_in_c = M in {c_subj, c_pred} or self._term_matches(M, c_subj) or self._term_matches(M, c_pred)
        if not m_in_c:
            self._log(f"  ✓ M \"{M}\" not in conclusion: CORRECT")
        else:
            self._log(f"  ⚠ M \"{M}\" appears in conclusion", "WARNING")
        
        # S must be conclusion subject
        if S == c_subj or self._term_matches(S, c_subj):
            self._log(f"  ✓ S = conclusion.subject: MATCH")
        else:
            self._log(f"  ⚠ S \"{S}\" != conclusion.subject \"{c_subj}\"", "WARNING")
        
        # P must be conclusion predicate
        if P == c_pred or self._term_matches(P, c_pred):
            self._log(f"  ✓ P = conclusion.predicate: MATCH")
        else:
            self._log(f"  ⚠ P \"{P}\" != conclusion.predicate \"{c_pred}\"", "WARNING")
        
        return errors
    
    def _term_matches(self, t1: str, t2: str) -> bool:
        """Check if two terms match (exact or substring)."""
        if not t1 or not t2:
            return False
        return t1 == t2 or t1 in t2 or t2 in t1
    
    # =========================================================================
    # PHASE 5: Compute Figure (THE KEY FIX!)
    # =========================================================================
    
    def _phase5_compute_figure(self, normalized: Dict[str, Any], M: str) -> Tuple[Optional[int], Dict[str, str]]:
        """
        Compute figure based on M's position in each premise.
        
        Returns (figure, positions_dict)
        """
        p1_subj = normalized["premise1"]["subject"]
        p1_pred = normalized["premise1"]["predicate"]
        p2_subj = normalized["premise2"]["subject"]
        p2_pred = normalized["premise2"]["predicate"]
        
        self._log(f"  M = \"{M}\"")
        self._log(f"  In P1: subject=\"{p1_subj}\", predicate=\"{p1_pred}\"")
        
        # Find M's position in P1
        if M == p1_subj or self._term_matches(M, p1_subj):
            m_in_p1 = "SUBJECT"
            self._log(f"      M == subject? YES → M is SUBJECT in P1")
        elif M == p1_pred or self._term_matches(M, p1_pred):
            m_in_p1 = "PREDICATE"
            self._log(f"      M == predicate? YES → M is PREDICATE in P1")
        else:
            m_in_p1 = "NOT_FOUND"
            self._log(f"      M not found in P1!", "ERROR")
        
        self._log(f"  In P2: subject=\"{p2_subj}\", predicate=\"{p2_pred}\"")
        
        # Find M's position in P2
        if M == p2_subj or self._term_matches(M, p2_subj):
            m_in_p2 = "SUBJECT"
            self._log(f"      M == subject? YES → M is SUBJECT in P2")
        elif M == p2_pred or self._term_matches(M, p2_pred):
            m_in_p2 = "PREDICATE"
            self._log(f"      M == predicate? YES → M is PREDICATE in P2")
        else:
            m_in_p2 = "NOT_FOUND"
            self._log(f"      M not found in P2!", "ERROR")
        
        positions = {"in_premise1": m_in_p1, "in_premise2": m_in_p2}
        
        # Figure lookup
        figure = self.FIGURE_TABLE.get((m_in_p1, m_in_p2))
        
        if figure:
            self._log(f"  Lookup: ({m_in_p1}, {m_in_p2}) → FIGURE {figure}")
            self._log(f"  Result: Figure = {figure} ✓")
        else:
            self._log(f"  Lookup: ({m_in_p1}, {m_in_p2}) → NOT FOUND", "ERROR")
        
        return figure, positions
    
    # =========================================================================
    # PHASE 6: Build Mood & Form
    # =========================================================================
    
    def _phase6_build_mood_and_form(self, extraction: Dict[str, Any], figure: int) -> Tuple[str, str]:
        """Build mood from types and combine with figure."""
        p1_type = extraction.get("premise1", {}).get("type", "").upper()
        p2_type = extraction.get("premise2", {}).get("type", "").upper()
        c_type = extraction.get("conclusion", {}).get("type", "").upper()
        
        mood = f"{p1_type}{p2_type}{c_type}"
        form = f"{mood}-{figure}"
        
        self._log(f"  P1.type = {p1_type}")
        self._log(f"  P2.type = {p2_type}")
        self._log(f"  Conclusion.type = {c_type}")
        self._log(f"  Mood = \"{p1_type}\" + \"{p2_type}\" + \"{c_type}\" = \"{mood}\"")
        self._log(f"  Form = \"{mood}\" + \"-\" + \"{figure}\" = \"{form}\"")
        
        return mood, form
    
    # =========================================================================
    # PHASE 7: Check Validity
    # =========================================================================
    
    def _phase7_check_validity(self, form: str) -> Tuple[bool, str]:
        """Check if form is valid and return reason."""
        self._log(f"  Form: \"{form}\"")
        self._log(f"  Checking against 24 valid forms...")
        
        if form in self.VALID_FORMS:
            name = self.FORM_NAMES.get(form, "Unknown")
            self._log(f"  {form} in VALID_FORMS? YES ({name})")
            self._log(f"  Result: VALID ✓")
            return True, f"{form} is valid ({name})"
        else:
            self._log(f"  {form} in VALID_FORMS? NO")
            self._log(f"  Result: INVALID ✗")
            return False, f"{form} is not in the 24 valid syllogistic forms"


# Convenience function
def process_extraction(extraction: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
    """Process an extraction using the deterministic post-processor."""
    processor = DeterministicPostProcessor(verbose=verbose)
    return processor.process(extraction)
