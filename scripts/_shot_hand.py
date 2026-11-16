"""抓手态截图：确认画笔参数收起、选区信息保留。"""
import os, sys
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP)
from PyQt5.QtWidgets import QApplication
import main as app_main
app = QApplication(sys.argv)
w = app_main.MainWindow()
w.show(); app.processEvents()
w._load_source(os.path.join(app_main.DATA, "test_input.png"), None); app.processEvents()
w.canvas.set_result(os.path.join(app_main.DATA, "_gc_preview.png"))
w.set_tool("hand")
app.processEvents()
print("HAND brush=%s tol=%s sel=%s" % (w.grp_brush.isVisible(), w.grp_tol.isVisible(), w.grp_sel.isVisible()), flush=True)
w.grab().save(os.path.join(app_main.DATA, "_ui_hand.png"))
print("OK", flush=True)
