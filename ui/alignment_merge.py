from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from core.models import Token, AlignmentRow


@dataclass
class CombinedRow:
    key: Tuple
    main_token: Optional[Token] = None
    tokens_by_ms: Dict[str, Optional[Token]] = field(default_factory=dict)
    variants_by_ms: Dict[str, Optional[str]] = field(default_factory=dict)
    row_refs_by_ms: Dict[str, AlignmentRow] = field(default_factory=dict)


def merge_pairwise_alignments(main_manuscript_id: str, pairwise_results: Dict[str, List[AlignmentRow]]) -> List[CombinedRow]:
    rows_map: Dict[Tuple, CombinedRow] = {}
    order_keys: List[Tuple] = []

    def ensure_row(key: Tuple) -> CombinedRow:
        if key not in rows_map:
            rows_map[key] = CombinedRow(key=key)
            order_keys.append(key)
        return rows_map[key]

    for ms_id, rows in pairwise_results.items():
        prev_main_pos = -1
        extra_counter = 0

        for row in rows:
            t = row.target_token
            s = row.source_token
            variant = row.final_variant_type

            if t is not None:
                key = ("main", t.position)
                cr = ensure_row(key)
                cr.main_token = t
                cr.tokens_by_ms[main_manuscript_id] = t
                cr.tokens_by_ms[ms_id] = s
                cr.variants_by_ms[ms_id] = variant
                cr.row_refs_by_ms[ms_id] = row
                prev_main_pos = t.position
                extra_counter = 0
            else:
                extra_counter += 1
                key = ("ins", prev_main_pos, ms_id, extra_counter)
                cr = ensure_row(key)
                cr.tokens_by_ms[main_manuscript_id] = None
                cr.tokens_by_ms[ms_id] = s
                cr.variants_by_ms[ms_id] = None
                cr.row_refs_by_ms[ms_id] = row

    def sort_key(key: Tuple):
        if key[0] == "main":
            return (key[1], 0, "", 0)
        return (key[1], 1, key[2], key[3])

    ordered = [rows_map[k] for k in sorted(order_keys, key=sort_key)]
    return ordered