import os, sys
ROOTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOTDIR, 'app'))
from PyQt5.QtWidgets import QApplication, QLabel
from PyQt5.QtCore import QPoint
import main as A
app = QApplication(sys.argv)
win = A.MainWindow()
win.resize(1440, 900)
win.show()
for _ in range(8): app.processEvents()
def px(w):
    return w.mapTo(win, QPoint(0, 0)).x()
for w in win.findChildren(QLabel):
    t = w.text()
    if t and len(t) <= 6 and ('创作' in t or '原始图' == t or '素材图' in t or '文本' == t):
        print('label', repr(t), 'x', px(w), 'style pad?', w.objectName())
print('model_head', repr(win.model_head.text()), 'x', px(win.model_head), 'obj', win.model_head.objectName())
print('scroll x', px(win.panel_scroll), 'w', win.panel_scroll.width())
print('src_card x', px(win.src_card), win.src_card.width(), win.src_card.height())