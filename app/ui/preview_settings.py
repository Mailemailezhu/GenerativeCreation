"""预览大小弹层：草稿档按原图长边的百分比缩放。"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget

STYLE = """
QWidget#pop { background: #2b2b2b; border: 1px solid #454545; border-radius: 4px; }
QLabel { color: #cfcfcf; font-size: 12px; }
QLabel#t { color: #ffffff; font-size: 12px; font-weight: 600; }
QLabel#v { color: #2d8ceb; font-size: 12px; }
QLabel#h { color: #8a8a8a; font-size: 11px; }
QSlider::groove:horizontal { height: 4px; background: #3a3a3a; border-radius: 2px; }
QSlider::handle:horizontal { width: 12px; margin: -5px 0; border-radius: 6px; background: #d8d8d8; }
QSlider::sub-page:horizontal { background: #2d8ceb; border-radius: 2px; }
"""


class PreviewSettings(QWidget):
    changed = pyqtSignal(float)

    def __init__(self, size, ratio=0.10, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setObjectName("pop")
        self.setStyleSheet(STYLE)
        self.setFixedWidth(272)
        self._size = size

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)
        t = QLabel("预览大小")
        t.setObjectName("t")
        lay.addWidget(t)

        row = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(2, 50)
        self.slider.setValue(int(round(ratio * 100)))
        self.slider.valueChanged.connect(self._on_change)
        row.addWidget(self.slider, 1)
        self.pct = QLabel("")
        self.pct.setObjectName("v")
        self.pct.setFixedWidth(46)
        row.addWidget(self.pct)
        lay.addLayout(row)

        self.px = QLabel("")
        self.px.setObjectName("h")
        lay.addWidget(self.px)
        note = QLabel("按原图长边等比缩放。越小越快，但细节越少；10% 足够看构图。")
        note.setObjectName("h")
        note.setWordWrap(True)
        lay.addWidget(note)

        self._on_change(self.slider.value())

    def _on_change(self, v):
        self.pct.setText("%d%%" % v)
        w, h = self._size
        if w and h:
            long_edge = max(w, h)
            side = max(256, min(2048, int(round(long_edge * v / 100.0))))
            self.px.setText("长边约 %d px（原图 %d × %d）" % (side, w, h))
        else:
            self.px.setText("先打开一张图，才知道实际像素")
        self.changed.emit(v / 100.0)
