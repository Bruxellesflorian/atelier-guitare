"""Catalogue livré avec l’application et variantes enregistrées par l’utilisateur."""
from pathlib import Path
from PySide6.QtCore import Signal, QStandardPaths
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QListWidget,
    QPushButton, QMessageBox)
from chord_creator import Diagram
from storage import read_json, save_json, validate_chord


def normalize(name):
    name = name.strip().replace("♯", "#").replace("♭", "b")
    flats = {"Db":"C#", "Eb":"D#", "Gb":"F#", "Ab":"G#", "Bb":"A#"}
    root = name[:1].upper()+name[1:2]
    return (flats.get(root, root)+name[2:]).casefold()


class ChordLibrary(QWidget):
    insert = Signal(dict)

    def __init__(self):
        super().__init__()
        self.stock = read_json(Path(__file__).with_name("chords_data.json"))
        folder = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
        self.path = folder / "mes_accords.json"
        self.custom = []
        self.load_error = None
        if self.path.exists():
            try:
                custom = read_json(self.path)
                for c in custom:
                    validate_chord(c)
                self.custom = custom
            except (ValueError, TypeError, KeyError, OSError) as exc:
                self.load_error = str(exc)
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Rechercher · Am7, F#m, Cadd9…")
        self.listing = QListWidget()
        self.preview = Diagram()
        self.button = QPushButton("Insérer sur la feuille")
        for w in (self.search, self.listing, self.preview, self.button):
            layout.addWidget(w)
        self.search.textChanged.connect(self.refresh)
        self.listing.currentRowChanged.connect(self.select)
        self.button.clicked.connect(self.place)
        self.listing.itemDoubleClicked.connect(self.place)
        self.refresh()

    def refresh(self):
        query = normalize(self.search.text())
        self.entries = [(c, True) for c in self.custom]+[(c, False) for c in self.stock]
        self.entries = [(c, own) for c, own in self.entries if query in normalize(c["name"])]
        self.entries.sort(key=lambda pair: (normalize(pair[0]["name"]) != query, not pair[1]))
        self.listing.clear()
        self.listing.addItems([c["name"]+("  · personnel" if own else "") for c, own in self.entries])
        self.listing.setCurrentRow(0 if self.entries else -1)
        self.select(self.listing.currentRow())

    def select(self, row):
        self.button.setEnabled(row >= 0)
        self.preview.setVisible(row >= 0)
        if row >= 0:
            self.preview.data = self.entries[row][0]
            self.preview.update()

    def place(self, *args):
        row = self.listing.currentRow()
        if row >= 0:
            self.insert.emit(self.entries[row][0])

    def store(self, data):
        try:
            if self.load_error:
                raise ValueError(f"Réparez la bibliothèque avant d’enregistrer : {self.path}")
            validate_chord(data)
            updated = [*self.custom, data]
            self.path.parent.mkdir(parents=True, exist_ok=True)
            save_json(self.path, updated)
            self.custom = updated
            self.search.setText(data["name"])
            self.refresh()
            return True
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Bibliothèque", str(exc))
            return False

