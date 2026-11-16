import os, sys, shutil
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
sys.path.insert(0, APP)
from PyQt5.QtWidgets import QApplication, QScrollArea
from PyQt5.QtCore import QTimer
import main as M

app = QApplication(sys.argv)
w = M.MainWindow()
w.show()
w._load_source(os.path.join(M.ROOT, 'data', 'test_input.tif'), None)
src = os.path.join(M.ROOT, 'data', 'test_input.png')
for i in range(3):
    dst = os.path.join(M.ROOT, 'data', '_asset%d.png' % i)
    shutil.copy(src, dst)
    w.asset_strip.add(dst)
w.model_head.setChecked(True)

def probe(tag):
    sa = w.panel_scroll
    body = sa.widget()
    bar = sa.verticalScrollBar()
    print('%s viewport=%dx%d body=%dx%d bodyMinH=%d bar_vis=%s max=%d dockH=%d strip_h=%d'
          % (tag, sa.viewport().width(), sa.viewport().height(), body.width(), body.height(),
             body.minimumSizeHint().height(), bar.isVisible(), bar.maximum(),
             w.model_list.parentWidget().height(), w.asset_strip.height()), flush=True)

def step1():
    probe('900')
    w.resize(1440, 700)
    QTimer.singleShot(600, step2)

def step2():
    probe('700')
    w.grab().save(os.path.join(M.ROOT, 'data', '_ui_short2.png'))
    app.quit()

QTimer.singleShot(900, step1)
sys.exit(app.exec_())