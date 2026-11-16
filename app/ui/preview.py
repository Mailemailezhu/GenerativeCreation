"""结果预览窗口：独立窗口，不打断画布上的蒙版。"""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QDialog, QLabel, QScrollArea, QVBoxLayout


class PreviewWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("预览")
        self.resize(900, 700)
        self.setStyleSheet("QDialog { background: #1e1e1e; }")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel("还没有结果")
        self.label.setAlignment(Qt.AlignCenter)
        self.area = QScrollArea()
        self.area.setWidget(self.label)
        self.area.setWidgetResizable(True)
        lay.addWidget(self.area)
        self._path = None
        self._caption = ""

    def show_image(self, path, caption=""):
        pm = QPixmap(path)
        if pm.isNull():
            self.label.setText("读不到 " + path)
        else:
            self.label.setPixmap(pm)
            self.label.resize(pm.size())
        self._path = path
        self._caption = caption or "预览"
        self.setWindowTitle(self._caption)
        self.show()
        self.raise_()

    def refresh(self):
        if self._path:
            self.show_image(self._path, self._caption)
