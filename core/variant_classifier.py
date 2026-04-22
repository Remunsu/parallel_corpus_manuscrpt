from typing import Set, List
from core.models import AlignmentRow


MORPH_KEYS = {
    "case", "number", "gender", "person",
    "tense", "mood", "voice", "degree",
    "kind", "category"
}


def _flatten_morph(morph_dict) -> Set[str]:
    values = set()
    for key, items in morph_dict.items():
        if key in MORPH_KEYS:
            for item in items:
                values.add(f"{key}={item}")
    return values


def _same_morphology(t, s) -> bool:
    return _flatten_morph(t.morph) == _flatten_morph(s.morph)


def _close_abbreviation(t, s) -> bool:
    a = t.abbr_skeleton or ""
    b = s.abbr_skeleton or ""

    if not a or not b:
        return False

    if a == b:
        return True

    if a in b or b in a:
        return True

    if abs(len(a) - len(b)) <= 1:
        mismatches = 0
        for ch1, ch2 in zip(a, b):
            if ch1 != ch2:
                mismatches += 1
                if mismatches > 1:
                    return False
        return True

    return False


def _phonetic_form(token) -> str:
    s = token.norm_phon or token.norm_graph or token.surface or ""
    s = s.lower().strip()

    # очень грубые вторичные сближения только для классификации
    s = (
        s.replace("щ", "ш")
         .replace("ц", "с")
    )
    return s


def _levenshtein_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr.append(min(
                prev[j] + 1,
                curr[j - 1] + 1,
                prev[j - 1] + cost
            ))
        prev = curr
    return prev[-1]


def _is_short_function_word(token) -> bool:
    if token is None:
        return False

    cat_values = token.morph.get("category", [])
    category = cat_values[0] if cat_values else ""

    short_words = {
        "и", "же", "не", "в", "въ", "на", "к", "къ", "с", "съ",
        "по", "о", "от", "ѡт", "но", "нъ", "бо", "ли", "у", "же"
    }

    surface = (token.norm_graph or token.surface or "").lower()
    return category in {"conjunction", "preposition", "particle"} or surface in short_words


def _is_probably_phonetic(t, s) -> bool:
    if t is None or s is None:
        return False

    # графическое уже отсеяно раньше
    if t.norm_graph == s.norm_graph:
        return False

    # короткие служебные слова не считаем фонетическими
    if _is_short_function_word(t) or _is_short_function_word(s):
        return False

    a = _phonetic_form(t)
    b = _phonetic_form(s)

    if not a or not b:
        return False

    # слишком разная длина -> не phonetic
    if abs(len(a) - len(b)) > 1:
        return False

    # точное совпадение фонетической формы
    if a == b:
        return True

    # одна и та же лемма + маленькое расстояние
    if t.lemma and s.lemma and t.lemma == s.lemma:
        return _levenshtein_distance(a, b) <= 1

    # без совпадения леммы — только очень близкие формы средней длины
    if min(len(a), len(b)) >= 4:
        return _levenshtein_distance(a, b) == 1

    return False


def classify_row(row: AlignmentRow) -> AlignmentRow:
    t = row.target_token
    s = row.source_token

    if t is None or s is None:
        row.auto_variant_type = None
        row.confidence = 0.0
        return row

    if t.surface == s.surface:
        row.auto_variant_type = "match"
        row.confidence = 1.0
        return row

    if _close_abbreviation(t, s):
        row.auto_variant_type = "graphical"
        row.confidence = 0.95
        return row

    if t.norm_graph == s.norm_graph:
        row.auto_variant_type = "graphical"
        row.confidence = 0.9
        return row

    if _is_probably_phonetic(t, s):
        row.auto_variant_type = "phonetic"
        row.confidence = 0.78
        return row

    if t.lemma and s.lemma and t.lemma == s.lemma:
        if _same_morphology(t, s):
            row.auto_variant_type = "graphical"
            row.confidence = 0.8
            return row

        row.auto_variant_type = "morphological"
        row.confidence = 0.8
        return row

    row.auto_variant_type = "lexical"
    row.confidence = 0.6
    return row


def classify_alignment(rows: List[AlignmentRow]) -> List[AlignmentRow]:
    return [classify_row(row) for row in rows]
