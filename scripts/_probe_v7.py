import os, sys
ROOTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOTDIR, 'app'))
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QPoint
import main as A
app = QApplication(sys.argv)
win = A.MainWindow()
win.resize(1440, 900)
win.show()
for _ in range(8): app.processEvents()
def box(w):
    p = w.mapTo(win, QPoint(0, 0))
    return (p.x(), p.y(), w.width(), w.height(), p.y() + w.height())
sc = win.panel_scroll
shell = sc.parentWidget()
print('win', win.width(), win.height())
print('statusbar', box(win.statusBar()))
print('dock-of-scroll', box(sc.parentWidget().parentWidget()))
print('shell', box(shell))
for i in range(shell.layout().count()):
    w = shell.layout().itemAt(i).widget()
    print(i, w.__class__.__name__, box(w))