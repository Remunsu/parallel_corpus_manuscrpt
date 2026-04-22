CREATE TABLE IF NOT EXISTS manuscripts (
    manuscript_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tokens (
    token_id TEXT PRIMARY KEY,
    manuscript_id TEXT NOT NULL,
    xml_id TEXT,
    surface TEXT NOT NULL,
    lemma TEXT,
    norm_graph TEXT,
    norm_phon TEXT,
    abbr_skeleton TEXT,
    morph_json TEXT,
    sheet TEXT,
    page TEXT,
    position INTEGER NOT NULL,
    line_break_before INTEGER DEFAULT 0,
    FOREIGN KEY(manuscript_id) REFERENCES manuscripts(manuscript_id)
);

CREATE TABLE IF NOT EXISTS projects (
    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    main_manuscript_id TEXT NOT NULL,
    selected_sheets_json TEXT,
    manuscript_order_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(main_manuscript_id) REFERENCES manuscripts(manuscript_id)
);

CREATE TABLE IF NOT EXISTS project_manuscripts (
    project_id INTEGER NOT NULL,
    manuscript_id TEXT NOT NULL,
    display_order INTEGER NOT NULL,
    PRIMARY KEY(project_id, manuscript_id),
    FOREIGN KEY(project_id) REFERENCES projects(project_id),
    FOREIGN KEY(manuscript_id) REFERENCES manuscripts(manuscript_id)
);

CREATE TABLE IF NOT EXISTS alignments (
    alignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    target_manuscript_id TEXT NOT NULL,
    source_manuscript_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS alignment_rows (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alignment_id INTEGER NOT NULL,
    row_no INTEGER NOT NULL,
    target_token_id TEXT,
    source_token_id TEXT,
    auto_variant_type TEXT,
    manual_variant_type TEXT,
    confidence REAL,
    status TEXT,
    FOREIGN KEY(alignment_id) REFERENCES alignments(alignment_id)
);

CREATE INDEX IF NOT EXISTS idx_tokens_manuscript_position
    ON tokens(manuscript_id, position);

CREATE INDEX IF NOT EXISTS idx_alignment_rows_alignment_rowno
    ON alignment_rows(alignment_id, row_no);

CREATE INDEX IF NOT EXISTS idx_alignments_project
    ON alignments(project_id);