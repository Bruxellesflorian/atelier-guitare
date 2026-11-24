"""Format de projet et écritures atomiques communes aux deux bibliothèques."""
import json
import math
from pathlib import Path

from PySide6.QtCore import QIODevice, QSaveFile

WIDTH, HEIGHT = 630, 891  # Trois unités de scène par millimètre.
TECH = set("hp/\\~b")
DEFAULT_TUNING = ["E", "B", "G", "D", "A", "E"]  # De haut en bas.


def save_json(path, data):
    payload = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    target = QSaveFile(str(path))
    if not target.open(QIODevice.OpenModeFlag.WriteOnly):
        raise OSError(target.errorString())
    if target.write(payload) != len(payload) or not target.commit():
        raise OSError(target.errorString())


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def require(condition):
    if not condition:
        raise ValueError("Données invalides ou version de fichier incompatible.")


def integer(v, low, high):
    return type(v) is int and low <= v <= high


def validate_chord(c):
    require(isinstance(c, dict) and isinstance(c.get("name"), str) and c["name"].strip())
    start = c["start"]
    require(integer(start, 1, 20))
    require(isinstance(c["frets"], list) and len(c["frets"]) == 6)
    require(all(integer(v, -1, 0) or integer(v, start, start + 4) for v in c["frets"]))
    require(isinstance(c["fingers"], list) and len(c["fingers"]) == 6
            and all(integer(v, 0, 4) for v in c["fingers"]))
    b = c["barre"]
    if b is not None:
        require(isinstance(b, list) and len(b) == 3 and integer(b[0], start, start + 4)
                and integer(b[1], 0, 4) and integer(b[2], b[1] + 1, 5))
        require(all(f >= b[0] for f in c["frets"][b[1]:b[2] + 1]))


def new_tab():
    return dict(tuning=DEFAULT_TUNING.copy(), per_line=4, spacing=16,
                cells=[[""] * 32 for _ in range(6)], bars=[8, 16, 24])


def validate_tab(t):
    require(len(t["tuning"]) == 6 and all(isinstance(s, str) and 0 < len(s) <= 5 for s in t["tuning"]))
    require(integer(t["per_line"], 1, 16) and integer(t["spacing"], 10, 40))
    rows = t["cells"]
    require(isinstance(rows, list) and len(rows) == 6 and 1 <= len(rows[0]) <= 512)
    n = len(rows[0])
    require(all(isinstance(r, list) and len(r) == n for r in rows))
    valid = {"", *TECH, *(str(i) for i in range(25))}
    require(all(v in valid for r in rows for v in r))
    require(isinstance(t["bars"], list) and all(integer(i, 1, n-1) for i in t["bars"]))
    require(t["bars"] == sorted(set(t["bars"])))


def validate_project(doc):
    require(isinstance(doc, dict) and doc.get("version") == 1)
    require(isinstance(doc["pages"], list) and doc["pages"])
    for page in doc["pages"]:
        require(isinstance(page, list))
        for item in page:
            x, y, w, h = (item[k] for k in ("x", "y", "w", "h"))
            require(all(type(v) in (float, int) and math.isfinite(v) for v in (x, y, w, h)))
            require(x >= 0 and y >= 0 and w >= 18 and h >= 18
                    and x+w <= WIDTH+0.00001 and y+h <= HEIGHT+0.00001)
            kind, data = item["kind"], item["data"]
            if kind == "chord":
                validate_chord(data)
            elif kind == "tab":
                validate_tab(data)
            else:
                require(kind == "text" and isinstance(data["text"], str)
                        and integer(data["size"], 8, 96))

