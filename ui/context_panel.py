from PyQt5.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget


class ContextPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.lbl_side = QLabel("Сторона: —")
        self.lbl_word = QLabel("Слово: —")
        self.lbl_lemma = QLabel("Лемма: —")
        self.lbl_morph = QLabel("Морфология: —")
        self.lbl_address = QLabel("Адрес: —")
        self.lbl_variant = QLabel("Тип: —")

        self.context_text = QTextEdit()
        self.context_text.setReadOnly(True)
        self.context_text.setMaximumHeight(70)

        layout = QVBoxLayout()
        layout.addWidget(self.lbl_side)
        layout.addWidget(self.lbl_word)
        layout.addWidget(self.lbl_lemma)
        layout.addWidget(self.lbl_morph)
        layout.addWidget(self.lbl_address)
        layout.addWidget(self.lbl_variant)
        layout.addWidget(self.context_text)

        self.setLayout(layout)

    def clear_panel(self):
        self.lbl_side.setText("Сторона: —")
        self.lbl_word.setText("Слово: —")
        self.lbl_lemma.setText("Лемма: —")
        self.lbl_morph.setText("Морфология: —")
        self.lbl_address.setText("Адрес: —")
        self.lbl_variant.setText("Тип: —")
        self.context_text.clear()

    def set_data(
        self,
        side: str,
        word: str,
        lemma: str,
        morph: str,
        address: str,
        variant_type: str,
        context: str,
    ):
        self.lbl_side.setText(f"Сторона: {side}")
        self.lbl_word.setText(f"Слово: {word or '—'}")
        self.lbl_lemma.setText(f"Лемма: {lemma or '—'}")
        self.lbl_morph.setText(f"Морфология: {morph or '—'}")
        self.lbl_address.setText(f"Адрес: {address or '—'}")
        self.lbl_variant.setText(f"Тип: {variant_type or '—'}")
        self.context_text.setPlainText(context or "")