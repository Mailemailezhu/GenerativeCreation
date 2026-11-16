"""无头验证：主窗口的 PSD 图层栈与导出对话框的 PSD 页。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app"))

import bootstrap

bootstrap.apply()

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QPainter
from PyQt5.QtWidgets import QApplication

import main as app_main

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
app = QApplication(sys.argv)
w = app_main.MainWindow()
w._load_source(os.path.join(ROOT, "data", "test_input.tif"))
print("LOADED", w._orig_pil.size, w._cur_pil.size)

c = w.canvas
p = QPainter(c.mask)
p.setRenderHint(QPainter.Antialiasing)
p.setBrush(QBrush(QColor(255, 0, 0, 255)))
p.setPen(Qt.NoPen)
p.drawEllipse(QRectF(300, 200, 400, 300))
p.end()
c._refresh_mask_item()
print("MASK_BBOX", c.mask_bounds(), "RATIO", round(c.mask_ratio(), 3))

layers = w._psd_layers()
print("LAYERS", [(n, im.size, im.mode) for n, im in layers])

from core import exporter
from ui.export_dialog import ExportDialog

dlg = ExportDialog(w._cur_pil, os.path.join(ROOT, "data"), "ui_export", w)
dlg.layers = layers
dlg.refresh_note()
dlg.fmt_combo.setCurrentIndex(list(exporter.FORMATS).index("PSD"))
print("FMT", dlg.fmt(), "PAGE", dlg.stack.currentIndex())
print("NOTE", dlg.psd_note.text())
print("STACK", None if dlg.layers_for() is None else len(dlg.layers_for()))
dlg._schedule()

from datetime import datetime

tmp = os.path.join(ROOT, "data", "_psd", "ui_export.psd")
n = exporter.save(w._cur_pil, tmp, "PSD", {}, stack=dlg.layers_for())
print("WROTE_UI", n)

from PIL import Image, ImageChops

back = Image.open(tmp).convert("RGB")
d = ImageChops.difference(back, w._cur_pil.convert("RGB")).convert("L")
print("READBACK", back.size, "MAXDIFF", max(d.getdata()))
print("PSD_UI_OK")
