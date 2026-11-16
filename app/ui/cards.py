"""右侧面板的卡片控件：原始图像卡、素材缩略图、末尾的"+"按钮。"""
import os

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QLabel, QSizePolicy,
                             QVBoxLayout, QWidget)

from core.hints import load as _load_hints

from .flow_layout import FlowLayout

UI = _load_hints()["ui"]

THUMB = 76


def _cover(path, size):
    pix = QPixmap(path)
    if pix.isNull():
        return pix
    return pix.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)


class PlusTile(QFrame):
    """半透明方块 + 居中加号；永远排在缩略图末尾。"""
    clicked = pyqtSignal()

    def __init__(self, parent=None, size=THUMB):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(UI["asset_plus"])
        # 和「原始图」卡片保持同一套底色/描边，两个区块才不会像两套风格
        self._hover = False

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        on = self.isEnabled()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 32 if self._hover else (18 if on else 8)))
        p.drawRoundedRect(r, 8, 8)
        pen = QPen(QColor(90, 90, 90) if self._hover else QColor(63, 63, 63))
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, 8, 8)
        pen.setColor(QColor(255, 255, 255, 110 if on else 50))
        pen.setWidth(2)
        p.setPen(pen)
        c = r.center()
        arm = r.width() // 6
        p.drawLine(c.x() - arm, c.y(), c.x() + arm, c.y())
        p.drawLine(c.x(), c.y() - arm, c.x(), c.y() + arm)


class ThumbTile(QFrame):
    removed = pyqtSignal(str)

    def __init__(self, path, parent=None, size=THUMB):
        super().__init__(parent)
        self.path = path
        self._size = size
        self._pix = _cover(path, size)
        self._hover = False
        self.setFixedSize(size, size)
        self.setToolTip(UI["asset_remove"].format(name=os.path.basename(path)))

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.removed.emit(self.path)
        super().mouseReleaseEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        clip = QPainterPath()
        clip.addRoundedRect(1, 1, r.width(), r.height(), 8, 8)
        p.setClipPath(clip)
        if not self._pix.isNull():
            p.drawPixmap(0, 0, self._pix)
        else:
            p.fillRect(self.rect(), QColor(60, 60, 60))
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 55)))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, 8, 8)
        if self._hover:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 130))
            p.drawRoundedRect(r, 8, 8)
            p.setBrush(QColor(226, 74, 74))
            p.drawEllipse(self._size - 24, 4, 20, 20)
            p.setPen(QPen(QColor(255, 255, 255), 2))
            cx, cy = self._size - 14, 14
            p.drawLine(cx - 4, cy - 4, cx + 4, cy + 4)
            p.drawLine(cx + 4, cy - 4, cx - 4, cy + 4)


class AssetStrip(QWidget):
    """素材图区：多选、可移除、末尾一直是"+"。"""
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._paths = []
        self._flow = FlowLayout(self, margin=0, hgap=8, vgap=8)
        self._plus = PlusTile()
        self._plus.clicked.connect(self.pick)
        self._flow.addWidget(self._plus)
        # 流式布局靠 heightForWidth 撑高，sizePolicy 不打开这个开关就只会占一行
        policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

    def paths(self):
        return list(self._paths)

    def pick(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择素材图", "", "图像 (*.png *.jpg *.jpeg *.webp *.tif *.tiff)")
        for f in files:
            self.add(f)

    def add(self, path):
        if path in self._paths or not os.path.isfile(path):
            return
        self._flow.removeWidget(self._plus)
        tile = ThumbTile(path)
        tile.removed.connect(self.remove)
        self._flow.addWidget(tile)
        self._flow.addWidget(self._plus)
        self._paths.append(path)
        self._relayout()

    def remove(self, path):
        if path not in self._paths:
            return
        for i in range(self._flow.count()):
            w = self._flow.itemAt(i).widget()
            if isinstance(w, ThumbTile) and w.path == path:
                self._flow.removeWidget(w)
                w.setParent(None)
                w.deleteLater()
                break
        self._paths.remove(path)
        self._relayout()

    def clear(self):
        for path in list(self._paths):
            self.remove(path)

    def _relayout(self):
        # 不能 adjustSize()：那会把宽度钉死在 sizeHint（一个格子的宽），缩略图就永远单列
        self.updateGeometry()
        self.update()
        self.changed.emit()


class SourceCard(QFrame):
    """原始图像卡：和素材缩略图同一套观感，整张卡可以直接点开选图。"""
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("srcCard")
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(UI["asset_hint"])
        self.setFixedHeight(92)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(12)
        self.thumb = QLabel("＋")
        self.thumb.setObjectName("srcThumb")
        self.thumb.setFixedSize(76, 76)
        self.thumb.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.thumb)
        col = QVBoxLayout()
        col.setSpacing(3)
        self.name = QLabel("点击选择原始图")
        self.name.setObjectName("srcName")
        self.meta = QLabel("或从 LrC 用「编辑于」打开")
        self.meta.setObjectName("srcMeta")
        self.meta.setWordWrap(True)
        col.addStretch(1)
        col.addWidget(self.name)
        col.addWidget(self.meta)
        col.addStretch(1)
        lay.addLayout(col, 1)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def set_image(self, path, width=None, height=None, label=None):
        self.thumb.setPixmap(_cover(path, 76))
        # label 用来显示 LrC 那边的原文件名，path 可能是缓存 PNG
        self.name.setText(label or os.path.basename(path))
        self.meta.setText("%d × %d px" % (width, height) if width else "")
