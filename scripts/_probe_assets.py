import os, sys, shutil
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
for i in range(6):
    dst = os.path.join(M.ROOT, 'data', '_asset%d.png' % i)
    if not os.path.exists(dst):
        shutil.copy(src, dst)
    w.asset_strip.add(dst)

def probe():
    sa = w.panel_scroll
    print('assets=%d strip=%dx%d bodyH=%d viewH=%d max=%d'
          % (len(w.asset_strip.paths()), w.asset_strip.width(), w.asset_strip.height(),
             sa.widget().height(), sa.viewport().height(), sa.verticalScrollBar().maximum()), flush=True)
    w.grab().save(os.path.join(M.ROOT, 'data', '_ui_assets6.png'))
    app.quit()

QTimer.singleShot(1000, probe)
sys.exit(app.exec_())