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
for _ in range(3):
    w.asset_strip.add(os.path.join(M.ROOT, 'data', 'test_input.png'))
w.prompt_edit.setPlainText('一队发光的纸飞机呈对角线编队飞行，拖曳青蓝色粒子尾迹')

def shot1():
    print('COLLAPSED list_visible=%s head=%r' % (w.model_list.isVisible(), w.model_head.text()), flush=True)
    w.grab().save(os.path.join(M.ROOT, 'data', '_ui_collapse.png'))
    w.model_head.setChecked(True)
    QTimer.singleShot(400, shot2)

def shot2():
    print('EXPANDED list_visible=%s head=%r' % (w.model_list.isVisible(), w.model_head.text()), flush=True)
    w.grab().save(os.path.join(M.ROOT, 'data', '_ui_expanded.png'))
    w.resize(1440, 640)
    QTimer.singleShot(500, shot3)

def shot3():
    sb = w.findChild(__import__('PyQt5.QtWidgets', fromlist=['QScrollArea']).QScrollArea)
    bar = sb.verticalScrollBar() if sb else None
    print('SHORT scrollarea=%s range=%s/%s assets_rows_visible=%s' % (
        sb is not None, bar.value() if bar else -1, bar.maximum() if bar else -1,
        w.asset_strip.isVisible()), flush=True)
    w.grab().save(os.path.join(M.ROOT, 'data', '_ui_short.png'))
    app.quit()

QTimer.singleShot(900, shot1)
sys.exit(app.exec_())