"""
Data structures for syllogism representation.
"""

from dataclasses import dataclass, asdict
from typing import Literal, Optional, Dict, Any


@dataclass
class Proposition:
    """Represents a single proposition (premise or conclusion)"""
    type: Literal["A", "E", "I", "O"]  # A=All, E=No, I=Some, O=Some...not
    subject: str
    predicate: str
    raw_text: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SyllogismStructure:
    """Extracted structure of a syllogism"""
    premise1: Proposition
    premise2: Proposition
    conclusion: Proposition
    middle_term: str
    major_term: str  # predicate of conclusion
    minor_term: str  # subject of conclusion
    figure: Literal[1, 2, 3, 4]
    mood: str  # e.g., "AAA", "EIO"
    
    def get_form(self) -> str:
        """Return mood-figure string, e.g., 'AAA-1'"""
        return f"{self.mood}-{self.figure}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "premise1": self.premise1.to_dict(),
            "premise2": self.premise2.to_dict(),
            "conclusion": self.conclusion.to_dict(),
            "middle_term": self.middle_term,
            "major_term": self.major_term,
            "minor_term": self.minor_term,
            "figure": self.figure,
            "mood": self.mood,
            "form": self.get_form()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyllogismStructure":
        """Create SyllogismStructure from dictionary"""
        return cls(
            premise1=Proposition(**data["premise1"]),
            premise2=Proposition(**data["premise2"]),
            conclusion=Proposition(**data["conclusion"]),
            middle_term=data["middle_term"],
            major_term=data["major_term"],
            minor_term=data["minor_term"],
            figure=data["figure"],
            mood=data["mood"]
        )
