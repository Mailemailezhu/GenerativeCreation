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
for ns in ('_asset0.png', '_asset1.png'):
    p = os.path.join(A.ROOT, 'data', ns)
    if os.path.exists(p):
        win.asset_strip.add(p)
win.prompt_edit.setPlainText('一队发光的纸飞机呈对角线队形飞行，拖曳青蓝色粒子尾迹')
win.canvas.set_result(os.path.join(A.ROOT, 'data', 'out_draft2.png'))
for _ in range(10): app.processEvents()
win.grab().save(os.path.join(A.ROOT, 'data', '_ui_v6_final.png'))
print('SHOT', win.width(), win.height(), 'view', win.canvas.view_mode)