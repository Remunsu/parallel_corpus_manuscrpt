from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt


EDITABLE_VARIANTS = [
    "",
    "match",
    "graphical",
    "phonetic",
    "morphological",
    "lexical",
]

GAP_FILTER = "__gap__"

ALL_VARIANTS = [
    "match",
    "graphical",
    "phonetic",
    "morphological",
    "lexical",
    GAP_FILTER,
]


class AlignmentTableModel(QAbstractTableModel):
    def __init__(self, combined_rows=None, manuscript_order=None, manuscript_titles=None, on_variant_edited=None):
        super().__init__()
        self.all_rows = combined_rows or []
        self.visible_rows = list(self.all_rows)
        self.manuscript_order = manuscript_order or []
        self.manuscript_titles = manuscript_titles or {}
        self.enabled_variant_filters = set(ALL_VARIANTS)
        self.on_variant_edited = on_variant_edited

        self.column_map = []
        if self.manuscript_order:
            main_id = self.manuscript_order[0]
            self.column_map.append(("word", main_id))
            for ms_id in self.manuscript_order[1:]:
                self.column_map.append(("word", ms_id))
                self.column_map.append(("type", ms_id))

    def rowCount(self, parent=QModelIndex()):
        return len(self.visible_rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.column_map)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None

        if orientation == Qt.Horizontal:
            kind, ms_id = self.column_map[section]
            title = self.manuscript_titles.get(ms_id, ms_id)

            if section == 0:
                return title

            if kind == "word":
                return f"{title}\nслово"
            return f"{title}\nтип"

        return section + 1

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        kind, ms_id = self.column_map[index.column()]

        if kind == "type" and index.column() != 0:
            row = self.visible_rows[index.row()]
            if row.tokens_by_ms.get(ms_id) is not None:
                return base | Qt.ItemIsEditable

        return base

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row = self.visible_rows[index.row()]
        kind, ms_id = self.column_map[index.column()]
        token = row.tokens_by_ms.get(ms_id)

        if role in (Qt.DisplayRole, Qt.EditRole):
            if kind == "word":
                return token.surface if token else "—"
            value = row.variants_by_ms.get(ms_id)
            return value if value else "—"

        if role == Qt.ToolTipRole:
            if token is None:
                return None

            lines = [
                token.surface,
                f"Лист: {token.sheet or '—'}",
                f"Страница: {token.page or '—'}",
                f"xml:id: {token.xml_id or '—'}",
            ]
            
            if token.lemma:
                lines.append(f"lemma: {token.lemma}")

            if token.morph:
                lines.append("") 
                lines.append("Морфология:")
                for key, values in token.morph.items():
                    for v in values:
                        lines.append(f"{key}: {v}")
                        
            if kind == "type":
                lines.append(f"Тип: {row.variants_by_ms.get(ms_id) or '—'}")
            return "\n".join(lines)

        if role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter

        return None

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False

        kind, ms_id = self.column_map[index.column()]
        if kind != "type":
            return False

        row = self.visible_rows[index.row()]
        if row.tokens_by_ms.get(ms_id) is None:
            return False

        value = (value or "").strip()
        if value == "—":
            value = ""

        if value and value not in EDITABLE_VARIANTS:
            return False

        new_value = value or None
        row.variants_by_ms[ms_id] = new_value

        pair_row = row.row_refs_by_ms.get(ms_id)
        if pair_row is not None:
            pair_row.manual_variant_type = new_value
            pair_row.status = "edited" if new_value is not None else "confirmed"

            if self.on_variant_edited is not None:
                self.on_variant_edited(ms_id, pair_row)

        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
        return True

    def get_combined_row(self, row_index: int):
        if 0 <= row_index < len(self.visible_rows):
            return self.visible_rows[row_index]
        return None

    def get_column_info(self, col_index: int):
        if 0 <= col_index < len(self.column_map):
            return self.column_map[col_index]
        return None

    def set_variant_filters(self, enabled_filters):
        self.beginResetModel()
        self.enabled_variant_filters = set(enabled_filters)

        filtered = []
        for row in self.all_rows:
            if self._row_matches_filters(row):
                filtered.append(row)

        self.visible_rows = filtered
        self.endResetModel()

    def _row_matches_filters(self, row):
        variants = []
        has_gap = False

        for ms_id in self.manuscript_order[1:]:
            value = row.variants_by_ms.get(ms_id)
            token = row.tokens_by_ms.get(ms_id)
            if value:
                variants.append(value)
            elif token is None:
                has_gap = True

        if has_gap and GAP_FILTER in self.enabled_variant_filters:
            return True

        if not variants:
            return False

        return any(v in self.enabled_variant_filters for v in variants)