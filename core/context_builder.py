from typing import Dict, List, Optional
from core.models import Manuscript, Token


def build_token_index(manuscript: Manuscript) -> Dict[str, Token]:
    return {token.token_id: token for token in manuscript.tokens}


def get_token_by_xml_id(manuscript: Manuscript, xml_id: str) -> Optional[Token]:
    for token in manuscript.tokens:
        if token.xml_id == xml_id:
            return token
    return None


def get_context_window(tokens: List[Token], center_position: int, window: int = 10) -> List[Token]:
    start = max(0, center_position - window)
    end = min(len(tokens), center_position + window + 1)
    return tokens[start:end]


def format_context(tokens: List[Token], center_position: int) -> str:
    parts = []
    for token in tokens:
        word = token.surface
        if token.position == center_position:
            word = f"[{word}]"
        parts.append(word)
    return " ".join(parts)


def token_address(token: Token) -> str:
    return f"Лист: {token.sheet or '—'} | Страница: {token.page or '—'} | xml:id: {token.xml_id or '—'}"