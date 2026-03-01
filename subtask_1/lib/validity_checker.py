"""
Deterministic validity checker for categorical syllogisms.

Uses ARISTOTELIAN interpretation: 24 valid forms (with existential import).
This matches SemEval 2026 Task 11 guidelines.

NO LLM INVOLVED - Pure rule application.
"""

from typing import Dict, Any, Optional
from syllogism_structures import SyllogismStructure


class SyllogismValidityChecker:
    """
    Deterministic validity checker for categorical syllogisms.
    
    Uses ARISTOTELIAN interpretation: all 24 traditionally valid forms,
    including those requiring existential import.
    """
    
    # ALL 24 traditionally valid syllogistic forms
    VALID_FORMS = {
        # Figure 1: M-P, S-M
        "AAA-1",  # Barbara
        "EAE-1",  # Celarent
        "AII-1",  # Darii
        "EIO-1",  # Ferio
        "AAI-1",  # Barbari (weakened)
        "EAO-1",  # Celaront (weakened)
        
        # Figure 2: P-M, S-M
        "EAE-2",  # Cesare
        "AEE-2",  # Camestres
        "EIO-2",  # Festino
        "AOO-2",  # Baroco
        "EAO-2",  # Cesaro (weakened)
        "AEO-2",  # Camestrop (weakened)
        
        # Figure 3: M-P, M-S
        "IAI-3",  # Disamis
        "AII-3",  # Datisi
        "OAO-3",  # Bocardo
        "EIO-3",  # Ferison
        "AAI-3",  # Darapti (existential import)
        "EAO-3",  # Felapton (existential import)
        
        # Figure 4: P-M, M-S
        "AEE-4",  # Camenes
        "IAI-4",  # Dimaris
        "EIO-4",  # Fresison
        "AEO-4",  # Camenop (weakened)
        "EAO-4",  # Fesapo (existential import)
        "AAI-4",  # Bramantip (existential import)
    }
    
    # Traditional Latin names
    FORM_NAMES = {
        "AAA-1": "Barbara", "EAE-1": "Celarent", "AII-1": "Darii", "EIO-1": "Ferio",
        "AAI-1": "Barbari", "EAO-1": "Celaront",
        "EAE-2": "Cesare", "AEE-2": "Camestres", "EIO-2": "Festino", "AOO-2": "Baroco",
        "EAO-2": "Cesaro", "AEO-2": "Camestrop",
        "IAI-3": "Disamis", "AII-3": "Datisi", "OAO-3": "Bocardo", "EIO-3": "Ferison",
        "AAI-3": "Darapti", "EAO-3": "Felapton",
        "AEE-4": "Camenes", "IAI-4": "Dimaris", "EIO-4": "Fresison",
        "AEO-4": "Camenop", "EAO-4": "Fesapo", "AAI-4": "Bramantip",
    }
    
    # Forms requiring existential import (for diagnostics only - all are VALID)
    EXISTENTIAL_IMPORT_FORMS = {
        "AAI-1", "EAO-1",  # Figure 1 weakened
        "EAO-2", "AEO-2",  # Figure 2 weakened
        "AAI-3", "EAO-3",  # Figure 3
        "AEO-4", "EAO-4", "AAI-4",  # Figure 4
    }
    
    def check_validity(self, structure: SyllogismStructure) -> Dict[str, Any]:
        """Check if the syllogism is valid based on its mood and figure."""
        form = structure.get_form()
        
        result = {
            "form": form,
            "mood": structure.mood,
            "figure": structure.figure,
            "requires_existential_import": form in self.EXISTENTIAL_IMPORT_FORMS,
        }
        
        if form in self.VALID_FORMS:
            result["valid"] = True
            result["form_name"] = self.FORM_NAMES.get(form, "Unknown")
            result["reason"] = f"Valid syllogistic form: {result['form_name']}"
            if form in self.EXISTENTIAL_IMPORT_FORMS:
                result["reason"] += " (requires existential import)"
            return result
        
        result["valid"] = False
        result["form_name"] = None
        result["reason"] = self._diagnose_invalidity(structure)
        return result
    
    def _diagnose_invalidity(self, structure: SyllogismStructure) -> str:
        """Provide explanation for why the syllogism is invalid."""
        reasons = []
        
        p1_type = structure.premise1.type
        p2_type = structure.premise2.type
        c_type = structure.conclusion.type
        
        # Check for two negative premises
        neg_count = sum(1 for p in [p1_type, p2_type] if p in ["E", "O"])
        if neg_count >= 2:
            reasons.append("Two negative premises (Fallacy of Exclusive Premises)")
        
        # Check for negative premise with affirmative conclusion
        has_neg_premise = any(p in ["E", "O"] for p in [p1_type, p2_type])
        has_aff_conclusion = c_type in ["A", "I"]
        if has_neg_premise and has_aff_conclusion:
            reasons.append("Negative premise with affirmative conclusion")
        
        # Check for two affirmative premises with negative conclusion
        all_aff_premises = all(p in ["A", "I"] for p in [p1_type, p2_type])
        has_neg_conclusion = c_type in ["E", "O"]
        if all_aff_premises and has_neg_conclusion:
            reasons.append("Affirmative premises cannot yield negative conclusion")
        
        # Check for two particular premises
        particular_count = sum(1 for p in [p1_type, p2_type] if p in ["I", "O"])
        if particular_count >= 2:
            reasons.append("Two particular premises (Fallacy of Two Particulars)")
        
        # Check undistributed middle
        if not self._is_middle_distributed(structure):
            reasons.append("Undistributed middle term")
        
        # Check illicit major/minor
        illicit = self._check_illicit_process(structure)
        if illicit:
            reasons.append(illicit)
        
        if not reasons:
            reasons.append(f"Form {structure.get_form()} is not valid")
        
        return "; ".join(reasons)
    
    def _is_middle_distributed(self, structure: SyllogismStructure) -> bool:
        """Check if middle term is distributed in at least one premise."""
        middle = structure.middle_term
        p1_dist = self._get_distributed_terms(structure.premise1.type,
                                               structure.premise1.subject,
                                               structure.premise1.predicate)
        p2_dist = self._get_distributed_terms(structure.premise2.type,
                                               structure.premise2.subject,
                                               structure.premise2.predicate)
        return middle in p1_dist or middle in p2_dist
    
    def _get_distributed_terms(self, prop_type: str, subject: str, predicate: str) -> set:
        """Return set of distributed terms for a proposition type."""
        if prop_type == "A":
            return {subject}
        elif prop_type == "E":
            return {subject, predicate}
        elif prop_type == "I":
            return set()
        elif prop_type == "O":
            return {predicate}
        return set()
    
    def _check_illicit_process(self, structure: SyllogismStructure) -> Optional[str]:
        """Check for illicit major or minor term."""
        c_dist = self._get_distributed_terms(structure.conclusion.type,
                                              structure.conclusion.subject,
                                              structure.conclusion.predicate)
        p1_dist = self._get_distributed_terms(structure.premise1.type,
                                               structure.premise1.subject,
                                               structure.premise1.predicate)
        p2_dist = self._get_distributed_terms(structure.premise2.type,
                                               structure.premise2.subject,
                                               structure.premise2.predicate)
        premise_dist = p1_dist | p2_dist
        
        if structure.major_term in c_dist and structure.major_term not in premise_dist:
            return f"Illicit major: '{structure.major_term}'"
        if structure.minor_term in c_dist and structure.minor_term not in premise_dist:
            return f"Illicit minor: '{structure.minor_term}'"
        return None


# Test
if __name__ == "__main__":
    from syllogism_structures import Proposition, SyllogismStructure
    
    checker = SyllogismValidityChecker()
    
    print("=" * 60)
    print("VALIDITY CHECKER TEST - 24 FORMS (Aristotelian)")
    print("=" * 60)
    print(f"Total valid forms: {len(checker.VALID_FORMS)}")
    print(f"Existential import forms: {len(checker.EXISTENTIAL_IMPORT_FORMS)}")
    
    # Test AAI-3 (Darapti) - should now be VALID
    print("\nTest: AAI-3 (Darapti) - should be VALID")
    darapti = SyllogismStructure(
        premise1=Proposition("A", "idea", "tree", "Every idea is a tree"),
        premise2=Proposition("A", "idea", "animal", "Every idea is an animal"),
        conclusion=Proposition("I", "animal", "tree", "Some animals are trees"),
        middle_term="idea",
        major_term="tree",
        minor_term="animal",
        figure=3,
        mood="AAI"
    )
    result = checker.check_validity(darapti)
    print(f"  Result: {result['valid']} - {result['reason']}")
    assert result['valid'] == True, "AAI-3 should be VALID!"
    
    # Test EAO-1 (Celaront) - should be VALID
    print("\nTest: EAO-1 (Celaront) - should be VALID")
    celaront = SyllogismStructure(
        premise1=Proposition("E", "circle", "round shape", "No circles are round shapes"),
        premise2=Proposition("A", "ring", "circle", "All rings are circles"),
        conclusion=Proposition("O", "ring", "round shape", "Some rings are not round shapes"),
        middle_term="circle",
        major_term="round shape",
        minor_term="ring",
        figure=1,
        mood="EAO"
    )
    result = checker.check_validity(celaront)
    print(f"  Result: {result['valid']} - {result['reason']}")
    assert result['valid'] == True, "EAO-1 should be VALID!"
    
    # Test AEO-2 (Camestrop) - should be VALID
    print("\nTest: AEO-2 (Camestrop) - should be VALID")
    camestrop = SyllogismStructure(
        premise1=Proposition("A", "triangle", "polygon", "All triangles are polygons"),
        premise2=Proposition("E", "line", "polygon", "No lines are polygons"),
        conclusion=Proposition("O", "line", "triangle", "Some lines are not triangles"),
        middle_term="polygon",
        major_term="triangle",
        minor_term="line",
        figure=2,
        mood="AEO"
    )
    result = checker.check_validity(camestrop)
    print(f"  Result: {result['valid']} - {result['reason']}")
    assert result['valid'] == True, "AEO-2 should be VALID!"
    
    # Test invalid form (EEE-1) - should still be INVALID
    print("\nTest: EEE-1 - should be INVALID")
    invalid = SyllogismStructure(
        premise1=Proposition("E", "tree", "green", "No trees are green"),
        premise2=Proposition("E", "car", "tree", "No cars are trees"),
        conclusion=Proposition("E", "car", "green", "No cars are green"),
        middle_term="tree",
        major_term="green",
        minor_term="car",
        figure=1,
        mood="EEE"
    )
    result = checker.check_validity(invalid)
    print(f"  Result: {result['valid']} - {result['reason']}")
    assert result['valid'] == False, "EEE-1 should be INVALID!"
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
