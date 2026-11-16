import os, sys, json
ROOTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOTDIR, 'app'))
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QPoint
import main as A
app = QApplication(sys.argv)
win = A.MainWindow()
win.resize(1440, 900)
win.show()
win._load_source(os.path.join(A.ROOT, 'data', 'test_input.tif'))
for _ in range(8): app.processEvents()
h0 = win.btn_gen.sizeHint().height()
win.set_font(16)
for _ in range(8): app.processEvents()
h1 = win.btn_gen.sizeHint().height()
win.grab().save(os.path.join(A.ROOT, 'data', '_ui_font16.png'))
cfg = json.load(open(os.path.join(A.ROOT, 'config', 'ui.json'), encoding='utf-8'))
checked = [a.text() for a in win.font_menu.actions() if a.isChecked()]
print('hint 12px =', h0, ' 16px =', h1)
print('ui.json', cfg, 'checked', checked)
win.set_font(12)
for _ in range(6): app.processEvents()
print('restored', json.load(open(os.path.join(A.ROOT, 'config', 'ui.json'), encoding='utf-8')))