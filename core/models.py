from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Token:
    token_id: str
    xml_id: str
    surface: str
    lemma: str
    norm_graph: str
    norm_phon: str
    abbr_skeleton: str
    morph: Dict[str, List[str]]
    sheet: Optional[str]
    page: Optional[str]
    position: int
    line_break_before: bool = False


@dataclass
class Manuscript:
    manuscript_id: str
    name: str
    file_path: str
    tokens: List[Token] = field(default_factory=list)


@dataclass
class AlignmentRow:
    row_no: int
    target_token: Optional[Token]
    source_token: Optional[Token]
    auto_variant_type: Optional[str] = None
    manual_variant_type: Optional[str] = None
    confidence: float = 0.0
    status: str = "auto"

    @property
    def final_variant_type(self) -> Optional[str]:
        return self.manual_variant_type if self.manual_variant_type is not None else self.auto_variant_type