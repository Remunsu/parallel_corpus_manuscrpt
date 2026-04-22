from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QListWidget, QListWidgetItem,
    QVBoxLayout, QLabel
)
from PyQt5.QtCore import Qt


class SheetSelectorDialog(QDialog):
    def __init__(self, sheets, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор листов главного списка")
        self.resize(300, 400)

        self.list_widget = QListWidget()
        for sheet in sheets:
            item = QListWidgetItem(sheet)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.list_widget.addItem(item)

        info = QLabel("Отметьте листы, которые нужно взять для главного текста.")
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addWidget(self.list_widget)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_selected_sheets(self):
        result = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                result.append(item.text())
        return result