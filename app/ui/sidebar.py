"""左侧工具条：工具按两列竖排，底部是原图/对比/预览。

之所以不用 QToolBar：竖向工具栏只会按 sizeHint 给高度，底部那组对照按钮贴不到底。
"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QButtonGroup, QFrame, QGridLayout, QPushButton, QVBoxLayout, QWidget

VIEWS = (("original", "原图", "只看原始图像"),
         ("split", "对比", "原图与预览并排，拖中间那条线改比例"),
         ("result", "预览", "只看生成结果"))


class SideRail(QWidget):
    toolPicked = pyqtSignal(str)
    viewPicked = pyqtSignal(str)
    axisPicked = pyqtSignal()

    def __init__(self, tools, parent=None):
        super().__init__(parent)
        self.setObjectName("rail")
        self.setFixedWidth(74)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(5, 8, 5, 8)
        lay.setSpacing(8)

        grid = QGridLayout()
        grid.setSpacing(4)
        grid.setContentsMargins(0, 0, 0, 0)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._tools = {}
        for i, (key, glyph, tip) in enumerate(tools):
            b = QPushButton(glyph)
            b.setObjectName("tool")
            b.setCheckable(True)
            b.setFixedSize(30, 28)
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self.toolPicked.emit(k))
            self._group.addButton(b)
            self._tools[key] = b
            grid.addWidget(b, i // 2, i % 2)
        lay.addLayout(grid)
        lay.addStretch(1)

        line = QFrame()
        line.setObjectName("railLine")
        line.setFixedHeight(1)
        lay.addWidget(line)

        self._views = {}
        for mode, text, tip in VIEWS:
            b = QPushButton(text)
            b.setObjectName("railseg")
            b.setCheckable(True)
            b.setFixedHeight(24)
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, m=mode: self._pick_view(m))
            self._views[mode] = b
            lay.addWidget(b)

        self.btn_axis = QPushButton("⇄")
        self.btn_axis.setObjectName("railseg")
        self.btn_axis.setFixedHeight(24)
        self.btn_axis.setToolTip("切换分割线方向：⇄ 左右拖动 / ⇅ 上下拖动")
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
        self.btn_axis.setText("⇄" if axis == "v" else "⇅")

    def _pick_view(self, mode):
        # 再点一次已经选中的按钮 = 关掉对照，回到只编辑蒙版
        if self._views[mode].isChecked():
            self.sync_view(mode)
            self.viewPicked.emit(mode)
        else:
            self.sync_view("")
            self.viewPicked.emit("edit")
