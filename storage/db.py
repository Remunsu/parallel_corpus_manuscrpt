import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.models import AlignmentRow, Manuscript, Token


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def init_schema(self, schema_path: str):
        sql = Path(schema_path).read_text(encoding="utf-8")
        self.conn.executescript(sql)
        self.conn.commit()

    # ----------------------------
    # Manuscripts / tokens
    # ----------------------------

    def save_manuscript(self, manuscript: Manuscript):
        self.conn.execute(
            "INSERT OR REPLACE INTO manuscripts(manuscript_id, name, file_path) VALUES (?, ?, ?)",
            (manuscript.manuscript_id, manuscript.name, manuscript.file_path)
        )

        for t in manuscript.tokens:
            self.conn.execute("""
                INSERT OR REPLACE INTO tokens(
                    token_id, manuscript_id, xml_id, surface, lemma,
                    norm_graph, norm_phon, abbr_skeleton, morph_json,
                    sheet, page, position, line_break_before
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                t.token_id,
                manuscript.manuscript_id,
                t.xml_id,
                t.surface,
                t.lemma,
                t.norm_graph,
                t.norm_phon,
                t.abbr_skeleton,
                json.dumps(t.morph, ensure_ascii=False),
                t.sheet,
                t.page,
                t.position,
                1 if t.line_break_before else 0
            ))
        self.conn.commit()

    def load_manuscript(self, manuscript_id: str) -> Optional[Manuscript]:
        row = self.conn.execute(
            "SELECT manuscript_id, name, file_path FROM manuscripts WHERE manuscript_id = ?",
            (manuscript_id,)
        ).fetchone()

        if row is None:
            return None

        token_rows = self.conn.execute("""
            SELECT token_id, xml_id, surface, lemma, norm_graph, norm_phon,
                   abbr_skeleton, morph_json, sheet, page, position, line_break_before
            FROM tokens
            WHERE manuscript_id = ?
            ORDER BY position
        """, (manuscript_id,)).fetchall()

        tokens = []
        for tr in token_rows:
            tokens.append(Token(
                token_id=tr["token_id"],
                xml_id=tr["xml_id"] or "",
                surface=tr["surface"],
                lemma=tr["lemma"] or "",
                norm_graph=tr["norm_graph"] or "",
                norm_phon=tr["norm_phon"] or "",
                abbr_skeleton=tr["abbr_skeleton"] or "",
                morph=json.loads(tr["morph_json"] or "{}"),
                sheet=tr["sheet"],
                page=tr["page"],
                position=tr["position"],
                line_break_before=bool(tr["line_break_before"]),
            ))

        return Manuscript(
            manuscript_id=row["manuscript_id"],
            name=row["name"],
            file_path=row["file_path"],
            tokens=tokens
        )

    def load_all_manuscripts(self) -> Dict[str, Manuscript]:
        rows = self.conn.execute("""
            SELECT manuscript_id FROM manuscripts ORDER BY manuscript_id
        """).fetchall()

        result = {}
        for row in rows:
            ms = self.load_manuscript(row["manuscript_id"])
            if ms is not None:
                result[ms.manuscript_id] = ms
        return result

    def token_map(self) -> Dict[str, Token]:
        rows = self.conn.execute("""
            SELECT manuscript_id, token_id, xml_id, surface, lemma, norm_graph, norm_phon,
                   abbr_skeleton, morph_json, sheet, page, position, line_break_before
            FROM tokens
        """).fetchall()

        result = {}
        for tr in rows:
            result[tr["token_id"]] = Token(
                token_id=tr["token_id"],
                xml_id=tr["xml_id"] or "",
                surface=tr["surface"],
                lemma=tr["lemma"] or "",
                norm_graph=tr["norm_graph"] or "",
                norm_phon=tr["norm_phon"] or "",
                abbr_skeleton=tr["abbr_skeleton"] or "",
                morph=json.loads(tr["morph_json"] or "{}"),
                sheet=tr["sheet"],
                page=tr["page"],
                position=tr["position"],
                line_break_before=bool(tr["line_break_before"]),
            )
        return result

    # ----------------------------
    # Projects
    # ----------------------------

    def create_project(
        self,
        name: str,
        main_manuscript_id: str,
        selected_sheets: List[str],
        manuscript_order: List[str],
    ) -> int:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO projects(
                name, main_manuscript_id, selected_sheets_json, manuscript_order_json,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            name,
            main_manuscript_id,
            json.dumps(selected_sheets, ensure_ascii=False),
            json.dumps(manuscript_order, ensure_ascii=False),
        ))
        project_id = cur.lastrowid

        for idx, manuscript_id in enumerate(manuscript_order):
            cur.execute("""
                INSERT INTO project_manuscripts(project_id, manuscript_id, display_order)
                VALUES (?, ?, ?)
            """, (project_id, manuscript_id, idx))

        self.conn.commit()
        return project_id

    def update_project(
        self,
        project_id: int,
        name: str,
        main_manuscript_id: str,
        selected_sheets: List[str],
        manuscript_order: List[str],
    ):
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE projects
            SET name = ?, main_manuscript_id = ?, selected_sheets_json = ?,
                manuscript_order_json = ?, updated_at = CURRENT_TIMESTAMP
            WHERE project_id = ?
        """, (
            name,
            main_manuscript_id,
            json.dumps(selected_sheets, ensure_ascii=False),
            json.dumps(manuscript_order, ensure_ascii=False),
            project_id
        ))

        cur.execute("DELETE FROM project_manuscripts WHERE project_id = ?", (project_id,))
        for idx, manuscript_id in enumerate(manuscript_order):
            cur.execute("""
                INSERT INTO project_manuscripts(project_id, manuscript_id, display_order)
                VALUES (?, ?, ?)
            """, (project_id, manuscript_id, idx))

        self.conn.commit()

    def list_projects(self):
        return self.conn.execute("""
            SELECT project_id, name, main_manuscript_id, created_at, updated_at
            FROM projects
            ORDER BY updated_at DESC, project_id DESC
        """).fetchall()

    def load_project(self, project_id: int):
        row = self.conn.execute("""
            SELECT project_id, name, main_manuscript_id, selected_sheets_json, manuscript_order_json
            FROM projects
            WHERE project_id = ?
        """, (project_id,)).fetchone()

        if row is None:
            return None

        manuscript_rows = self.conn.execute("""
            SELECT manuscript_id
            FROM project_manuscripts
            WHERE project_id = ?
            ORDER BY display_order
        """, (project_id,)).fetchall()

        manuscript_order = [r["manuscript_id"] for r in manuscript_rows]
        if not manuscript_order:
            manuscript_order = json.loads(row["manuscript_order_json"] or "[]")

        return {
            "project_id": row["project_id"],
            "name": row["name"],
            "main_manuscript_id": row["main_manuscript_id"],
            "selected_sheets": json.loads(row["selected_sheets_json"] or "[]"),
            "manuscript_order": manuscript_order,
        }

    # ----------------------------
    # Alignments
    # ----------------------------

    def delete_project_alignments(self, project_id: int):
        alignment_rows = self.conn.execute("""
            SELECT alignment_id FROM alignments WHERE project_id = ?
        """, (project_id,)).fetchall()

        for row in alignment_rows:
            self.conn.execute("DELETE FROM alignment_rows WHERE alignment_id = ?", (row["alignment_id"],))

        self.conn.execute("DELETE FROM alignments WHERE project_id = ?", (project_id,))
        self.conn.commit()

    def save_alignment(self, project_id: Optional[int], target_manuscript_id: str, source_manuscript_id: str, rows):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO alignments(project_id, target_manuscript_id, source_manuscript_id, created_at)
            VALUES (?, ?, ?, datetime('now'))
        """, (project_id, target_manuscript_id, source_manuscript_id))
        alignment_id = cur.lastrowid

        for row in rows:
            cur.execute("""
                INSERT INTO alignment_rows(
                    alignment_id, row_no, target_token_id, source_token_id,
                    auto_variant_type, manual_variant_type, confidence, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alignment_id,
                row.row_no,
                row.target_token.token_id if row.target_token else None,
                row.source_token.token_id if row.source_token else None,
                row.auto_variant_type,
                row.manual_variant_type,
                row.confidence,
                row.status
            ))

        self.conn.commit()
        return alignment_id

    def update_alignment_row(self, alignment_id: int, row_no: int, manual_variant_type, status: str):
        self.conn.execute("""
            UPDATE alignment_rows
            SET manual_variant_type = ?, status = ?
            WHERE alignment_id = ? AND row_no = ?
        """, (manual_variant_type, status, alignment_id, row_no))
        self.conn.commit()

    def load_project_pairwise_rows(self, project_id: int) -> Dict[str, List[AlignmentRow]]:
        token_map = self.token_map()

        alignments = self.conn.execute("""
            SELECT alignment_id, source_manuscript_id
            FROM alignments
            WHERE project_id = ?
            ORDER BY alignment_id
        """, (project_id,)).fetchall()

        result: Dict[str, List[AlignmentRow]] = {}

        for a in alignments:
            row_rows = self.conn.execute("""
                SELECT row_no, target_token_id, source_token_id,
                       auto_variant_type, manual_variant_type, confidence, status
                FROM alignment_rows
                WHERE alignment_id = ?
                ORDER BY row_no
            """, (a["alignment_id"],)).fetchall()

            pair_rows = []
            for rr in row_rows:
                pair_rows.append(AlignmentRow(
                    row_no=rr["row_no"],
                    target_token=token_map.get(rr["target_token_id"]),
                    source_token=token_map.get(rr["source_token_id"]),
                    auto_variant_type=rr["auto_variant_type"],
                    manual_variant_type=rr["manual_variant_type"],
                    confidence=rr["confidence"] or 0.0,
                    status=rr["status"] or "auto",
                ))
            result[a["source_manuscript_id"]] = pair_rows

        return result

    def load_project_alignment_ids(self, project_id: int) -> Dict[str, int]:
        rows = self.conn.execute("""
            SELECT alignment_id, source_manuscript_id
            FROM alignments
            WHERE project_id = ?
        """, (project_id,)).fetchall()

        return {r["source_manuscript_id"]: r["alignment_id"] for r in rows}