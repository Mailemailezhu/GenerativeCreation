"""无头验证：复位按钮回到原图、选区工具默认显示蒙版并切回原图。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
import bootstrap  # noqa: E402

bootstrap.apply()
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

import main as app_main  # noqa: E402

app = QApplication(sys.argv)
w = app_main.MainWindow()
src = os.path.join(ROOT, "data", "test_input.png")
assert w._load_source(src), "打开原图失败"
orig = w._orig_pil
print("LOADED", w._orig_pil.size, "reset_enabled", w.btn_reset.isEnabled())

draft = orig.resize((orig.width // 2, orig.height // 2))
w._draft_pil = draft
w.canvas.set_result(draft)
w._sync_view_buttons("split")
print("DRAFT_VIEW", w.canvas.view_mode, w.canvas.has_result())

w.set_tool("rect")
print("AFTER_RECT", w.canvas.view_mode, w.show_mask_cb.isChecked(), w.canvas.mask_visible,
      "zoom_act", w.act_zoom.isVisible())
w.set_tool("hand")
print("AFTER_HAND", w.canvas.tool, w.canvas.view_mode)

w.on_reset()
print("AFTER_RESET", w.canvas.image.width(), w.canvas.image.height(),
      "draft", w._draft_pil, "has_result", w.canvas.has_result(),
      "apply", w.btn_apply.isEnabled(), "gen", w.btn_gen.text())
print("SAME_ORIG", w.canvas.image.width() == orig.width)
print("OK")