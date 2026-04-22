import re
import unicodedata


COMBINING_RE = re.compile(r"[\u0300-\u036f]")
SUPERSCRIPT_SIGNS = {
    "҃", "҄", "҅", "҆", "꙯",
    "ⷠ", "ⷡ", "ⷢ", "ⷣ", "ⷤ", "ⷥ", "ⷦ", "ⷧ",
    "ⷨ", "ⷩ", "ⷪ", "ⷫ", "ⷬ", "ⷭ", "ⷮ", "ⷯ"
}


def strip_combining(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = COMBINING_RE.sub("", text)
    return unicodedata.normalize("NFC", text)


def clean_superscripts(text: str) -> str:
    s = strip_combining(text)
    for ch in SUPERSCRIPT_SIGNS:
        s = s.replace(ch, "")
    return s


def normalize_graph(text: str) -> str:
    s = text.lower().strip()
    s = clean_superscripts(s)

    # старые/вариантные буквы -> более обычная графика
    s = s.replace("ѡ", "о")
    s = s.replace("ѻ", "о")
    s = s.replace("ꙋ", "у").replace("ѹ", "у").replace("оу", "у")
    s = s.replace("і", "и").replace("ı", "и").replace("ѵ", "и")
    s = s.replace("ѣ", "е").replace("є", "е").replace("ѥ", "е")
    s = s.replace("ꙗ", "я").replace("ѧ", "я")
    s = s.replace("ѫ", "у").replace("ѭ", "ю")
    s = s.replace("ѳ", "ф")
    s = s.replace("ѕ", "з")
    s = s.replace("ѯ", "кс")
    s = s.replace("ѱ", "пс")

    s = s.replace("ъ", "").replace("ь", "")
    return s


def normalize_phon(text: str) -> str:
    s = normalize_graph(text)

    # сначала типичные славянские сближения сочетаний
    cluster_replacements = [
        ("жд", "ж"),
        ("шт", "щ"),
        ("сч", "щ"),
        ("зч", "щ"),
        ("жч", "щ"),
        ("чт", "ч"),
        ("стн", "сн"),
        ("здн", "зн"),
        ("тс", "ц"),
        ("дс", "ц"),
        ("тьс", "ц"),
        ("дьс", "ц"),
    ]
    for old, new in cluster_replacements:
        s = s.replace(old, new)

    # старые и колеблющиеся гласные — более грубое фонетическое сведение
    vowel_map = str.maketrans({
        "о": "а",
        "е": "и",
        "я": "а",
        "ю": "у",
        "ы": "и",
    })
    s = s.translate(vowel_map)

    # грубые согласные ряды для фонетического уровня
    consonant_map = str.maketrans({
        "г": "к",
        "х": "к",
        "з": "с",
        "д": "т",
        "б": "п",
        "ж": "ш",
    })
    s = s.translate(consonant_map)

    return s


def abbreviation_skeleton(text: str) -> str:
    s = text.lower().strip()
    s = clean_superscripts(s)

    s = s.replace("ѡ", "о").replace("ѻ", "о")
    s = s.replace("ꙋ", "у").replace("ѹ", "у").replace("оу", "у")
    s = s.replace("і", "и").replace("ı", "и").replace("ѵ", "и")
    s = s.replace("ѣ", "е").replace("є", "е").replace("ѥ", "е")
    s = s.replace("ꙗ", "я").replace("ѧ", "я")
    s = s.replace("ѫ", "у").replace("ѭ", "ю")
    s = s.replace("ѳ", "ф")
    s = s.replace("ѕ", "з")
    s = s.replace("ѯ", "кс")
    s = s.replace("ѱ", "пс")

    s = s.replace("ъ", "").replace("ь", "")
    return s
