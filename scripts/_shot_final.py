import os, sys
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
sys.path.insert(0, APP)
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import main as M
app = QApplication(sys.argv)
w = M.MainWindow()
w.show()
w._load_source(os.path.join(M.ROOT, 'data', 'test_input.tif'), None)
src = os.path.join(M.ROOT, 'data', 'test_input.png')
for i in range(3):
    w.asset_strip.add(src if i == 0 else os.path.join(M.ROOT, 'data', 'test_input.png'))
w.asset_strip.clear()
for p in ('data/test_input.png', 'data/test_frame.png', 'data/test_mask.png'):
    fp = os.path.join(M.ROOT, p)
    if os.path.exists(fp):
        w.asset_strip.add(fp)
w.prompt_edit.setPlainText('一队发光的纸飞机呈对角线编队飞行，拖曳青蓝色粒子尾迹')
def fin():
    print('final dock_w=%d strip_h=%d strip_n=%d' % (w.panel_scroll.width(), w.asset_strip.height(), len(w.asset_strip.paths())), flush=True)
    w.grab().save(os.path.join(M.ROOT, 'data', '_ui_final.png'))
    app.quit()
QTimer.singleShot(1000, fin)
sys.exit(app.exec_())