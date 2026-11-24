"""Grille de saisie à six cordes. Les barres précèdent leur colonne."""
from copy import deepcopy
from time import monotonic
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QAbstractItemView)
from storage import TECH


class NoteGrid(QTableWidget):
    def __init__(self, tab):
        super().__init__(6, len(tab["cells"][0]))
        self.bars = set(tab["bars"])
        self.pending = None
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.horizontalHeader().setDefaultSectionSize(36)
        self.horizontalHeader().setMinimumSectionSize(25)
        for row, values in enumerate(tab["cells"]):
            for col, value in enumerate(values):
                self.write(row, col, value)
        self.headers()
        self.currentCellChanged.connect(self.reset_pending)
        self.cellClicked.connect(self.reset_pending)
        self.setCurrentCell(0, 0)

    def reset_pending(self, *args):
        self.pending = None

    def write(self, row, col, value):
        item = QTableWidgetItem(value)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row, col, item)

    def headers(self):
        self.setHorizontalHeaderLabels([("│ " if i in self.bars else "")+str(i+1)
                                        for i in range(self.columnCount())])

    def keyPressEvent(self, event):
        row, col = self.currentRow(), self.currentColumn()
        key = event.text()
        if row < 0 or col < 0:
            return super().keyPressEvent(event)
        if key and key in "0123456789":
            now = monotonic()
            old = self.pending
            value = key
            if old and now-old[1] < 1.2 and int(old[0]+key) <= 24:
                value = str(int(old[0]+key))
                self.pending = None
            else:
                self.pending = (key, now) if key in "12" else None
            self.write(row, col, value)
        elif key in TECH:
            self.write(row, col, key)
            self.pending = None
        elif key == "|":
            if col:
                self.bars.symmetric_difference_update([col])
                self.headers()
            self.pending = None
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.write(row, col, "")
            self.pending = None
        else:
            super().keyPressEvent(event)


class TabEditor(QDialog):
    def __init__(self, tab, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Éditer la tablature")
        self.resize(810, 445)
        self.tab = deepcopy(tab)
        self.grid = NoteGrid(tab)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Flèches pour naviguer · 0–24 pour les frettes · | pour une barre avant la colonne"))
        layout.addWidget(QLabel("Techniques : h, p, /, \\, ~, b · Suppr pour effacer"))
        self.tuning = QLineEdit(" ".join(tab["tuning"]))
        form = QFormLayout()
        form.addRow("Accordage de haut en bas (6 noms)", self.tuning)
        self.per_line = QSpinBox()
        self.per_line.setRange(1, 16)
        self.per_line.setValue(tab["per_line"])
        self.spacing = QSpinBox()
        self.spacing.setRange(10, 40)
        self.spacing.setValue(tab["spacing"])
        form.addRow("Mesures par ligne", self.per_line)
        form.addRow("Espacement des notes", self.spacing)
        layout.addLayout(form)
        layout.addWidget(self.grid)
        row = QHBoxLayout()
        for label, slot in [("Insérer une colonne", self.insert), ("Retirer la colonne", self.remove)]:
            button = QPushButton(label)
            button.clicked.connect(slot)
            row.addWidget(button)
        layout.addLayout(row)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.tuning.textChanged.connect(self.update_tuning)
        self.update_tuning()
        self.grid.setFocus()

    def update_tuning(self):
        names = self.tuning.text().split()
        valid = len(names) == 6 and all(len(n) <= 5 for n in names)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(valid)
        if valid:
            self.grid.setVerticalHeaderLabels(names)

    def insert(self):
        g = self.grid
        if g.columnCount() >= 512:
            return
        col = g.currentColumn()+1
        g.insertColumn(col)
        g.bars = {k+(k>=col) for k in g.bars}
        g.headers()
        g.setCurrentCell(max(0, g.currentRow()), col)
        g.setFocus()

    def remove(self):
        g = self.grid
        col = g.currentColumn()
        if g.columnCount() > 1 and col >= 0:
            g.removeColumn(col)
            g.bars = {k-(k>col) for k in g.bars if k != col}
            g.headers()
        g.setFocus()

    def result_data(self):
        g = self.grid
        return dict(tuning=self.tuning.text().split(), per_line=self.per_line.value(),
                    spacing=self.spacing.value(), bars=sorted(g.bars),
                    cells=[[g.item(r,c).text() if g.item(r,c) else "" for c in range(g.columnCount())]
                           for r in range(6)])

