from typing import List, Optional
from core.models import Token


def get_available_sheets(tokens: List[Token]) -> List[str]:
    sheets = []
    seen = set()

    for token in tokens:
        if token.sheet and token.sheet not in seen:
            sheets.append(token.sheet)
            seen.add(token.sheet)

    return sheets


def filter_tokens_by_sheets(tokens: List[Token], selected_sheets: List[str]) -> List[Token]:
    if not selected_sheets:
        return tokens
    selected = set(selected_sheets)
    return [t for t in tokens if t.sheet in selected]