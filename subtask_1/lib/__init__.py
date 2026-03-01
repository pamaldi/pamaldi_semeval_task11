"""
Neuro-Symbolic Syllogism Validator

A two-stage approach:
1. LLM extracts syllogism structure (NLU task)
2. Python applies deterministic validity rules (no LLM reasoning)

This eliminates code generation errors and removes content effect from validity checking.
"""

from .syllogism_structures import Proposition, SyllogismStructure
from .validity_checker import SyllogismValidityChecker
from .syllogism_extractor import SyllogismExtractor
from .extraction_reflexion import ExtractionReflexion
from .neurosymbolic_pipeline import NeuroSymbolicPipeline
from .evaluation import NeuroSymbolicEvaluator

__all__ = [
    'Proposition',
    'SyllogismStructure',
    'SyllogismValidityChecker',
    'SyllogismExtractor',
    'ExtractionReflexion',
    'NeuroSymbolicPipeline',
    'NeuroSymbolicEvaluator'
]
