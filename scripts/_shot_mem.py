"""真实平台截图：打开原图 + 蒙版 + 草稿对比，看复位按钮位置与选区联动。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
import bootstrap  # noqa: E402

bootstrap.apply()

from PIL import Image  # noqa: E402
from PyQt5.QtCore import Qt, QTimer  # noqa: E402
from PyQt5.QtGui import QColor, QPainter  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

import main as app_main  # noqa: E402

app = QApplication(sys.argv)
w = app_main.MainWindow()
w.resize(1444, 900)
w.show()
w._load_source(os.path.join(ROOT, "data", "test_input.tif"))
p = QPainter(w.canvas.mask)
p.setPen(Qt.NoPen)
p.setBrush(QColor(255, 0, 0, 255))
p.drawEllipse(700, 300, 320, 240)
p.end()
w.canvas._refresh_mask_item()
w.canvas.maskChanged.emit()
w.on_mask_changed()

draft = Image.open(os.path.join(ROOT, "data", "_mem_draft.png")).convert("RGB")
w._draft_pil = draft
w.canvas.set_result(draft)
w.btn_apply.setEnabled(True)
w.btn_gen.setText("重新生成预览图")
w._sync_view_buttons("split")
w.set_tool("brush")


def shot():
    w.grab().save(os.path.join(ROOT, "data", "_ui_mem.png"))
    print("SHOT_OK", flush=True)
    app.quit()


QTimer.singleShot(1500, shot)
sys.exit(app.exec_())