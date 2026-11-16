import os, sys, time
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
sys.path.insert(0, APP)
import numpy as np
from PIL import Image
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import main as M

app = QApplication(sys.argv)
w = M.MainWindow()
w.show()
w._load_source(os.path.join(M.ROOT, 'data', 'test_input.tif'), None)
mask = np.array(Image.open(os.path.join(M.ROOT, 'data', 'test_mask.png')).convert('L'))
w.canvas.mask = w.canvas._mask_from_alpha(mask)
w.prompt_edit.setPlainText('一队发光的纸飞机呈对角线编队飞行，拖曳青蓝色粒子尾迹')
print('ENGINE_BEFORE', w._engine_ok, flush=True)
w.on_generate()
print('AFTER_CLICK busy=%s pending=%s proc=%s' % (w._busy, bool(w._pending), bool(w._engine_proc)), flush=True)

t0 = time.time()
def poll():
    if not w._busy and (w._draft_path or time.time() - t0 > 300):
        print('DONE draft=%s elapsed=%.1fs engine_ok=%s' % (w._draft_path, time.time() - t0, w._engine_ok), flush=True)
        app.quit()
        return
    QTimer.singleShot(2000, poll)
QTimer.singleShot(3000, poll)
sys.exit(app.exec_())