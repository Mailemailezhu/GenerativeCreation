"""左侧工具条：工具用图标竖排（悬停出名称与快捷键），底部是原图/对比/预览。

图标没有现成资源，全部用 QPainter 画：不引第三方图标库，打包也只多几百字节。
之所以不用 QToolBar：竖向工具栏只会按 sizeHint 给高度，底部那组对照按钮贴不到底。
"""
from PyQt5.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import QButtonGroup, QFrame, QPushButton, QVBoxLayout, QWidget

VIEWS = (("original", "原图", "只看原始图像"),
         ("split", "对比", "原图与预览并排，拖中间那条线改比例"),
         ("result", "预览", "只看生成结果"))


def _pen(q, color, w=1.7):
    p = QPen(QColor(color))
    p.setWidthF(w)
    p.setCapStyle(Qt.RoundCap)
    p.setJoinStyle(Qt.RoundJoin)
    q.setPen(p)
    q.setBrush(Qt.NoBrush)


def _draw(key, q, color):
    # 坐标按 24x24 画，_icon() 里再缩放到按钮尺寸
    _pen(q, color)
    if key == "brush":
        # 笔杆 + 金属箍 + 笔毛，三段拼出来才像画笔，单画一条斜线会变成斜杠
        p = QPen(QColor(color), 2.6)
        p.setCapStyle(Qt.RoundCap)
        q.setPen(p)
        q.drawLine(QPointF(17, 4), QPointF(11.6, 11.2))
        _pen(q, color)
        q.setBrush(QColor(color))
        ferrule = QPainterPath()
        ferrule.moveTo(QPointF(12.4, 9.6))
        ferrule.lineTo(QPointF(15.0, 12.2))
        ferrule.lineTo(QPointF(13.6, 13.8))
        ferrule.lineTo(QPointF(10.8, 11.2))
        ferrule.closeSubpath()
        q.drawPath(ferrule)
        bristle = QPainterPath()
        bristle.moveTo(QPointF(12.2, 11.6))
        bristle.lineTo(QPointF(6.0, 20.8))
        bristle.cubicTo(QPointF(9.0, 19.4), QPointF(12.6, 17.0), QPointF(14.4, 14.6))
        bristle.closeSubpath()
        q.drawPath(bristle)
        q.setBrush(Qt.NoBrush)
    elif key == "eraser":
        q.save()
        q.translate(12, 12)
        q.rotate(-38)
        q.drawRoundedRect(QRectF(-7.5, -3.6, 15, 7.2), 1.6, 1.6)
        q.drawLine(QPointF(0.6, -3.6), QPointF(0.6, 3.6))
        q.restore()
    elif key == "rect":
        p = QPen(QColor(color), 1.7, Qt.DashLine)
        p.setCapStyle(Qt.FlatCap)
        q.setPen(p)
        q.drawRect(QRectF(4.5, 5.5, 15, 13))
    elif key == "wand":
        q.drawLine(QPointF(5, 20), QPointF(13.5, 11.5))
        star = QPainterPath()
        star.moveTo(QPointF(17, 3.5))
        star.lineTo(QPointF(18.2, 7.4))
        star.lineTo(QPointF(22, 8.6))
        star.lineTo(QPointF(18.2, 9.8))
        star.lineTo(QPointF(17, 13.6))
        star.lineTo(QPointF(15.8, 9.8))
        star.lineTo(QPointF(12, 8.6))
        star.lineTo(QPointF(15.8, 7.4))
        star.closeSubpath()
        q.setBrush(QColor(color))
        q.drawPath(star)
        q.setBrush(Qt.NoBrush)
    elif key == "quick":
        # 套索：一个圈加一截甩出去的尾巴
        q.drawEllipse(QRectF(5, 5, 14, 11.5))
        tail = QPainterPath()
        tail.moveTo(QPointF(9.5, 16.5))
        tail.cubicTo(QPointF(8.5, 19.5), QPointF(11, 21), QPointF(13.5, 19.4))
        q.drawPath(tail)
    elif key == "hand":
        # 箭头指针（不是手掌）：H 在 PS 里也是移动画面
        arrow = QPainterPath()
        arrow.moveTo(QPointF(8, 3.5))
        arrow.lineTo(QPointF(8, 18.5))
        arrow.lineTo(QPointF(11.8, 14.8))
        arrow.lineTo(QPointF(14.6, 21))
        arrow.lineTo(QPointF(17.2, 19.8))
        arrow.lineTo(QPointF(14.4, 13.8))
        arrow.lineTo(QPointF(19, 13.4))
        arrow.closeSubpath()
        q.setBrush(QColor(color))
        q.drawPath(arrow)
        q.setBrush(Qt.NoBrush)
    elif key == "zoom":
        q.drawEllipse(QRectF(4.5, 4.5, 12, 12))
        q.drawLine(QPointF(15.6, 15.6), QPointF(20.5, 20.5))
        q.drawLine(QPointF(8, 10.5), QPointF(13, 10.5))
        q.drawLine(QPointF(10.5, 8), QPointF(10.5, 13))


def _icon(key, size=20):
    icon = QIcon()
    for color, state in (("#d6d6d6", QIcon.Off), ("#ffffff", QIcon.On)):
        pm = QPixmap(size * 2, size * 2)
        pm.fill(Qt.transparent)
        q = QPainter(pm)
        q.setRenderHint(QPainter.Antialiasing, True)
        q.scale(size * 2 / 24.0, size * 2 / 24.0)
        _draw(key, q, color)
        q.end()
        pm.setDevicePixelRatio(2)
        icon.addPixmap(pm, QIcon.Normal, state)
        icon.addPixmap(pm, QIcon.Active, state)
    return icon


class SideRail(QWidget):
    toolPicked = pyqtSignal(str)
    viewPicked = pyqtSignal(str)
    axisPicked = pyqtSignal()

    def __init__(self, tools, views=None, axis_tip="", parent=None):
        super().__init__(parent)
        self.setObjectName("rail")
        self.setFixedWidth(46)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 8, 4, 8)
        lay.setSpacing(6)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._tools = {}
        for key, name, tip in tools:
            b = QPushButton()
            b.setObjectName("tool")
            b.setCheckable(True)
            b.setFixedSize(34, 30)
            b.setIcon(_icon(key))
            b.setIconSize(QSize(20, 20))
            b.setAccessibleName(name)
            # 图标没有文字，名称和快捷键全靠悬停提示
            b.setToolTip("%s\n%s" % (name, tip))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self.toolPicked.emit(k))
            self._group.addButton(b)
            self._tools[key] = b
            lay.addWidget(b)
        lay.addStretch(1)

        line = QFrame()
        line.setObjectName("railLine")
        line.setFixedHeight(1)
        lay.addWidget(line)

        self._views = {}
        for mode, text, tip in (views or VIEWS):
            b = QPushButton(text)
            b.setObjectName("railseg")
            b.setCheckable(True)
            b.setFixedHeight(24)
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, m=mode: self._pick_view(m))
            self._views[mode] = b
            lay.addWidget(b)

        self.btn_axis = QPushButton("\u21c4")
        self.btn_axis.setObjectName("railseg")
        self.btn_axis.setFixedHeight(24)
        self.btn_axis.setToolTip(axis_tip or "切换分割线方向：\u21c4 左右拖动 / \u21c5 上下拖动")
        self.btn_axis.setCursor(Qt.PointingHandCursor)
        self.btn_axis.clicked.connect(lambda: self.axisPicked.emit())
        lay.addWidget(self.btn_axis)
        self.set_view_enabled(False)

    def set_tool(self, key):
        b = self._tools.get(key)
        if b is not None:
            b.setChecked(True)

    def set_view_enabled(self, on):
        for b in list(self._views.values()) + [self.btn_axis]:
            b.setEnabled(on)

    def sync_view(self, mode):
        for m, b in self._views.items():
            b.setChecked(m == mode)

    def set_axis(self, axis):
        self.btn_axis.setText("\u21c4" if axis == "v" else "\u21c5")

    def _pick_view(self, mode):
        # 再点一次已经选中的按钮 = 关掉对照，回到只编辑蒙版
        if self._views[mode].isChecked():
            self.sync_view(mode)
            self.viewPicked.emit(mode)
        else:
            self.sync_view("")
            self.viewPicked.emit("edit")