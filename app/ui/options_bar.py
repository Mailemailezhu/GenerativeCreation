"""顶部参数栏。

不用 QToolBar：它按每个控件的 sizeHint 排布，滑块的固定像素长度不会跟着窗口变，
换个界面缩放就变成文字挤在一起、滑块却不动。这里用普通 QWidget + 水平布局，
滑块设成 Expanding，多余宽度按组分配。
"""
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QWidget


class OptionsBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("optionsBar")
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(8, 5, 8, 5)
        self._lay.setSpacing(10)

    def add_widget(self, w, stretch=0):
        self._lay.addWidget(w, stretch)
        return w

    def add_sep(self):
        f = QFrame()
        f.setObjectName("vline")
        f.setFixedWidth(1)
        self._lay.addWidget(f)

    def finish(self):
        self._lay.addStretch(1)