from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor, QFont
from PyQt5.QtWidgets import QTextEdit

from core.models import Manuscript


class TextViewer(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.manuscript = None
        self.xml_id_to_span = {}
        self.viewer_title = ""

    def clear(self):
        super().clear()
        self.manuscript = None
        self.xml_id_to_span = {}
        self.viewer_title = ""
        self.setExtraSelections([])

    def load_manuscript(self, manuscript: Manuscript, display_title: str = None):
        super().clear()
        self.manuscript = manuscript
        self.xml_id_to_span = {}
        self.setExtraSelections([])
        self.viewer_title = display_title or manuscript.name or "Без названия"

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.Start)

        cursor.insertText(f"[{self.viewer_title}]\n")

        current_sheet = None
        current_page = None

        for token in manuscript.tokens:
            if token.sheet != current_sheet:
                current_sheet = token.sheet
                cursor.insertText(f"\n[Лист {current_sheet or '—'}]\n")

            if token.page != current_page:
                current_page = token.page
                cursor.insertText(f"\n[Страница {current_page or '—'}]\n")

            if token.line_break_before:
                cursor.insertText("\n")

            start_pos = cursor.position()
            cursor.insertText(token.surface)
            end_pos = cursor.position()

            if token.xml_id:
                self.xml_id_to_span[token.xml_id] = (start_pos, end_pos)

            cursor.insertText(" ")

        self.moveCursor(QTextCursor.Start)

    def jump_to_xml_id(self, xml_id: str):
        if not xml_id or xml_id not in self.xml_id_to_span:
            return

        start_pos, end_pos = self.xml_id_to_span[xml_id]

        cursor = self.textCursor()
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        self.setFocus()

        selection = QTextEdit.ExtraSelection()
        selection.cursor = cursor

        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#ffeb3b"))
        fmt.setForeground(QColor("#000000"))
        fmt.setFontWeight(QFont.Bold)
        selection.format = fmt

        self.setExtraSelections([selection])