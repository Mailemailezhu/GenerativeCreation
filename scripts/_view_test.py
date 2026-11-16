import os, sys
ROOTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOTDIR, 'app'))
from PyQt5.QtWidgets import QApplication
import main as A
app = QApplication(sys.argv)
win = A.MainWindow()
win.resize(1440, 900)
win.show()
win._load_source(os.path.join(A.ROOT, 'data', 'test_input.tif'))
for _ in range(8): app.processEvents()
win.canvas.set_result(os.path.join(A.ROOT, 'data', 'out_draft2.png'))
win.rail.set_view_enabled(True)
w = A.UI_SCALE
b = win.rail._views['split']
b.click()
for _ in range(4): app.processEvents()
print('after 1st click mode =', win.canvas.view_mode, 'checked', b.isChecked())
b.click()
for _ in range(4): app.processEvents()
print('after 2nd click mode =', win.canvas.view_mode, 'checked', b.isChecked())
win.grab().save(os.path.join(A.ROOT, 'data', '_ui_edit_after.png'))
print('zoom tool group visible after set_tool(zoom):', end=' ')
win.set_tool('zoom')
for _ in range(3): app.processEvents()
print(win.grp_zoom.isVisible())
win.btn_zoom_fit.click()
for _ in range(3): app.processEvents()
print('zoom label after fit =', win.zoom_label.text() if hasattr(win, 'zoom_label') else 'n/a')