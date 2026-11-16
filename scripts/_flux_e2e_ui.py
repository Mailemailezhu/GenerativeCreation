"""真实平台端到端：选 FLUX、给提示词、点生成预览图，等结果。"""
import os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'app'))
import bootstrap; bootstrap.apply()
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
import numpy as np
import PIL.Image as PILImage
import main as app_main

PROMPT = ('A young woman in a white knit sweater sitting on a mossy bank, a dozen white paper airplanes '
          'spiraling up around her, visible paper creases and soft shadows, fine cyan light particles, '
          'dreamy film look, photorealistic')

app = QApplication(sys.argv)
w = app_main.MainWindow()
w.resize(1444, 900)
w.show()
w._load_source(os.path.join(ROOT, 'data', 'DSC_4498.png'))
mask = np.array(PILImage.open(os.path.join(ROOT, 'data', '_plane_mask.png')).convert('L'))
h, wd = mask.shape
rgba = np.zeros((h, wd, 4), np.uint8)
rgba[..., 0] = 217
rgba[..., 1] = 64
rgba[..., 2] = 64
rgba[..., 3] = mask
qim = QImage(rgba.tobytes(), wd, h, 4 * wd, QImage.Format_RGBA8888).copy()
p = QPainter(w.canvas.mask)
p.setCompositionMode(QPainter.CompositionMode_Source)
p.drawImage(0, 0, qim)
p.end()
w.canvas._refresh_mask_item()
w.canvas.maskChanged.emit()
w.on_mask_changed()
w.prompt_edit.setPlainText(PROMPT)
w.on_model_selected('flux-fill-q5')
print('SIDE', w._draft_side(), 'MASK_RATIO %.3f' % w.canvas.mask_ratio(), flush=True)
w.on_generate()
t0 = time.time()
while time.time() - t0 < 900:
    QCoreApplication.processEvents()
    if not w._busy:
        break
    time.sleep(0.5)
print('BUSY', w._busy, 'DRAFT', w._draft_pil is not None, 'ELAPSED %.1f' % (time.time() - t0), flush=True)
if w._draft_pil is not None:
    out = os.path.join(ROOT, 'data', '_flux', 'ui_draft.png')
    w._draft_pil.save(out)
    print('SAVED', out, w._draft_pil.size, flush=True)
w.grab().save(os.path.join(ROOT, 'data', '_ui_flux_run.png'))
print('SHOT_OK', flush=True)
app.quit()
