"""Rendu vectoriel partagé entre la scène, le PDF et les aperçus."""
from PySide6.QtCore import Qt, QRectF, QPointF, QLineF
from PySide6.QtGui import QColor, QFont, QPen

CENTER = Qt.AlignmentFlag.AlignCenter
INK = QColor("#172525")
LEFT, TOP, DX, DY = 24, 39, 15, 15
CHORD_W, CHORD_H = 122, 124


def font(px, bold=False):
    f = QFont("Segoe UI")
    f.setPixelSize(max(1, round(px)))
    f.setBold(bold)
    return f


def line(p, x, y, xx, yy):
    p.drawLine(QLineF(x, y, xx, yy))


def chord(p, c):
    p.save()
    p.setPen(INK)
    p.setFont(font(14, True))
    title = QRectF(1, 0, CHORD_W-2, 22)
    label = c["name"]
    if p.fontMetrics().horizontalAdvance(label) > title.width():
        p.setFont(font(14 * title.width() / p.fontMetrics().horizontalAdvance(label), True))
    p.drawText(title, CENTER, label)
    p.setFont(font(10))
    for i in range(6):
        x = LEFT + DX*i
        line(p, x, TOP, x, TOP+5*DY)
        fret = c["frets"][i]
        if fret <= 0:
            p.drawText(QRectF(x-7, TOP-17, 14, 15), CENTER, "×" if fret < 0 else "○")
    for i in range(6):
        y = TOP + i*DY
        p.setPen(QPen(INK, 2.6 if i == 0 and c["start"] == 1 else 0.9))
        line(p, LEFT, y, LEFT+5*DX, y)
    if c["start"] > 1:
        p.drawText(QRectF(0, TOP, LEFT-3, DY), CENTER, str(c["start"]))
    if c["barre"]:
        fret, a, b = c["barre"]
        y = TOP+(fret-c["start"]+0.5)*DY
        p.setPen(QPen(INK, 9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        line(p, LEFT+a*DX, y, LEFT+b*DX, y)
    for i, fret in enumerate(c["frets"]):
        if fret <= 0:
            continue
        x, y = LEFT+i*DX, TOP+(fret-c["start"]+0.5)*DY
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(INK)
        p.drawEllipse(QPointF(x, y), 5, 5)
        if c["fingers"][i]:
            p.setPen(Qt.GlobalColor.white)
            p.setFont(font(8, True))
            p.drawText(QRectF(x-5, y-5, 10, 10), CENTER, str(c["fingers"][i]))
    p.restore()


def systems(t):
    bounds = [0, *t["bars"], len(t["cells"][0])]
    step = t["per_line"]
    return [(bounds[i], bounds[min(i+step, len(bounds)-1)])
            for i in range(0, len(bounds)-1, step)]


def tab_size(t):
    runs = systems(t)
    return 42 + max(b-a for a, b in runs)*t["spacing"], len(runs)*86


def tablature(p, t, w, h):
    runs = systems(t)
    natural_w, natural_h = tab_size(t)
    # Une ligne courte garde son espacement musical, même dans un bloc large.
    p.scale(w/max(540, natural_w), h/natural_h)
    step = t["spacing"]
    p.setFont(font(10))
    for system, (a, b) in enumerate(runs):
        top = system*86+12
        right = 32+(b-a)*step
        p.setPen(QPen(INK, 0.85))
        for j in [a, *(k for k in t["bars"] if a < k < b), b]:
            x = 32+(j-a)*step
            line(p, x, top, x, top+55)
        for row, tuning in enumerate(t["tuning"]):
            y = top+row*11
            p.setPen(QPen(INK, 0.8))
            p.drawText(QRectF(0, y-7, 30, 14), CENTER, tuning)
            line(p, 32, y, right, y)
            for col in range(a, b):
                value = t["cells"][row][col]
                if value:
                    x = 32+(col-a+0.5)*step
                    rw = p.fontMetrics().horizontalAdvance(value)+2
                    r = QRectF(x-rw/2, y-5.5, rw, 11)
                    p.fillRect(r, Qt.GlobalColor.white)
                    p.drawText(r, CENTER, value)


def draw_object(p, kind, data, w, h):
    p.save()
    p.setClipRect(QRectF(0, 0, w, h), Qt.ClipOperation.IntersectClip)
    p.setPen(INK)
    if kind == "chord":
        p.scale(w/CHORD_W, h/CHORD_H)
        chord(p, data)
    elif kind == "tab":
        tablature(p, data, w, h)
    else:
        p.setFont(font(data["size"]))
        p.drawText(QRectF(1, 0, w-2, h),
                   Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, data["text"])
    p.restore()

