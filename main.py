"""Point d’entrée de l’atelier de tablature A4."""
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QSaveFile, QIODevice, QLocale
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QDialog, QVBoxLayout,
    QHBoxLayout, QFormLayout, QPlainTextEdit, QDialogButtonBox, QSpinBox, QLabel,
    QComboBox, QToolBar, QTabWidget, QSplitter, QMessageBox, QFileDialog, QStyleFactory)
from canvas_a4 import Canvas, Sheet, render_pdf
from chord_library import ChordLibrary
from chord_creator import ChordCreator
from drawing import tab_size
from storage import new_tab, read_json, save_json, validate_project
from tab_editor import TabEditor


class TextEditor(QDialog):
    def __init__(self, data, parent):
        super().__init__(parent)
        self.setWindowTitle("Texte, paroles ou titre")
        layout = QFormLayout(self)
        self.body = QPlainTextEdit(data["text"])
        self.size = QSpinBox()
        self.size.setRange(8, 96)
        self.size.setValue(data["size"])
        layout.addRow(self.body)
        layout.addRow("Corps (unités de feuille)", self.size)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        self.resize(430, 260)

    def result_data(self):
        return dict(text=self.body.toPlainText(), size=self.size.value())


class Studio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1190, 845)
        self.path = None
        self.pages = []
        self.dirty = False
        self.canvas = Canvas()
        self.library = ChordLibrary()
        self.creator = ChordCreator()
        self.library.insert.connect(self.insert_chord)
        self.creator.insert.connect(self.insert_chord)
        self.creator.save.connect(self.store_chord)
        side = QTabWidget()
        side.addTab(self.library, "Accords")
        side.addTab(self.creator, "Créer un accord")
        side.setMinimumWidth(245)
        split = QSplitter()
        split.addWidget(side)
        split.addWidget(self.canvas)
        split.setStretchFactor(1, 1)
        split.setSizes([270, 900])
        self.setCentralWidget(split)
        self.toolbar = QToolBar("Édition")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        menus = self.menuBar()
        file = menus.addMenu("&Fichier")
        edit = menus.addMenu("&Édition")
        view = menus.addMenu("&Affichage")
        for label, keys, fn in [
            ("Nouveau projet", "Ctrl+N", self.new), ("Ouvrir…", "Ctrl+O", self.open),
            ("Enregistrer", "Ctrl+S", self.save), ("Enregistrer sous…", "Ctrl+Shift+S", self.save_as),
            ("Exporter en PDF…", "Ctrl+Shift+E", self.export)]:
            self.action(file, label, keys, fn, label.startswith("Exporter"))
        self.action(edit, "Tablature…", "Ctrl+T", lambda: self.edit_tab(), True)
        self.action(edit, "Texte…", "Ctrl+Shift+T", lambda: self.edit_text(), True)
        self.action(edit, "Dupliquer", "Ctrl+D", lambda: self.sheet.duplicate())
        self.action(edit, "Supprimer", "Delete", lambda: self.sheet.delete())
        self.action(edit, "Aligner à gauche", "Ctrl+Alt+L", lambda: self.sheet.align("left"))
        self.action(edit, "Centrer horizontalement", "Ctrl+Alt+C", lambda: self.sheet.align("center"))
        self.action(edit, "Aligner en haut", "Ctrl+Alt+T", lambda: self.sheet.align("top"))
        self.toolbar.addSeparator()
        self.page_box = QComboBox()
        self.page_box.setAccessibleName("Page active")
        self.page_box.currentIndexChanged.connect(self.activate)
        self.toolbar.addWidget(self.page_box)
        self.action(edit, "+ Page", "Ctrl+Return", self.add_page, True)
        self.toolbar.addSeparator()
        self.action(view, "−", "Ctrl+-", lambda: self.canvas.zoom(1/1.2), True)
        self.action(view, "+", "Ctrl++", lambda: self.canvas.zoom(1.2), True)
        self.action(view, "Page entière", "Ctrl+0", self.canvas.fit, True)
        self.snap = QAction("Magnétisme (1 mm)", self, checkable=True)
        self.snap.toggled.connect(self.set_snap)
        view.addAction(self.snap)
        self.toolbar.addAction(self.snap)
        self.statusBar().showMessage("Double-clic pour modifier · Ctrl+clic pour sélectionner plusieurs objets · Règles en mm")
        self.reset([[]], None)
        QTimer.singleShot(0, self.canvas.fit)
        if self.library.load_error:
            self.statusBar().showMessage("Bibliothèque personnelle illisible : "+str(self.library.path))

    @property
    def sheet(self):
        return self.pages[self.page_box.currentIndex()]

    def action(self, menu, label, keys, fn, toolbar=False):
        action = QAction(label, self)
        action.setShortcut(QKeySequence(keys))
        action.triggered.connect(lambda checked=False: fn())
        menu.addAction(action)
        if toolbar:
            self.toolbar.addAction(action)
        return action

    def mark(self):
        self.dirty = True
        self.caption()

    def caption(self):
        name = self.path.name if self.path else "Sans titre"
        self.setWindowTitle(f"{'● ' if self.dirty else ''}{name} — Atelier Guitare")

    def set_snap(self, enabled):
        for sheet in self.pages:
            sheet.snap = enabled

    def activate(self, index):
        if 0 <= index < len(self.pages):
            self.canvas.setScene(self.pages[index])
            if self.canvas.auto_fit:
                self.canvas.fit()

    def append(self, records):
        scene = Sheet(records)
        scene.snap = self.snap.isChecked()
        scene.modified.connect(self.mark)
        scene.edit.connect(self.edit_object)
        self.pages.append(scene)
        self.page_box.addItem(f"Page {len(self.pages)}")
        self.page_box.setCurrentIndex(len(self.pages)-1)

    def add_page(self):
        self.append([])
        self.mark()

    def reset(self, pages, path):
        self.page_box.clear()
        self.canvas.setScene(None)
        self.pages.clear()
        for records in pages:
            self.append(records)
        self.page_box.setCurrentIndex(0)
        self.path = path
        self.dirty = False
        self.caption()

    def insert_chord(self, chord):
        self.sheet.insert("chord", chord, 100, 102)

    def store_chord(self, chord):
        if self.library.store(chord):
            self.statusBar().showMessage("Accord enregistré dans votre bibliothèque.", 4000)

    def edit_object(self, b):
        if b.kind == "tab":
            self.edit_tab(b)
        elif b.kind == "text":
            self.edit_text(b)
        else:
            dialog = QDialog(self)
            dialog.setWindowTitle("Modifier le diagramme")
            layout = QVBoxLayout(dialog)
            creator = ChordCreator(b.data)
            for button in creator.actions:
                button.hide()
            layout.addWidget(creator)
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            creator.name.textChanged.connect(lambda v: buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(v.strip())))
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            if dialog.exec():
                b.data = creator.diagram.data
                b.update()
                self.mark()

    def edit_tab(self, b=None):
        dialog = TabEditor(b.data if b else new_tab(), self)
        if dialog.exec():
            data = dialog.result_data()
            if b:
                b.data = data
                b.update()
                self.mark()
            else:
                w, h = tab_size(data)
                self.sheet.insert("tab", data, min(558, max(540,w)), min(820,h))

    def edit_text(self, b=None):
        dialog = TextEditor(b.data if b else dict(text="", size=22), self)
        if dialog.exec():
            data = dialog.result_data()
            if b:
                b.data = data
                b.update()
                self.mark()
            elif data["text"]:
                self.sheet.insert("text", data, 450, 95)

    def confirm_leave(self):
        if not self.dirty:
            return True
        opts = QMessageBox.StandardButton
        answer = QMessageBox.question(self, "Projet modifié", "Enregistrer les modifications du projet ?",
                                      opts.Save | opts.Discard | opts.Cancel, opts.Save)
        return answer == opts.Discard or (answer == opts.Save and self.save())

    def new(self):
        if self.confirm_leave():
            self.reset([[]], None)

    def open(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Ouvrir un projet", "", "Atelier Guitare (*.gtab)")
        if not filename:
            return
        try:
            data = read_json(filename)
            validate_project(data)
            if self.confirm_leave():
                self.reset(data["pages"], Path(filename))
        except (OSError, TypeError, ValueError, KeyError, IndexError) as exc:
            QMessageBox.warning(self, "Ouverture impossible", str(exc))

    def document(self):
        return dict(version=1, pages=[s.records() for s in self.pages])

    def write(self, path):
        try:
            doc = self.document()
            validate_project(doc)
            save_json(path, doc)
            self.path = path
            self.dirty = False
            self.caption()
            return True
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Enregistrement impossible", str(exc))
            return False

    def save(self):
        return self.write(self.path) if self.path else self.save_as()

    def destination(self, label, ext):
        dialog = QFileDialog(self, label)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilter(f"{label} (*.{ext})")
        dialog.setDefaultSuffix(ext)
        dialog.selectFile(str(self.path.with_suffix("."+ext)) if self.path else "Partition."+ext)
        return Path(dialog.selectedFiles()[0]) if dialog.exec() else None

    def save_as(self):
        path = self.destination("Projet guitare", "gtab")
        return self.write(path) if path else False

    def export(self):
        path = self.destination("Document PDF", "pdf")
        if not path:
            return
        target = QSaveFile(str(path))
        try:
            if not target.open(QIODevice.OpenModeFlag.WriteOnly):
                raise OSError(target.errorString())
            render_pdf(target, self.pages)
            if not target.commit():
                raise OSError(target.errorString())
            self.statusBar().showMessage(f"PDF exporté · {path}", 6000)
        except OSError as exc:
            target.cancelWriting()
            QMessageBox.warning(self, "Export impossible", str(exc))

    def closeEvent(self, event):
        event.accept() if self.confirm_leave() else event.ignore()


def main():
    if sys.platform == "win32":
        from ctypes import windll
        windll.shell32.SetCurrentProcessExplicitAppUserModelID("AtelierGuitare.Desktop")
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(Path(__file__).with_name("atelier_guitare.ico"))))
    app.setOrganizationName("AtelierGuitare")
    app.setApplicationName("Atelier Guitare")
    app.setStyle(QStyleFactory.create("Fusion"))
    QLocale.setDefault(QLocale(QLocale.Language.French))
    app.setStyleSheet("""
        QMainWindow, QToolBar, QStatusBar { background: #edf2ef; color: #213932; }
        QToolBar { padding: 6px; spacing: 4px; border: 0; }
        QToolButton, QPushButton { padding: 5px 8px; }
        QToolBar QToolButton {
            color: #213932; background-color: #ffffff;
            border: 1px solid #82998f; border-radius: 4px;
        }
        QToolBar QToolButton:hover { background-color: #d9ece5; border-color: #387466; }
        QToolBar QToolButton:checked, QToolBar QToolButton:pressed {
            color: #ffffff; background-color: #126b60; border-color: #10574e;
        }
        QToolBar QToolButton:focus { border: 2px solid #126b60; padding: 4px 7px; }
        QToolBar QToolButton:disabled { color: #626f69; background-color: #e4e9e6; }
        QListWidget::item { padding: 4px; }
        QListWidget::item:selected, QTableWidget::item:selected { background: #126b60; color: white; }
        QTabBar::tab { padding: 8px 12px; }
    """)
    window = Studio()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

