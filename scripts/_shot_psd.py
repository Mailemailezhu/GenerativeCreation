"""真实平台截图：把导出对话框切到 PSD 页，抓窗口。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app"))

import bootstrap

bootstrap.apply()

from PyQt5.QtCore import QRectF, Qt, QTimer
from PyQt5.QtGui import QBrush, QColor, QPainter
from PyQt5.QtWidgets import QApplication

import main as app_main
from core import exporter
from ui.export_dialog import ExportDialog

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA = os.path.join(ROOT, "data")

app = QApplication(sys.argv)
w = app_main.MainWindow()
w.resize(1440, 900)
w._load_source(os.path.join(DATA, "test_input.tif"))

c = w.canvas
p = QPainter(c.mask)
p.setRenderHint(QPainter.Antialiasing)
p.setBrush(QBrush(QColor(255, 0, 0, 255)))
p.setPen(Qt.NoPen)
p.drawEllipse(QRectF(700, 180, 380, 420))
p.end()
c._refresh_mask_item()

dlg = ExportDialog(w._cur_pil, DATA, "test_input", w)
dlg.layers = w._psd_layers()
dlg.refresh_note()
dlg.fmt_combo.setCurrentIndex(list(exporter.FORMATS).index("PSD"))


def grab():
    dlg.grab().save(os.path.join(DATA, "_ui_psd.png"))
    w.grab().save(os.path.join(DATA, "_ui_psd_main.png"))
    print("SHOT_OK", os.path.join(DATA, "_ui_psd.png"))
    app.quit()


dlg.show()
w.show()
QTimer.singleShot(1200, grab)
app.exec_()
