"""「生成预览图」按钮：主体点击生成，右侧内嵌齿轮点开预览设置。"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QPushButton, QToolButton

_ACTIVE = """
QPushButton { background: #2d8ceb; border: 1px solid #2d8ceb; border-radius: 3px;
             color: #ffffff; font-size: 13px; padding-right: 40px; min-height: 32px; }
QPushButton:hover { background: #3f9bf0; }
QPushButton:disabled { background: #333333; border-color: #3a3a3a; color: #777777; }
"""
_PLAIN = """
QPushButton { background: #3a3a3a; border: 1px solid #4a4a4a; border-radius: 3px;
             color: #c8c8c8; font-size: 13px; padding-right: 40px; min-height: 32px; }
QPushButton:hover { background: #454545; }
QPushButton:disabled { background: #2f2f2f; border-color: #383838; color: #6a6a6a; }
"""


class GearButton(QPushButton):
    gearClicked = pyqtSignal()

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.gear = QToolButton(self)
        self.gear.setText("\u2699")
        self.gear.setCursor(Qt.PointingHandCursor)
        self.gear.setFixedSize(26, 26)
        self.gear.setStyleSheet(
            "QToolButton { background: transparent; border: none; color: #ffffff;"
            " font-size: 15px; padding: 0; }"
            "QToolButton:hover { background: rgba(255,255,255,45); border-radius: 13px; }"
            "QToolButton:disabled { color: rgba(255,255,255,90); }")
        self.gear.clicked.connect(self.gearClicked.emit)
        self.set_look(True)

    def set_look(self, primary):
        self.setStyleSheet(_ACTIVE if primary else _PLAIN)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.gear.move(self.width() - 34, (self.height() - 26) // 2)
