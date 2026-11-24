"""Édition des doigtés en coordonnées de diagramme, du grave vers l’aigu."""
from copy import deepcopy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit,
    QSpinBox, QPushButton, QCheckBox, QLabel)
from drawing import CHORD_W, CHORD_H, LEFT, TOP, DX, DY, chord


def blank():
    return dict(name="Mon accord", start=1, frets=[-1]*6, fingers=[0]*6, barre=None)


class Diagram(QWidget):
    def __init__(self, editable=False):
        super().__init__()
        self.data = blank()
        self.editable = editable
        self.finger = 0
        self.bar_mode = False
        self.anchor = None
        self.setMinimumHeight(165)

    def geometry_values(self):
        scale = min((self.width()-8)/CHORD_W, (self.height()-8)/CHORD_H)
        return scale, (self.width()-CHORD_W*scale)/2, (self.height()-CHORD_H*scale)/2

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), Qt.GlobalColor.white)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale, x, y = self.geometry_values()
        p.translate(x, y)
        p.scale(scale, scale)
        chord(p, self.data)
        p.end()

    def hit(self, event):
        scale, x, y = self.geometry_values()
        pos = event.position()
        return round(((pos.x()-x)/scale-LEFT)/DX), int((((pos.y()-y)/scale-TOP)//DY))

    def mousePressEvent(self, event):
        if not self.editable or event.button() != Qt.MouseButton.LeftButton:
            return
        i, row = self.hit(event)
        if not (0 <= i < 6 and -1 <= row < 5):
            return
        c = self.data
        if self.bar_mode and row >= 0:
            self.anchor = (i, row)
            return
        fret = c["start"]+row
        if row < 0:
            value = -1 if c["frets"][i] == 0 else 0
        else:
            value = -1 if c["frets"][i] == fret and c["fingers"][i] == self.finger else fret
        b = c["barre"]
        if b and b[1] <= i <= b[2] and value < b[0]:
            c["barre"] = None
        c["frets"][i] = value
        c["fingers"][i] = self.finger if value > 0 else 0
        self.update()

    def mouseReleaseEvent(self, event):
        if self.anchor is None:
            return
        i, row = self.anchor
        self.anchor = None
        end, _ = self.hit(event)
        a, b = sorted((i, max(0, min(5, end))))
        if a == b:
            return
        c = self.data
        fret = c["start"]+row
        c["barre"] = [fret, a, b]
        for s in range(a, b+1):
            if c["frets"][s] <= fret:
                c["frets"][s] = fret
                c["fingers"][s] = 0
        self.update()


class ChordCreator(QWidget):
    insert = Signal(dict)
    save = Signal(dict)

    def __init__(self, initial=None):
        super().__init__()
        layout = QVBoxLayout(self)
        self.diagram = Diagram(True)
        self.diagram.data = deepcopy(initial) if initial else blank()
        c = self.diagram.data
        form = QFormLayout()
        self.name = QLineEdit(c["name"])
        self.start = QSpinBox()
        self.start.setRange(1, 20)
        self.start.setValue(c["start"])
        self.finger = QSpinBox()
        self.finger.setRange(0, 4)
        self.finger.setSpecialValueText("Sans numéro")
        for label, field in [("Nom", self.name), ("Première frette", self.start), ("Doigt", self.finger)]:
            form.addRow(label, field)
        layout.addLayout(form)
        layout.addWidget(self.diagram)
        help_text = QLabel("Cliquez sur une case pour placer ou retirer un doigt. Cliquez au-dessus du manche pour alterner ○ et ×.")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        bar = QCheckBox("Tracer un barré par glissement")
        bar.toggled.connect(lambda on: setattr(self.diagram, "bar_mode", on))
        layout.addWidget(bar)
        clear = QPushButton("Retirer le barré")
        clear.clicked.connect(self.clear_bar)
        layout.addWidget(clear)
        self.actions = []
        for label, signal in [("Enregistrer dans ma bibliothèque", self.save), ("Insérer sur la feuille", self.insert)]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked=False, s=signal: s.emit(deepcopy(self.diagram.data)))
            layout.addWidget(btn)
            self.actions.append(btn)
        layout.addStretch()
        self.name.textChanged.connect(self.rename)
        self.start.valueChanged.connect(self.transpose)
        self.finger.valueChanged.connect(lambda n: setattr(self.diagram, "finger", n))

    def clear_bar(self):
        self.diagram.data["barre"] = None
        self.diagram.update()

    def rename(self, value):
        self.diagram.data["name"] = value.strip()
        for btn in self.actions:
            btn.setEnabled(bool(value.strip()))
        self.diagram.update()

    def transpose(self, start):
        c = self.diagram.data
        delta = start-c["start"]
        c["start"] = start
        c["frets"] = [f+delta if f > 0 else f for f in c["frets"]]
        if c["barre"]:
            c["barre"][0] += delta
        self.diagram.update()

