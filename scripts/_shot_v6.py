import os, sys
ROOTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOTDIR, 'app'))
from PyQt5.QtWidgets import QApplication
import main as A

app = QApplication(sys.argv)
win = A.MainWindow()
win.resize(1440, 900)
win.show()
app.processEvents()
win._load_source(os.path.join(A.ROOT, 'data', 'test_input.tif'))
app.processEvents()
print('UI scale=%s font=%s dpr=%.2f' % (A.UI_SCALE, A.UI_FONT, win.devicePixelRatioF()))

def shot(name):
    for _ in range(8):
        app.processEvents()
    p = os.path.join(A.ROOT, 'data', name)
    win.grab().save(p)
    print('SHOT', p, win.width(), win.height())

shot('_ui_v6a.png')
win.set_tool('zoom')
shot('_ui_v6b.png')
win.set_tool('brush')
ok = win.canvas.set_result(os.path.join(A.ROOT, 'data', 'out_draft2.png'))
print('set_result', ok)
win.rail.set_view_enabled(True)
win._sync_view_buttons('split')
win.on_view_mode('split')
shot('_ui_v6c.png')
win.canvas.set_view_mode('original')
shot('_ui_v6d.png')
print('DONE')