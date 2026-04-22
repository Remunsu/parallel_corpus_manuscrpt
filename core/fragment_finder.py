from typing import List, Tuple

from core.models import Token


# какие категории считаем "содержательными" для якорей
CONTENT_CATEGORIES = {
    "noun",
    "verb",
    "adjective",
    "numeral",
    "participle",
}


def _token_category(token: Token) -> str:
    values = token.morph.get("category", [])
    return values[0] if values else ""


def _is_content_token(token: Token) -> bool:
    cat = _token_category(token)
    return cat in CONTENT_CATEGORIES


def _token_match_score(a: Token, b: Token) -> int:
    if a.surface == b.surface:
        return 5
    if a.abbr_skeleton and b.abbr_skeleton and a.abbr_skeleton == b.abbr_skeleton:
        return 5
    if a.lemma and b.lemma and a.lemma == b.lemma:
        return 4
    if a.norm_graph == b.norm_graph:
        return 3
    if a.norm_phon == b.norm_phon:
        return 2
    return 0


def _build_anchor(tokens: List[Token], from_start: bool, size: int = 10) -> List[Token]:
    seq = tokens if from_start else list(reversed(tokens))

    content = [t for t in seq if _is_content_token(t)]
    if len(content) >= size:
        anchor = content[:size]
    else:
        anchor = seq[:size]

    return anchor if from_start else list(reversed(anchor))


def _score_anchor_at(source_tokens: List[Token], pos: int, anchor_tokens: List[Token]) -> int:
    """
    Ищет только НАЧАЛО фрагмента.
    """
    if not anchor_tokens:
        return 0

    score = 0
    max_window = min(len(source_tokens), pos + len(anchor_tokens) + 12)
    src_slice = source_tokens[pos:max_window]

    src_i = 0
    for a in anchor_tokens:
        best_local = 0
        best_j = -1

        lookahead_end = min(len(src_slice), src_i + 4)
        for j in range(src_i, lookahead_end):
            s = src_slice[j]
            local = _token_match_score(a, s)
            if local > best_local:
                best_local = local
                best_j = j

        if best_j >= 0 and best_local > 0:
            score += best_local
            src_i = best_j + 1
        else:
            score -= 2

    return score


def find_best_fragment(target_tokens: List[Token], source_tokens: List[Token]) -> Tuple[int, int, float]:
    """
    Упрощённый и более стабильный вариант:
    - ищем ТОЛЬКО начало фрагмента по первым содержательным словам
    - конец задаём как фиксированное окно длиной target + запас

    Это надёжнее для притчи о блудном сыне, чем пытаться автоматически
    угадать конец по повторяющимся словам вроде "достоинъ".
    """
    if not target_tokens or not source_tokens:
        return 0, 0, 0.0

    # для старта берём только начало эталона
    start_anchor = _build_anchor(target_tokens, from_start=True, size=10)

    best_pos = 0
    best_score = -10**9

    for pos in range(len(source_tokens)):
        score = _score_anchor_at(source_tokens, pos, start_anchor)
        if score > best_score:
            best_score = score
            best_pos = pos

    # фиксированная длина окна после найденного старта
    extra_tail = max(20, len(target_tokens) // 6)
    end_pos = min(len(source_tokens), best_pos + len(target_tokens) + extra_tail)

    if end_pos <= best_pos:
        end_pos = min(len(source_tokens), best_pos + len(target_tokens))

    return best_pos, end_pos, float(best_score)
