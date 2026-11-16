import sys, os
sys.path.insert(0, "app")
from PyQt5.QtWidgets import QApplication
import main as M
app = QApplication(sys.argv)
w = M.MainWindow()
w.resize(1440, 900)
w.show()
app.processEvents()
w.on_adv_toggle(True)
w.adv_head.setChecked(True)
app.processEvents()
for _ in range(6):
    app.processEvents()
pm = w.grab()
out = os.path.join(M.DATA, "_ui_adv_open.png")
pm.save(out)
print("SHOT", out, pm.width(), pm.height())