"""Feuille A4 interactive. Les coordonnées de document restent indépendantes du zoom."""
from copy import deepcopy
from PySide6.QtCore import QPointF, QRectF, Qt, Signal, QMarginsF
from PySide6.QtGui import QColor, QPen, QPainter, QPageSize, QPageLayout, QPdfWriter
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsView, QMenu
from drawing import CHORD_H, CHORD_W, draw_object, font, line
from storage import WIDTH, HEIGHT

PAGE = QRectF(0, 0, WIDTH, HEIGHT)
ACCENT = QColor("#047c74")


class Block(QGraphicsItem):
    def __init__(self, record):
        super().__init__()
        self.kind = record["kind"]
        self.data = deepcopy(record["data"])
        self.w, self.h = record["w"], record["h"]
        x, y = record["x"], record["y"]
        if self.kind == "chord":
            # Inscrire les anciens diagrammes déformés dans leur cadre enregistré.
            self.w = max(18, min(self.w, self.h * CHORD_W / CHORD_H))
            self.h = self.w * CHORD_H / CHORD_W
            y = min(y, HEIGHT - self.h)
        self.setPos(x, y)
        self.corner = None
        self.setFlags(self.GraphicsItemFlag.ItemIsSelectable | self.GraphicsItemFlag.ItemIsMovable
                      | self.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

    def record(self):
        return dict(kind=self.kind, data=deepcopy(self.data), x=self.x(), y=self.y(), w=self.w, h=self.h)

    def boundingRect(self):
        return QRectF(-4, -4, self.w+8, self.h+8)

    def corners(self):
        return [(0,0), (self.w,0), (0,self.h), (self.w,self.h)]

    def hit_corner(self, pos):
        if self.isSelected():
            for index, (x,y) in enumerate(self.corners()):
                if abs(pos.x()-x) <= 5 and abs(pos.y()-y) <= 5:
                    return index
        return None

    def paint(self, p, option, widget):
        draw_object(p, self.kind, self.data, self.w, self.h)
        if self.isSelected():
            p.setPen(QPen(ACCENT, 1, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(0, 0, self.w, self.h))
            p.setPen(ACCENT)
            p.setBrush(Qt.GlobalColor.white)
            for x, y in self.corners():
                p.drawRect(QRectF(x-3, y-3, 6, 6))

    def itemChange(self, change, value):
        if change == self.GraphicsItemChange.ItemPositionChange and self.scene():
            x, y = value.x(), value.y()
            if self.scene().snap and self.corner is None:
                x, y = round(x/3)*3, round(y/3)*3
            return QPointF(min(max(0,x), WIDTH-self.w), min(max(0,y), HEIGHT-self.h))
        return super().itemChange(change, value)

    def hoverMoveEvent(self, event):
        index = self.hit_corner(event.pos())
        self.setCursor(Qt.CursorShape.SizeFDiagCursor if index in (0,3) else
                       Qt.CursorShape.SizeBDiagCursor if index in (1,2) else Qt.CursorShape.SizeAllCursor)

    def mousePressEvent(self, event):
        self.before = self.scene().records()
        self.corner = self.hit_corner(event.pos()) if event.button() == Qt.MouseButton.LeftButton else None
        if self.corner is None:
            super().mousePressEvent(event)
        else:
            self.original = QRectF(self.x(), self.y(), self.w, self.h)
            event.accept()

    def mouseMoveEvent(self, event):
        if self.corner is None:
            return super().mouseMoveEvent(event)
        r = self.original
        x, y = event.scenePos().x(), event.scenePos().y()
        if self.scene().snap:
            x, y = round(x/3)*3, round(y/3)*3
        left, top, right, bottom = r.left(), r.top(), r.right(), r.bottom()
        if self.kind == "chord":
            # Projeter le pointeur sur la diagonale issue du coin opposé fixe.
            sx = -1 if self.corner in (0, 2) else 1
            sy = -1 if self.corner in (0, 1) else 1
            ax = right if sx < 0 else left
            ay = bottom if sy < 0 else top
            ratio = CHORD_H / CHORD_W
            width = (sx * (x - ax) + ratio * sy * (y - ay)) / (1 + ratio**2)
            max_width = min(ax if sx < 0 else WIDTH - ax,
                            (ay if sy < 0 else HEIGHT - ay) / ratio)
            width = min(max_width, max(18, width))
            self.prepareGeometryChange()
            self.w, self.h = width, width * ratio
            self.setPos(ax - width if sx < 0 else ax, ay - self.h if sy < 0 else ay)
            self.update()
            return
        if self.corner in (0,2):
            left = min(max(0,x), right-18)
        else:
            right = max(left+18, min(WIDTH,x))
        if self.corner in (0,1):
            top = min(max(0,y), bottom-18)
        else:
            bottom = max(top+18, min(HEIGHT,y))
        self.prepareGeometryChange()
        self.w, self.h = right-left, bottom-top
        self.setPos(left, top)
        self.update()

    def mouseReleaseEvent(self, event):
        if self.corner is None:
            super().mouseReleaseEvent(event)
        self.corner = None
        if getattr(self, "before", None) != self.scene().records():
            self.scene().modified.emit()

    def mouseDoubleClickEvent(self, event):
        self.scene().edit.emit(self)
        event.accept()

    def contextMenuEvent(self, event):
        scene = self.scene()
        if not self.isSelected():
            scene.clearSelection()
            self.setSelected(True)
        menu = QMenu()
        for label, fn in [("Modifier…", lambda: scene.edit.emit(self)),
                          ("Dupliquer", scene.duplicate), ("Aligner à gauche", lambda: scene.align("left")),
                          ("Centrer horizontalement", lambda: scene.align("center")),
                          ("Aligner en haut", lambda: scene.align("top")), ("Supprimer", scene.delete)]:
            menu.addAction(label, fn)
        menu.exec(event.screenPos())


class Sheet(QGraphicsScene):
    modified = Signal()
    edit = Signal(object)

    def __init__(self, records=()):
        super().__init__()
        self.snap = False
        self.setSceneRect(-34,-34, WIDTH+68, HEIGHT+68)
        for r in records:
            self.addItem(Block(r))

    def records(self):
        return [b.record() for b in self.items(Qt.SortOrder.AscendingOrder)]

    def insert(self, kind, data, w, h):
        count = len(self.items())
        x = min(36+12*(count%5), WIDTH-w)
        y = min(36+36*(count%18), HEIGHT-h)
        self.clearSelection()
        b = Block(dict(kind=kind, data=data, w=w, h=h, x=x, y=y))
        self.addItem(b)
        b.setSelected(True)
        self.modified.emit()

    def duplicate(self):
        selection = [b for b in self.items(Qt.SortOrder.AscendingOrder) if b.isSelected()]
        self.clearSelection()
        for b in selection:
            copy = Block(b.record())
            self.addItem(copy)
            copy.setPos(b.pos()+QPointF(12,12))
            copy.setSelected(True)
        if selection:
            self.modified.emit()

    def delete(self):
        selection = self.selectedItems()
        for b in selection:
            self.removeItem(b)
        if selection:
            self.modified.emit()

    def align(self, mode):
        items = self.selectedItems()
        if not items:
            return
        box = PAGE
        if len(items) > 1:
            box = QRectF(items[0].x(), items[0].y(), items[0].w, items[0].h)
            for b in items[1:]:
                box = box.united(QRectF(b.x(), b.y(), b.w, b.h))
        snap, self.snap = self.snap, False
        for b in items:
            if mode == "top":
                b.setY(box.top())
            else:
                b.setX(box.left() if mode == "left" else box.center().x()-b.w/2)
        self.snap = snap
        self.modified.emit()

    def drawBackground(self, p, rect):
        p.fillRect(rect, QColor("#dae1df"))
        p.fillRect(PAGE.translated(3,4), QColor("#bac5c2"))
        p.fillRect(PAGE, Qt.GlobalColor.white)
        p.setPen(QPen(QColor("#677772"), 0.75))
        p.setFont(font(8))
        for length, horizontal in [(210, True), (297, False)]:
            for mm in range(0, length+1, 5):
                pos = mm*3
                tick = 7 if mm%10 == 0 else 3
                if horizontal:
                    line(p,pos,-1,pos,-1-tick)
                    if mm%20 == 0:
                        p.drawText(QPointF(pos-2,-11),str(mm))
                else:
                    line(p,-1,pos,-1-tick,pos)
                    if mm%20 == 0:
                        p.drawText(QPointF(-27,pos+3),str(mm))


class Canvas(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setDragMode(self.DragMode.RubberBandDrag)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.auto_fit = True

    def fit(self):
        self.auto_fit = True
        if self.scene():
            self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.auto_fit:
            self.fit()

    def zoom(self, factor):
        self.auto_fit = False
        if 0.15 <= self.transform().m11()*factor <= 8:
            self.scale(factor, factor)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom(1.15 if event.angleDelta().y() > 0 else 1/1.15)
            event.accept()
        else:
            super().wheelEvent(event)


def render_pdf(device, pages):
    """Écrit sur un QSaveFile ouvert. Aucune poignée ni règle dans le PDF."""
    writer = QPdfWriter(device)
    writer.setResolution(600)
    writer.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait,
                                     QMarginsF(0,0,0,0), QPageLayout.Unit.Millimeter))
    writer.setTitle("Partition de guitare")
    p = QPainter()
    if not p.begin(writer):
        raise OSError("Impossible de démarrer le rendu PDF.")
    try:
        for i, sheet in enumerate(pages):
            if i and not writer.newPage():
                raise OSError("Impossible de créer la page PDF.")
            p.save()
            p.scale(writer.width()/WIDTH, writer.height()/HEIGHT)
            for b in sheet.items(Qt.SortOrder.AscendingOrder):
                p.save()
                p.translate(b.pos())
                draw_object(p, b.kind, b.data, b.w, b.h)
                p.restore()
            p.restore()
    finally:
        p.end()

