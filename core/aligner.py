from typing import List
from core.models import AlignmentRow, Token


MATCH_SCORE = 2
LEMMA_SCORE = 3
PHON_SCORE = 1
GAP_PENALTY = -2
MISMATCH_PENALTY = -1


def token_similarity(a: Token, b: Token) -> int:
    if a.surface == b.surface:
        return 4
    if a.abbr_skeleton and b.abbr_skeleton and a.abbr_skeleton == b.abbr_skeleton:
        return 4
    if a.lemma and b.lemma and a.lemma == b.lemma:
        return 3
    if a.norm_graph == b.norm_graph:
        return 2
    if a.norm_phon == b.norm_phon:
        return 1
    return -1

def align_tokens(target_tokens: List[Token], source_tokens: List[Token]) -> List[AlignmentRow]:
    n = len(target_tokens)
    m = len(source_tokens)

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    bt = [[None] * (m + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        dp[i][0] = dp[i - 1][0] + GAP_PENALTY
        bt[i][0] = "up"

    for j in range(1, m + 1):
        dp[0][j] = dp[0][j - 1] + GAP_PENALTY
        bt[0][j] = "left"

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            diag = dp[i - 1][j - 1] + token_similarity(target_tokens[i - 1], source_tokens[j - 1])
            up = dp[i - 1][j] + GAP_PENALTY
            left = dp[i][j - 1] + GAP_PENALTY

            best = max(diag, up, left)
            dp[i][j] = best
            if best == diag:
                bt[i][j] = "diag"
            elif best == up:
                bt[i][j] = "up"
            else:
                bt[i][j] = "left"

    rows: List[AlignmentRow] = []
    i, j = n, m
    row_no = 0

    while i > 0 or j > 0:
        move = bt[i][j]

        if move == "diag":
            t = target_tokens[i - 1]
            s = source_tokens[j - 1]
            rows.append(AlignmentRow(row_no=row_no, target_token=t, source_token=s))
            i -= 1
            j -= 1

        elif move == "up":
            t = target_tokens[i - 1]
            rows.append(AlignmentRow(row_no=row_no, target_token=t, source_token=None))
            i -= 1

        else:
            s = source_tokens[j - 1]
            rows.append(AlignmentRow(row_no=row_no, target_token=None, source_token=s))
            j -= 1

        row_no += 1

    rows.reverse()
    for idx, row in enumerate(rows):
        row.row_no = idx
    return rows