"""画布与蒙版：显示大图、缩放平移、画笔涂抹出可编辑区域。"""
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import (QImage, QPixmap, QPainter, QPainterPath, QPainterPathStroker,
                         QPen, QColor, QBrush)
from PyQt5.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsPathItem)

BRUSH_COLOR = QColor(255, 64, 64)
MASK_OPACITY = 0.55
MAX_UNDO = 20


class CanvasView(QGraphicsView):
    maskChanged = pyqtSignal()
    zoomChanged = pyqtSignal(float)
    cursorMoved = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.setResizeAnchor(QGraphicsView.NoAnchor)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setBackgroundBrush(QBrush(QColor("#1a1a1a")))
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self.image = None
        self.mask = None
        self.file_path = ""
        self._pix_item = None
        self._mask_item = None
        self._live_item = None
        self._live_path = None
        self._panning = False
        self._pan_from = None
        self._space_down = False
        self._undo = []
        self._redo = []

        self.zoom = 1.0
        self.brush_size = 45
        self.tool = "brush"
        self.mask_visible = True

    # ---------- 图像 ----------
    def load_image(self, path):
        img = QImage(path)
        if img.isNull():
            return False
        self.image = img.convertToFormat(QImage.Format_ARGB32)
        self.file_path = path
        self.mask = QImage(self.image.size(), QImage.Format_ARGB32)
        self.mask.fill(Qt.transparent)
        self._undo.clear()
        self._redo.clear()

        self.scene().clear()
        pix = self.scene().addPixmap(QPixmap.fromImage(self.image))
        pix.setZValue(0)
        self._mask_item = self.scene().addPixmap(QPixmap.fromImage(self.mask))
        self._mask_item.setZValue(10)
        self._mask_item.setOpacity(MASK_OPACITY)
        self.scene().setSceneRect(QRectF(self.image.rect()))
        self.fit_view()
        self.maskChanged.emit()
        return True

    def close_image(self):
        self.scene().clear()
        self.image = None
        self.mask = None
        self._pix_item = None
        self._mask_item = None
        self._undo.clear()
        self._redo.clear()

    def fit_view(self):
        if self.image is None:
            return
        self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)
        self.zoom = self.transform().m11()
        self.zoomChanged.emit(self.zoom)

    def zoom_to(self, z):
        if self.image is None:
            return
        self.resetTransform()
        self.scale(z, z)
        self.zoom = z
        self.zoomChanged.emit(self.zoom)

    # ---------- 蒙版 ----------
    def _refresh_mask_item(self):
        if self._mask_item is not None:
            self._mask_item.setPixmap(QPixmap.fromImage(self.mask))
            self._mask_item.setVisible(self.mask_visible)

    def set_mask_visible(self, on):
        self.mask_visible = on
        if self._mask_item is not None:
            self._mask_item.setVisible(on)

    def push_undo(self):
        if self.mask is None:
            return
        self._undo.append(self.mask.copy())
        if len(self._undo) > MAX_UNDO:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self):
        if not self._undo:
            return False
        self._redo.append(self.mask.copy())
        self.mask = self._undo.pop()
        self._refresh_mask_item()
        self.maskChanged.emit()
        return True

    def redo(self):
        if not self._redo:
            return False
        self._undo.append(self.mask.copy())
        self.mask = self._redo.pop()
        self._refresh_mask_item()
        self.maskChanged.emit()
        return True

    def clear_mask(self):
        if self.mask is None:
            return
        self.push_undo()
        self.mask.fill(Qt.transparent)
        self._refresh_mask_item()
        self.maskChanged.emit()

    def invert_mask(self):
        if self.mask is None:
            return
        self.push_undo()
        p = QPainter(self.mask)
        p.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        p.fillRect(self.mask.rect(), QColor(255, 255, 255))
        p.end()
        self._refresh_mask_item()
        self.maskChanged.emit()

    def mask_alpha(self):
        if self.mask is None:
            return None
        return self.mask.convertToFormat(QImage.Format_Alpha8)

    def mask_bounds(self):
        """蒙版非空区域的外接矩形（原图坐标），缩小 1/8 扫描以避免长时间等待。"""
        a = self.mask_alpha()
        if a is None:
            return None
        w, h = a.width(), a.height()
        sw, sh = max(1, w // 8), max(1, h // 8)
        small = a.scaled(sw, sh, Qt.IgnoreAspectRatio, Qt.FastTransformation)
        ptr = small.constBits()
        ptr.setsize(small.byteCount())
        data = bytes(ptr)
        bpl = small.bytesPerLine()
        minx, miny, maxx, maxy = sw, sh, -1, -1
        for y in range(sh):
            row = data[y * bpl: y * bpl + sw]
            nz = [i for i, v in enumerate(row) if v]
            if not nz:
                continue
            if y < miny:
                miny = y
            maxy = y
            if nz[0] < minx:
                minx = nz[0]
            if nz[-1] > maxx:
                maxx = nz[-1]
        if maxx < 0:
            return None
        rx = w / sw
        ry = h / sh
        return QRectF(minx * rx, miny * ry, (maxx - minx + 1) * rx, (maxy - miny + 1) * ry)

    def mask_ratio(self):
        b = self.mask_bounds()
        if b is None or self.image is None:
            return 0.0
        return (b.width() * b.height()) / float(self.image.width() * self.image.height())

    # ---------- 交互 ----------
    def wheelEvent(self, e):
        if self.image is None:
            return
        old = self.mapToScene(e.pos())
        factor = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        nz = self.zoom * factor
        if nz < 0.05 or nz > 10:
            return
        self.scale(factor, factor)
        self.zoom = nz
        delta = self.mapToScene(e.pos()) - old
        self.translate(delta.x(), delta.y())
        self.zoomChanged.emit(self.zoom)
        e.accept()

    def mousePressEvent(self, e):
        if self.image is None:
            return super().mousePressEvent(e)
        if e.button() == Qt.MiddleButton or (e.button() == Qt.LeftButton and self._space_down):
            self._panning = True
            self._pan_from = e.pos()
            self.setCursor(Qt.ClosedHandCursor)
            return
        if e.button() == Qt.LeftButton and self.tool in ("brush", "eraser"):
            self.push_undo()
            start = self.mapToScene(e.pos())
            self._live_path = QPainterPath(start)
            live_color = BRUSH_COLOR if self.tool == "brush" else QColor(230, 230, 230, 90)
            pen = QPen(live_color, self.brush_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            self._live_item = self.scene().addPath(self._live_path, pen)
            self._live_item.setZValue(20)
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        p = self.mapToScene(e.pos())
        self.cursorMoved.emit(int(p.x()), int(p.y()))
        if self._panning and self._pan_from is not None:
            d = e.pos() - self._pan_from
            self._pan_from = e.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - d.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - d.y())
            return
        if self._live_path is not None and self._live_item is not None:
            self._live_path.lineTo(p)
            self._live_item.setPath(self._live_path)
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._panning:
            self._panning = False
            self._pan_from = None
            self.setCursor(Qt.OpenHandCursor if self._space_down else Qt.ArrowCursor)
            return
        if self._live_path is not None:
            self._commit_stroke()
            return
        super().mouseReleaseEvent(e)

    def _commit_stroke(self):
        path = self._live_path
        self.scene().removeItem(self._live_item)
        self._live_item = None
        self._live_path = None

        stroker = QPainterPathStroker()
        stroker.setWidth(self.brush_size)
        stroker.setCapStyle(Qt.RoundCap)
        stroker.setJoinStyle(Qt.RoundJoin)
        outline = stroker.createStroke(path)

        p = QPainter(self.mask)
        p.setRenderHint(QPainter.Antialiasing)
        if self.tool == "eraser":
            p.setCompositionMode(QPainter.CompositionMode_Clear)
            p.fillPath(outline, Qt.black)
        else:
            p.fillPath(outline, BRUSH_COLOR)
        p.end()
        self._refresh_mask_item()
        self.maskChanged.emit()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Space and not e.isAutoRepeat():
            self._space_down = True
            if not self._panning:
                self.setCursor(Qt.OpenHandCursor)
            return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Space and not e.isAutoRepeat():
            self._space_down = False
            if not self._panning:
                self.setCursor(Qt.ArrowCursor)
            return
        super().keyReleaseEvent(e)
