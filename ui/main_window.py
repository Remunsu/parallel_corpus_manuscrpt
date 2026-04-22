import re
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFileDialog,
    QComboBox,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.aligner import align_tokens
from core.context_builder import get_context_window, format_context, token_address
from core.fragment_finder import find_best_fragment
from core.tei_parser import parse_tei_file
from core.token_filters import get_available_sheets, filter_tokens_by_sheets
from core.variant_classifier import classify_alignment
from export.tei_export import write_alignment_tei
from storage.db import Database
from ui.alignment_merge import merge_pairwise_alignments
from ui.alignment_table_model import AlignmentTableModel, GAP_FILTER
from ui.context_panel import ContextPanel
from ui.sheet_selector_dialog import SheetSelectorDialog
from ui.text_viewer import TextViewer
from ui.variant_type_delegate import VariantTypeDelegate


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Параллельный корпус евангелий")
        self.resize(1750, 950)

        self.db = Database("parallel_corpus.sqlite")
        self.db.init_schema("storage/schema.sql")

        self.manuscripts = {}
        self.selected_target_sheets = []
        self.current_project_id = None
        self.current_project_name = "Без названия"
        self.current_alignment_ids = {}
        self.current_pairwise_rows = {}
        self.current_combined_rows = []
        self.current_manuscript_order = []

        self.table = QTableView()
        self.table.setItemDelegate(VariantTypeDelegate(self.table))
        self.table.clicked.connect(self.on_table_clicked)
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.ElideNone)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionsMovable(True)

        self.context_panel = ContextPanel()
        self.target_viewer = TextViewer()
        self.source_viewer = TextViewer()

        self.cmb_main_text = QComboBox()

        self.btn_load_xmls = QPushButton("Загрузить XML")
        self.btn_select_sheets = QPushButton("Выбрать листы главного списка")
        self.btn_align = QPushButton("Построить выравнивание")
        self.btn_save_project = QPushButton("Сохранить проект")
        self.btn_open_project = QPushButton("Открыть проект")
        self.btn_export_tei = QPushButton("Экспорт XML-TEI")

        self.chk_match = QCheckBox("match")
        self.chk_graphical = QCheckBox("graphical")
        self.chk_phonetic = QCheckBox("phonetic")
        self.chk_morphological = QCheckBox("morphological")
        self.chk_syntactic = QCheckBox("syntactic")
        self.chk_lexical = QCheckBox("lexical")
        self.chk_gap = QCheckBox("прочерки")

        for chk in (
            self.chk_match,
            self.chk_graphical,
            self.chk_phonetic,
            self.chk_morphological,
            self.chk_syntactic,
            self.chk_lexical,
            self.chk_gap,
        ):
            chk.setChecked(True)
            chk.stateChanged.connect(self.apply_variant_filters)

        self.btn_load_xmls.clicked.connect(self.load_manuscripts)
        self.btn_select_sheets.clicked.connect(self.select_target_sheets)
        self.btn_align.clicked.connect(self.build_alignment)
        self.btn_save_project.clicked.connect(self.save_project)
        self.btn_open_project.clicked.connect(self.open_project)
        self.btn_export_tei.clicked.connect(self.export_alignment_tei)
        self.cmb_main_text.currentIndexChanged.connect(self.on_main_changed)

        top = QHBoxLayout()
        top.addWidget(self.btn_load_xmls)
        top.addWidget(self.btn_open_project)
        top.addWidget(self.btn_save_project)
        top.addWidget(self.btn_export_tei)
        top.addWidget(self.cmb_main_text)
        top.addWidget(self.btn_select_sheets)
        top.addWidget(self.btn_align)
        top.addWidget(self.chk_match)
        top.addWidget(self.chk_graphical)
        top.addWidget(self.chk_phonetic)
        top.addWidget(self.chk_morphological)
        top.addWidget(self.chk_lexical)
        top.addWidget(self.chk_gap)

        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.context_panel, 0)
        right_layout.addWidget(self.target_viewer, 1)
        right_layout.addWidget(self.source_viewer, 1)
        right_panel.setLayout(right_layout)
        right_panel.setMinimumWidth(360)
        right_panel.setMaximumWidth(470)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.table)
        splitter.addWidget(right_panel)
        splitter.setSizes([1300, 390])

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(splitter)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def short_manuscript_title(self, full_title: str) -> str:
        if not full_title:
            return "Без названия"

        m = re.search(r'(\([^()]+\))', full_title)
        if m:
            return m.group(1)

        return full_title

    def enabled_variant_filters(self):
        result = set()

        if self.chk_match.isChecked():
            result.add("match")
        if self.chk_graphical.isChecked():
            result.add("graphical")
        if self.chk_phonetic.isChecked():
            result.add("phonetic")
        if self.chk_morphological.isChecked():
            result.add("morphological")
        if self.chk_lexical.isChecked():
            result.add("lexical")
        if self.chk_gap.isChecked():
            result.add(GAP_FILTER)

        return result

    def apply_variant_filters(self):
        model = self.table.model()
        if model is None:
            return

        model.set_variant_filters(self.enabled_variant_filters())
        self.table.resizeRowsToContents()

    def set_initial_column_widths(self):
        model = self.table.model()
        if model is None:
            return

        for col in range(model.columnCount()):
            info = model.get_column_info(col)
            if info is None:
                continue

            kind, _ms_id = info

            if col == 0:
                self.table.setColumnWidth(col, 120)
            elif kind == "word":
                self.table.setColumnWidth(col, 90)
            elif kind == "type":
                self.table.setColumnWidth(col, 70)

    def load_manuscripts(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Открыть TEI XML", "", "XML Files (*.xml)")
        if not paths:
            return

        loaded_count = 0

        for path in paths:
            manuscript_id = Path(path).stem
            if manuscript_id in self.manuscripts:
                continue

            manuscript = parse_tei_file(path, manuscript_id)
            self.manuscripts[manuscript_id] = manuscript
            self.db.save_manuscript(manuscript)
            loaded_count += 1

        self.refresh_main_combo()

        QMessageBox.information(
            self,
            "Готово",
            f"Загружено текстов: {loaded_count}\n"
            f"Всего в проекте: {len(self.manuscripts)}"
        )

        self.on_main_changed()

    def refresh_main_combo(self):
        current_id = self.current_main_id()

        self.cmb_main_text.blockSignals(True)
        self.cmb_main_text.clear()

        for manuscript_id, manuscript in self.manuscripts.items():
            short_title = self.short_manuscript_title(manuscript.name)
            self.cmb_main_text.addItem(short_title, manuscript_id)
            self.cmb_main_text.setItemData(self.cmb_main_text.count() - 1, manuscript.name, Qt.ToolTipRole)

        if current_id:
            idx = self.cmb_main_text.findData(current_id)
            if idx >= 0:
                self.cmb_main_text.setCurrentIndex(idx)

        self.cmb_main_text.blockSignals(False)

    def current_main_id(self):
        return self.cmb_main_text.currentData()

    def current_main_manuscript(self):
        ms_id = self.current_main_id()
        if not ms_id:
            return None
        return self.manuscripts.get(ms_id)

    def on_main_changed(self):
        manuscript = self.current_main_manuscript()
        self.selected_target_sheets = []

        if manuscript is None:
            return

        self.target_viewer.load_manuscript(
            manuscript,
            display_title=f"Главный текст — {self.short_manuscript_title(manuscript.name)}"
        )
        self.source_viewer.clear()
        self.context_panel.clear_panel()

    def select_target_sheets(self):
        manuscript = self.current_main_manuscript()
        if manuscript is None:
            QMessageBox.warning(self, "Ошибка", "Сначала загрузите тексты и выберите главный.")
            return

        sheets = get_available_sheets(manuscript.tokens)
        if not sheets:
            QMessageBox.warning(self, "Ошибка", "В главном тексте не найдены листы.")
            return

        dialog = SheetSelectorDialog(sheets, self)
        if dialog.exec_():
            self.selected_target_sheets = dialog.get_selected_sheets()

            QMessageBox.information(
                self,
                "Листы выбраны",
                "Выбраны листы: " + (", ".join(self.selected_target_sheets) if self.selected_target_sheets else "все")
            )

    def _format_morph(self, token) -> str:
        if token is None or not getattr(token, "morph", None):
            return "—"

        preferred_order = [
            "category",
            "case",
            "number",
            "gender",
            "person",
            "tense",
            "mood",
            "voice",
            "degree",
            "kind",
        ]

        parts = []
        seen = set()

        for key in preferred_order:
            values = token.morph.get(key, [])
            if values:
                parts.append(f"{key}=" + ",".join(values))
                seen.add(key)

        for key in sorted(token.morph.keys()):
            if key in seen:
                continue
            values = token.morph.get(key, [])
            if values:
                parts.append(f"{key}=" + ",".join(values))

        return "; ".join(parts) if parts else "—"

    def crop_main_parable_fragment(self, tokens):
        """
        Ищем начало притчи в главном тексте по характерной стартовой цепочке.
        В отличие от неудачного варианта, здесь нет повторного вызова
        find_best_fragment(cropped, cropped), который мог резать фрагмент неверно.
        """
        if not tokens:
            return tokens

        def token_eq(token, variants):
            values = {
                token.surface.lower(),
                (token.lemma or "").lower(),
                (token.norm_graph or "").lower(),
                (token.abbr_skeleton or "").lower(),
            }
            return any(v in values for v in variants)

        start_patterns = [
            {"притъча", "притъчю", "притъчѫ", "притча"},
            {"сии", "сию", "сиѭ", "сиюю", "сьи"},
            {"человѣкъ", "чловѣкъ", "человѣк", "чловѣк", "члвк"},
            {"нѣкъто", "нѣкто", "некто"},
            {"имѣти", "имѣꙗ", "имый"},
            {"дъва", "два"},
            {"сꙑнъ", "сынъ", "снъ", "сн҃а", "сна"},
        ]

        best_start = None
        best_score = -1

        for i in range(len(tokens)):
            score = 0
            pos = i

            for pattern in start_patterns:
                matched = False
                for j in range(pos, min(len(tokens), pos + 4)):
                    if token_eq(tokens[j], pattern):
                        score += 1
                        pos = j + 1
                        matched = True
                        break
                if not matched:
                    score -= 1

            if score > best_score:
                best_score = score
                best_start = i

        if best_start is None or best_score < 3:
            return tokens

        return tokens[best_start:]

    def build_alignment(self):
        main_ms = self.current_main_manuscript()
        if main_ms is None:
            QMessageBox.warning(self, "Ошибка", "Сначала загрузите тексты и выберите главный.")
            return

        if len(self.manuscripts) < 2:
            QMessageBox.warning(self, "Ошибка", "Нужно загрузить минимум два текста.")
            return

        target_tokens_all = filter_tokens_by_sheets(main_ms.tokens, self.selected_target_sheets)
        if not target_tokens_all:
            QMessageBox.warning(self, "Ошибка", "После выбора листов не осталось слов для выравнивания.")
            return

        target_tokens = self.crop_main_parable_fragment(target_tokens_all)
        if not target_tokens:
            QMessageBox.warning(self, "Ошибка", "Не удалось выделить главный фрагмент притчи.")
            return

        self.current_project_name = self.short_manuscript_title(main_ms.name)
        self.current_alignment_ids = {}
        self.current_pairwise_rows = {}

        for ms_id, manuscript in self.manuscripts.items():
            if ms_id == main_ms.manuscript_id:
                continue

            source_tokens = manuscript.tokens
            s_start, s_end, score = find_best_fragment(target_tokens, source_tokens)

            if s_end <= s_start:
                s_start = 0
                s_end = min(len(source_tokens), len(target_tokens))

            fragment = source_tokens[s_start:s_end]
            if not fragment:
                continue

            rows = align_tokens(target_tokens, fragment)
            rows = classify_alignment(rows)

            self.current_pairwise_rows[ms_id] = rows

        if not self.current_pairwise_rows:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Не удалось построить выравнивание ни для одного сопоставляемого текста."
            )
            return

        self.current_combined_rows = merge_pairwise_alignments(
            main_ms.manuscript_id,
            self.current_pairwise_rows
        )

        manuscript_order = [main_ms.manuscript_id] + [
            ms_id for ms_id in self.manuscripts.keys()
            if ms_id != main_ms.manuscript_id
        ]
        self.current_manuscript_order = manuscript_order

        manuscript_titles = {
            ms_id: self.short_manuscript_title(self.manuscripts[ms_id].name)
            for ms_id in manuscript_order
        }

        model = AlignmentTableModel(
            combined_rows=self.current_combined_rows,
            manuscript_order=manuscript_order,
            manuscript_titles=manuscript_titles,
            on_variant_edited=self.auto_save_variant_edit
        )
        self.table.setModel(model)
        self.table.setItemDelegate(VariantTypeDelegate(self.table))
        self.table.resizeRowsToContents()

        self.apply_variant_filters()
        self.set_initial_column_widths()

        QMessageBox.information(
            self,
            "Готово",
            "Выравнивание построено.\n\n"
            f"Главный текст: {self.short_manuscript_title(main_ms.name)}\n"
            f"Главный фрагмент: {len(target_tokens)} слов\n"
            f"Сопоставлено текстов: {len(self.current_pairwise_rows)}"
        )

    def auto_save_variant_edit(self, ms_id, pair_row):
        alignment_id = self.current_alignment_ids.get(ms_id)
        if alignment_id is None:
            return

        self.db.update_alignment_row(
            alignment_id=alignment_id,
            row_no=pair_row.row_no,
            manual_variant_type=pair_row.manual_variant_type,
            status=pair_row.status
        )

    def save_project(self):
        if not self.current_manuscript_order:
            QMessageBox.warning(self, "Ошибка", "Нет данных проекта для сохранения.")
            return

        main_ms = self.current_main_manuscript()
        if main_ms is None:
            QMessageBox.warning(self, "Ошибка", "Не выбран главный текст.")
            return

        project_name = self.current_project_name or self.short_manuscript_title(main_ms.name)

        if self.current_project_id is None:
            self.current_project_id = self.db.create_project(
                name=project_name,
                main_manuscript_id=main_ms.manuscript_id,
                selected_sheets=self.selected_target_sheets,
                manuscript_order=self.current_manuscript_order,
            )
        else:
            self.db.update_project(
                project_id=self.current_project_id,
                name=project_name,
                main_manuscript_id=main_ms.manuscript_id,
                selected_sheets=self.selected_target_sheets,
                manuscript_order=self.current_manuscript_order,
            )
            self.db.delete_project_alignments(self.current_project_id)

        self.current_alignment_ids = {}

        for ms_id, rows in self.current_pairwise_rows.items():
            alignment_id = self.db.save_alignment(
                project_id=self.current_project_id,
                target_manuscript_id=main_ms.manuscript_id,
                source_manuscript_id=ms_id,
                rows=rows
            )
            self.current_alignment_ids[ms_id] = alignment_id

        QMessageBox.information(self, "Готово", f"Проект сохранён. ID: {self.current_project_id}")

    def open_project(self):
        projects = self.db.list_projects()
        if not projects:
            QMessageBox.warning(self, "Ошибка", "Сохранённых проектов нет.")
            return

        row = projects[0]
        project_id = row["project_id"]

        project = self.db.load_project(project_id)
        if project is None:
            QMessageBox.warning(self, "Ошибка", "Не удалось загрузить проект.")
            return

        self.manuscripts = self.db.load_all_manuscripts()
        self.current_project_id = project["project_id"]
        self.current_project_name = project["name"]
        self.selected_target_sheets = project["selected_sheets"]
        self.current_manuscript_order = project["manuscript_order"]

        self.refresh_main_combo()

        idx = self.cmb_main_text.findData(project["main_manuscript_id"])
        if idx >= 0:
            self.cmb_main_text.setCurrentIndex(idx)

        self.current_pairwise_rows = self.db.load_project_pairwise_rows(project_id)
        self.current_alignment_ids = self.db.load_project_alignment_ids(project_id)

        self.current_combined_rows = merge_pairwise_alignments(
            project["main_manuscript_id"],
            self.current_pairwise_rows
        )

        manuscript_titles = {
            ms_id: self.short_manuscript_title(self.manuscripts[ms_id].name)
            for ms_id in self.current_manuscript_order
            if ms_id in self.manuscripts
        }

        model = AlignmentTableModel(
            combined_rows=self.current_combined_rows,
            manuscript_order=self.current_manuscript_order,
            manuscript_titles=manuscript_titles,
            on_variant_edited=self.auto_save_variant_edit
        )
        self.table.setModel(model)
        self.table.setItemDelegate(VariantTypeDelegate(self.table))
        self.apply_variant_filters()
        self.set_initial_column_widths()
        self.table.resizeRowsToContents()

        main_ms = self.current_main_manuscript()
        if main_ms is not None:
            self.target_viewer.load_manuscript(
                main_ms,
                display_title=f"Главный текст — {self.short_manuscript_title(main_ms.name)}"
            )

        self.source_viewer.clear()
        self.context_panel.clear_panel()

        QMessageBox.information(self, "Готово", f"Проект загружен: {project['name']}")

    def export_alignment_tei(self):
        if not self.current_combined_rows or not self.current_manuscript_order:
            QMessageBox.warning(self, "Ошибка", "Нет выравнивания для экспорта.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить XML-TEI",
            "parallel_corpus_alignment.xml",
            "XML Files (*.xml)"
        )
        if not path:
            return

        manuscript_titles = {
            ms_id: self.short_manuscript_title(self.manuscripts[ms_id].name)
            for ms_id in self.current_manuscript_order
            if ms_id in self.manuscripts
        }

        write_alignment_tei(
            output_path=path,
            project_name=self.current_project_name or "Параллельный корпус",
            main_manuscript_id=self.current_manuscript_order[0],
            manuscript_order=self.current_manuscript_order,
            manuscript_titles=manuscript_titles,
            combined_rows=self.current_combined_rows,
        )

        QMessageBox.information(self, "Готово", f"Экспорт выполнен:\n{path}")

    def on_table_clicked(self, index):
        model = self.table.model()
        if model is None:
            return

        combined_row = model.get_combined_row(index.row())
        if combined_row is None:
            return

        info = model.get_column_info(index.column())
        if info is None:
            return

        _kind, ms_id = info
        token = combined_row.tokens_by_ms.get(ms_id)

        if token is None:
            self.context_panel.clear_panel()
            return

        manuscript = self.manuscripts.get(ms_id)
        if manuscript is None:
            return

        short_title = self.short_manuscript_title(manuscript.name)

        if ms_id == self.current_manuscript_order[0]:
            viewer = self.target_viewer
            side_label = f"Главный текст — {short_title}"
            variant_value = "—"
        else:
            viewer = self.source_viewer
            viewer.load_manuscript(manuscript, display_title=short_title)
            side_label = short_title
            variant_value = combined_row.variants_by_ms.get(ms_id) or "—"

        self.show_token_context(ms_id, token, viewer, side_label, variant_value)

    def show_token_context(self, ms_id, token, viewer, side_label, variant_value):
        manuscript = self.manuscripts.get(ms_id)
        if manuscript is None:
            return

        context_tokens = get_context_window(manuscript.tokens, token.position, window=10)
        context_str = format_context(context_tokens, token.position)
        address = token_address(token)
        morph_str = self._format_morph(token)

        self.context_panel.set_data(
            side=side_label,
            word=token.surface,
            lemma=token.lemma,
            morph=morph_str,
            address=address,
            variant_type=variant_value,
            context=context_str
        )

        viewer.jump_to_xml_id(token.xml_id)