from PyQt5.QtWidgets import QComboBox, QStyledItemDelegate


VARIANT_OPTIONS = [
    "",
    "match",
    "graphical",
    "phonetic",
    "morphological",
    "lexical",
]


class VariantTypeDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        model = index.model()
        info = model.get_column_info(index.column())
        if not info:
            return None

        kind, _ms_id = info
        if kind != "type":
            return None

        combo = QComboBox(parent)
        combo.addItems(VARIANT_OPTIONS)
        return combo

    def setEditorData(self, editor, index):
        if editor is None:
            return

        model = index.model()
        row = model.get_combined_row(index.row())
        kind, ms_id = model.get_column_info(index.column())

        value = ""
        if kind == "type" and row is not None:
            value = row.variants_by_ms.get(ms_id) or ""

        pos = editor.findText(value)
        editor.setCurrentIndex(pos if pos >= 0 else 0)

    def setModelData(self, editor, model, index):
        if editor is None:
            return
        model.setData(index, editor.currentText())