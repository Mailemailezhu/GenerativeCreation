"""画布与蒙版：显示大图、缩放平移、多种选区工具、原图与结果对比。"""
import numpy as np
from PIL import Image, ImageFilter
from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import (QBrush, QColor, QImage, QPainter, QPainterPath,
                         QPainterPathStroker, QPen, QPixmap)
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsView

BRUSH_COLOR = QColor(255, 64, 64)
MASK_OPACITY = 0.55
MAX_UNDO = 20
SPLIT_HIT = 7          # 屏幕上离分割线几像素算抓住它


def _flood(sel, x, y):
    # Pillow 的 ImageDraw.floodfill 对 0/255 的 L 图实测一个像素都不改，所以自己写扫描线填充
    h, w = sel.shape
    out = np.zeros((h, w), bool)
    if not sel[y, x]:
        return out
    stack = [(x, y)]
    while stack:
        cx, cy = stack.pop()
        if not sel[cy, cx] or out[cy, cx]:
            continue
        row, orow = sel[cy], out[cy]
        left = cx
        while left > 0 and row[left - 1] and not orow[left - 1]:
            left -= 1
        right = cx
        while right < w - 1 and row[right + 1] and not orow[right + 1]:
            right += 1
        orow[left:right + 1] = True
        for ny in (cy - 1, cy + 1):
            if not (0 <= ny < h):
                continue
            seg = sel[ny, left:right + 1] & ~out[ny, left:right + 1]
            if not seg.any():
                continue
            pad = np.concatenate(([0], seg.astype(np.int8), [0]))
            for k in np.flatnonzero(np.diff(pad) == 1):
                stack.append((left + int(k), ny))
    return out


class SplitPixmapItem(QGraphicsItem):
    # QGraphicsPixmapItem 没有 setClipPath，对比视图需要自己按矩形裁剪后再画
    def __init__(self):
        super().__init__()
        self._pix = None
        self._clip = None

    def set_pixmap(self, pix):
        self.prepareGeometryChange()
        self._pix = pix
        self.update()

    def set_clip_rect(self, rect):
        self._clip = rect
        self.update()

    def boundingRect(self):
        if self._pix is None:
            return QRectF()
        return QRectF(0, 0, self._pix.width(), self._pix.height())

    def paint(self, p, opt, widget=None):
        if self._pix is None:
            return
        p.setClipRect(self._clip if self._clip is not None else self.boundingRect())
        p.drawPixmap(0, 0, self._pix)


class CanvasView(QGraphicsView):
    maskChanged = pyqtSignal()
    zoomChanged = pyqtSignal(float)
    cursorMoved = pyqtSignal(int, int)
    viewChanged = pyqtSignal(str)

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
        self.result_img = None
        self._pix_item = None
        self._result_item = None
        self._split_line = None
        self._mask_item = None
        self._live_item = None
        self._live_path = None
        self._rect_item = None
        self._rect_start = None
        self._panning = False
        self._pan_from = None
        self._space_down = False
        self._split_drag = False
        self._undo = []
        self._redo = []
        self._cursor_scene = None
        self._arr = None
        self._qs_seed = None
        self._qs_layer = None
        self._qs_base = None

        self.zoom = 1.0
        self.brush_size = 45
        self.hardness = 80        # 0 = 全是柔边，100 = 硬边
        self.opacity = 100        # 单笔最大浓度
        self.tolerance = 32       # 魔棒 / 快速选择的颜色容差
        self.brush_mode = "add"   # add / subtract
        self.tool = "brush"
        self.mask_visible = True
        self.view_mode = "edit"   # edit / split / original / result
        self.split_ratio = 0.5
        self.split_axis = "v"     # v = 竖线左右拖，h = 横线上下拖

    # ---------- 图像 ----------
    def load_image(self, path):
        img = QImage(path)
        if img.isNull():
            return False
        self.image = img.convertToFormat(QImage.Format_ARGB32)
        self.file_path = path
        self._arr = None
        self.result_img = None
        self.view_mode = "edit"
        self.mask = QImage(self.image.size(), QImage.Format_ARGB32)
        self.mask.fill(Qt.transparent)
        self._undo.clear()
        self._redo.clear()

        self.scene().clear()
        self._split_line = None
        self._result_item = None
        self._mask_item = None
        self._live_item = None
        self._rect_item = None
        self._live_path = None
        self._pix_item = self.scene().addPixmap(QPixmap.fromImage(self.image))
        self._pix_item.setZValue(0)
        self._mask_item = self.scene().addPixmap(QPixmap.fromImage(self.mask))
        self._mask_item.setZValue(10)
        self._mask_item.setOpacity(MASK_OPACITY)
        self._split_line = self.scene().addLine(0, 0, 0, 0)
        pen = QPen(QColor(255, 255, 255, 200), 1.4)
        pen.setCosmetic(True)
        self._split_line.setPen(pen)
        self._split_line.setZValue(30)
        self._split_line.setVisible(False)
        self.scene().setSceneRect(QRectF(self.image.rect()))
        self.fit_view()
        self.maskChanged.emit()
        self.viewChanged.emit("edit")
        return True

    def close_image(self):
        self.scene().clear()
        self.image = None
        self.mask = None
        self.result_img = None
        self._pix_item = None
        self._result_item = None
        self._split_line = None
        self._mask_item = None
        self._arr = None
        self.view_mode = "edit"
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

    def zoom_at(self, pos, factor):
        """以鼠标位置为中心缩放。"""
        if self.image is None:
            return
        nz = self.zoom * factor
        if nz < 0.05 or nz > 10:
            return
        old = self.mapToScene(pos)
        self.scale(factor, factor)
        self.zoom = nz
        delta = self.mapToScene(pos) - old
        self.translate(delta.x(), delta.y())
        self.zoomChanged.emit(self.zoom)

    # ---------- 原图 / 结果对比 ----------
    def set_result(self, path):
        """贴一张结果图到画布顶部，切到对比视图（对齐 LrC 的参考视图）。"""
        if self.image is None:
            return False
        img = QImage(path)
        if img.isNull():
            return False
        if img.size() != self.image.size():
            img = img.scaled(self.image.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self.result_img = img.convertToFormat(QImage.Format_ARGB32)
        if self._result_item is None:
            self._result_item = SplitPixmapItem()
            self.scene().addItem(self._result_item)
            self._result_item.setZValue(5)
        self._result_item.set_pixmap(QPixmap.fromImage(self.result_img))
        self.set_view_mode("split")
        return True

    def clear_result(self):
        if self._result_item is not None:
            self.scene().removeItem(self._result_item)
            self._result_item = None
        self.result_img = None
        self.set_view_mode("edit")

    def has_result(self):
        return self._result_item is not None

    def set_view_mode(self, mode):
        self.view_mode = mode if self.has_result() else "edit"
        self._apply_view()
        self.viewChanged.emit(self.view_mode)

    def set_split_axis(self, axis):
        self.split_axis = axis
        self._apply_view()

    def _apply_view(self):
        if self.image is None or self._pix_item is None:
            return
        mode = self.view_mode
        if not self.has_result():
            self._pix_item.setVisible(True)
            if self._split_line is not None:
                self._split_line.setVisible(False)
            return
        r = self.image.rect()
        self._pix_item.setVisible(mode != "result")
        self._result_item.setVisible(mode in ("split", "result"))
        # 对照时把红色蒙版收起来，不然挡住要看的结果
        if self._mask_item is not None:
            self._mask_item.setVisible(self.mask_visible and mode == "edit")
        if mode != "split" or self._split_line is None:
            self._result_item.set_clip_rect(None)
            if self._split_line is not None:
                self._split_line.setVisible(False)
            return
        if self.split_axis == "v":
            x = r.width() * self.split_ratio
            clip = QRectF(x, 0, r.width() - x, r.height())
            self._split_line.setLine(x, 0, x, r.height())
        else:
            y = r.height() * self.split_ratio
            clip = QRectF(0, y, r.width(), r.height() - y)
            self._split_line.setLine(0, y, r.width(), y)
        self._result_item.set_clip_rect(clip)
        self._split_line.setVisible(True)

    def _near_split(self, pos):
        if not self.has_result() or self.view_mode != "split" or self.image is None:
            return False
        if self.split_axis == "v":
            x = self.mapFromScene(QPointF(self.image.width() * self.split_ratio, 0)).x()
            return abs(x - pos.x()) <= SPLIT_HIT
        y = self.mapFromScene(QPointF(0, self.image.height() * self.split_ratio)).y()
        return abs(y - pos.y()) <= SPLIT_HIT

    def _drag_split(self, pos):
        sc = self.mapToScene(pos)
        if self.split_axis == "v":
            self.split_ratio = max(0.0, min(1.0, sc.x() / float(self.image.width())))
        else:
            self.split_ratio = max(0.0, min(1.0, sc.y() / float(self.image.height())))
        self._apply_view()

    # ---------- 蒙版数据 ----------
    def _alpha_of(self, img):
        a = img.convertToFormat(QImage.Format_Alpha8)
        buf = a.constBits()
        buf.setsize(a.byteCount())
        arr = np.frombuffer(bytes(buf), np.uint8).reshape(a.height(), a.bytesPerLine())
        return arr[:, :a.width()].copy()

    def _mask_from_alpha(self, arr):
        h, w = arr.shape
        buf = np.zeros((h, w, 4), np.uint8)
        buf[..., 0] = BRUSH_COLOR.blue()
        buf[..., 1] = BRUSH_COLOR.green()
        buf[..., 2] = BRUSH_COLOR.red()
        buf[..., 3] = arr
        return QImage(buf.tobytes(), w, h, w * 4, QImage.Format_ARGB32).copy()

    def _refresh_mask_item(self):
        if self._mask_item is not None:
            self._mask_item.setPixmap(QPixmap.fromImage(self.mask))
            self._mask_item.setVisible(self.mask_visible)

    def set_mask_visible(self, on):
        self.mask_visible = on
        if self._mask_item is not None:
            self._mask_item.setVisible(on)

    def _img_array(self):
        """整图 RGB uint8，魔棒与快速选择按颜色工作时用；换图后失效。"""
        if self._arr is None and self.image is not None:
            img = self.image.convertToFormat(QImage.Format_RGB888)
            w, h = img.width(), img.height()
            buf = img.constBits()
            buf.setsize(img.byteCount())
            a = np.frombuffer(bytes(buf), np.uint8)
            a = a.reshape(h, img.bytesPerLine())[:, :w * 3].reshape(h, w, 3)
            self._arr = a.copy()
        return self._arr

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

    def apply_feather(self, px):
        """对整张蒙版做羽化（PS 的「选择 → 修改 → 羽化」）。"""
        if self.mask is None or px <= 0:
            return False
        self.push_undo()
        a = self._alpha_of(self.mask)
        a = np.asarray(Image.fromarray(a, "L").filter(ImageFilter.GaussianBlur(px)), np.uint8)
        self.mask = self._mask_from_alpha(a)
        self._refresh_mask_item()
        self.maskChanged.emit()
        return True

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
            nz = [i for i, v in enumerate(row) if v > 12]
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
        rx = w / float(sw)
        ry = h / float(sh)
        return QRectF(minx * rx, miny * ry, (maxx - minx + 1) * rx, (maxy - miny + 1) * ry)

    def mask_ratio(self):
        b = self.mask_bounds()
        if b is None or self.image is None:
            return 0.0
        return (b.width() * b.height()) / float(self.image.width() * self.image.height())

    # ---------- 选区工具 ----------
    def _combine(self, sel, subtract):
        cur = self._alpha_of(self.mask).astype(np.float32) / 255.0
        s = sel.astype(np.float32)
        if subtract:
            cur = cur * (1.0 - s)
        else:
            cur = np.maximum(cur, s)
        self.mask = self._mask_from_alpha((cur * 255).clip(0, 255).astype(np.uint8))
        self._refresh_mask_item()
        self.maskChanged.emit()

    def _wand_region(self, x, y):
        """魔棒：从点击处按颜色容差做连续区域填充。"""
        arr = self._img_array()
        if arr is None:
            return None
        h, w = arr.shape[:2]
        if not (0 <= x < w and 0 <= y < h):
            return None
        seed = arr[y, x].astype(np.int16)
        sel = np.abs(arr.astype(np.int16) - seed).max(axis=2) <= self.tolerance
        if not sel[y, x]:
            return None
        return _flood(sel, x, y)

    def _qs_stamp(self, layer, x, y):
        arr = self._img_array()
        if arr is None or self._qs_seed is None:
            return False
        h, w = arr.shape[:2]
        r = max(1, int(self.brush_size / 2.0))
        x0, x1 = max(0, x - r), min(w, x + r + 1)
        y0, y1 = max(0, y - r), min(h, y + r + 1)
        if x1 <= x0 or y1 <= y0:
            return False
        yy, xx = np.ogrid[y0:y1, x0:x1]
        circle = (xx - x) ** 2 + (yy - y) ** 2 <= r * r
        sub = arr[y0:y1, x0:x1].astype(np.int16)
        sim = np.abs(sub - self._qs_seed).max(axis=2) <= self.tolerance
        hit = circle & sim
        if not hit.any():
            return False
        layer[y0:y1, x0:x1] = np.maximum(layer[y0:y1, x0:x1],
                                        (hit * 255).astype(np.uint8))
        return True

    def _qs_paint(self):
        cur = self._alpha_of(self.mask).astype(np.float32) / 255.0
        lay = self._qs_layer.astype(np.float32) / 255.0
        if self.brush_mode == "subtract":
            cur = cur * (1.0 - lay)
        else:
            cur = np.maximum(cur, lay)
        self.mask = self._mask_from_alpha((cur * 255).clip(0, 255).astype(np.uint8))
        self._refresh_mask_item()

    # ---------- 交互 ----------
    def wheelEvent(self, e):
        if self.image is None:
            return
        self.zoom_at(e.pos(), 1.15 if e.angleDelta().y() > 0 else 1 / 1.15)
        e.accept()

    def mousePressEvent(self, e):
        if self.image is None:
            return super().mousePressEvent(e)
        if e.button() == Qt.LeftButton and self._near_split(e.pos()):
            self._split_drag = True
            self.setCursor(Qt.SplitHCursor if self.split_axis == "v" else Qt.SplitVCursor)
            return
        if e.button() == Qt.MiddleButton or (e.button() == Qt.LeftButton and self._space_down) \
                or (e.button() == Qt.LeftButton and self.tool == "hand"):
            self._panning = True
            self._pan_from = e.pos()
            self.setCursor(Qt.ClosedHandCursor)
            return
        if e.button() == Qt.LeftButton and self.tool == "zoom":
            self.zoom_at(e.pos(), 1.25 if not (e.modifiers() & Qt.AltModifier) else 1 / 1.25)
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
        if e.button() == Qt.LeftButton and self.tool == "wand":
            p = self.mapToScene(e.pos())
            reg = self._wand_region(int(p.x()), int(p.y()))
            if reg is None:
                return
            self.push_undo()
            self._combine(reg, self.brush_mode == "subtract")
            return
        if e.button() == Qt.LeftButton and self.tool == "quick":
            arr = self._img_array()
            p = self.mapToScene(e.pos())
            x, y = int(p.x()), int(p.y())
            if arr is None or not (0 <= x < arr.shape[1] and 0 <= y < arr.shape[0]):
                return
            self.push_undo()
            self._qs_seed = arr[y, x].astype(np.int16)
            self._qs_layer = np.zeros(arr.shape[:2], np.uint8)
            if self._qs_stamp(self._qs_layer, x, y):
                self._qs_paint()
            return
        if e.button() == Qt.LeftButton and self.tool == "rect":
            self._rect_start = self.mapToScene(e.pos())
            self._rect_item = self.scene().addRect(QRectF(self._rect_start, self._rect_start))
            pen = QPen(QColor(255, 255, 255, 220), 1.2, Qt.DashLine)
            pen.setCosmetic(True)
            self._rect_item.setPen(pen)
            self._rect_item.setZValue(20)
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        p = self.mapToScene(e.pos())
        self._cursor_scene = p
        self.cursorMoved.emit(int(p.x()), int(p.y()))
        if self._split_drag:
            self._drag_split(e.pos())
            return
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
        if self.tool == "rect" and self._rect_item is not None and self._rect_start is not None:
            self._rect_item.setRect(QRectF(self._rect_start, p).normalized())
            return
        if self.tool == "quick" and self._qs_layer is not None:
            if self._qs_stamp(self._qs_layer, int(p.x()), int(p.y())):
                self._qs_paint()
            self.viewport().update()
            return
        if self.tool in ("brush", "eraser", "quick", "wand"):
            self.viewport().update()
            return
        super().mouseMoveEvent(e)

    def leaveEvent(self, e):
        self._cursor_scene = None
        self.viewport().update()
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._split_drag:
            self._split_drag = False
            self.setCursor(Qt.ArrowCursor)
            return
        if self._panning:
            self._panning = False
            self._pan_from = None
            self.setCursor(Qt.OpenHandCursor if self.tool == "hand" or self._space_down
                           else Qt.ArrowCursor)
            return
        if self._live_path is not None:
            self._commit_stroke()
            return
        if self.tool == "rect" and self._rect_start is not None:
            r = self._rect_item.rect()
            self.scene().removeItem(self._rect_item)
            self._rect_item = None
            self._rect_start = None
            if r.width() >= 1 and r.height() >= 1:
                self.push_undo()
                sel = np.zeros((self.image.height(), self.image.width()), np.uint8)
                x0 = max(0, int(r.left()))
                y0 = max(0, int(r.top()))
                x1 = min(self.image.width(), int(r.right()) + 1)
                y1 = min(self.image.height(), int(r.bottom()) + 1)
                if x1 > x0 and y1 > y0:
                    sel[y0:y1, x0:x1] = 255
                    self._combine(sel > 0, self.brush_mode == "subtract")
            return
        if self.tool == "quick" and self._qs_layer is not None:
            self._qs_layer = None
            self._qs_seed = None
            self.maskChanged.emit()
            return
        super().mouseReleaseEvent(e)

    def _commit_stroke(self):
        """一笔落定：先画到透明层，再按硬度做柔化，最后与蒙版做 max / 减法合成。"""
        path = self._live_path
        self.scene().removeItem(self._live_item)
        self._live_item = None
        self._live_path = None

        stroker = QPainterPathStroker()
        stroker.setWidth(max(1.0, float(self.brush_size)))
        stroker.setCapStyle(Qt.RoundCap)
        stroker.setJoinStyle(Qt.RoundJoin)
        outline = stroker.createStroke(path)

        layer = QImage(self.mask.size(), QImage.Format_ARGB32)
        layer.fill(Qt.transparent)
        p = QPainter(layer)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillPath(outline, Qt.white)
        p.end()

        src = self._alpha_of(layer).astype(np.float32) / 255.0
        soft = self.brush_size * 0.5 * (1.0 - self.hardness / 100.0)
        if soft >= 0.6:
            blurred = Image.fromarray((src * 255).astype(np.uint8), "L")
            src = np.asarray(blurred.filter(ImageFilter.GaussianBlur(soft)), np.float32) / 255.0

        cur = self._alpha_of(self.mask).astype(np.float32) / 255.0
        op = max(0.0, min(1.0, self.opacity / 100.0))
        if self.tool == "eraser" or self.brush_mode == "subtract":
            cur = cur * (1.0 - src * op)
        else:
            cur = np.maximum(cur, src * op)
        self.mask = self._mask_from_alpha((cur * 255).clip(0, 255).astype(np.uint8))
        self._refresh_mask_item()
        self.maskChanged.emit()

    def drawForeground(self, p, rect):
        super().drawForeground(p, rect)
        if self.image is None:
            return
        if self.tool in ("brush", "eraser", "quick") and self._cursor_scene is not None:
            r = self.brush_size / 2.0
            pen = QPen(QColor(255, 255, 255, 210), 1)
            pen.setCosmetic(True)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(self._cursor_scene, r, r)
            if self.hardness < 100:
                inner = r * max(0.0, self.hardness / 100.0)
                if inner > 1.5:
                    pen2 = QPen(QColor(255, 255, 255, 110), 1)
                    pen2.setCosmetic(True)
                    p.setPen(pen2)
                    p.drawEllipse(self._cursor_scene, inner, inner)
        if self.view_mode == "split" and self.has_result() and not self._split_drag:
            self._draw_split_grip(p)

    def _draw_split_grip(self, p):
        """分割线中间画个小圆把手，提示可以拖。"""
        c = self.viewport().rect().center()
        cc = self.mapToScene(c)
        if self.split_axis == "v":
            pt = QPointF(self.image.width() * self.split_ratio, cc.y())
        else:
            pt = QPointF(cc.x(), self.image.height() * self.split_ratio)
        pos = self.mapFromScene(pt)
        p.save()
        p.resetTransform()
        p.setPen(QPen(QColor(255, 255, 255, 230), 1.5))
        p.setBrush(QColor(45, 140, 235, 235))
        p.drawEllipse(QPointF(pos), 7, 7)
        p.setBrush(Qt.NoBrush)
        p.drawLine(pos.x() - 3, pos.y(), pos.x() + 3, pos.y()) if self.split_axis == "v" \
            else p.drawLine(pos.x(), pos.y() - 3, pos.x(), pos.y() + 3)
        p.restore()

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
                self.setCursor(Qt.OpenHandCursor if self.tool == "hand" else Qt.ArrowCursor)
            return
        super().keyReleaseEvent(e)
