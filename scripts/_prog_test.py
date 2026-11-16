import os, sys, time
ROOTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOTDIR, 'app'))
from PIL import Image, ImageDraw
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from core import pipeline
from core.comfy_ws import ProgressWatcher
from ui.worker import GenWorker

ROOT = ROOTDIR
img = os.path.join(ROOT, 'data', 'test_input.tif')
mask = os.path.join(ROOT, 'data', '_prog_mask.png')
m = Image.new('L', (1200, 800), 0)
ImageDraw.Draw(m).ellipse((700, 180, 1120, 640), fill=255)
m.save(mask)
out = os.path.join(ROOT, 'data', '_prog_draft.png')

app = QApplication(sys.argv)
seen = []
w = ProgressWatcher()
t0 = time.time()
def on_ws(pct, msg):
    seen.append((round(time.time() - t0, 1), pct, msg))
    print('WS %.1fs %3d%% %s' % (seen[-1][0], pct, msg))
w.progress.connect(on_ws)
w.start()
for _ in range(40):
    app.processEvents()
    time.sleep(0.02)

g = GenWorker(pipeline.run, image_path=img, mask_path=mask, prompt='a flock of glowing cyan paper airplanes',
              out_path=out, stage='draft')
g.progress.connect(lambda p, s: print('CB %3d%% %s' % (p, s)))
g.failed.connect(lambda e: (print('FAIL', e), app.quit()))
g.done.connect(lambda info: (print('DONE', info), app.quit()))
QTimer.singleShot(0, g.start)
QTimer.singleShot(240000, app.quit)
app.exec_()
g.wait(5000)
mid = [p for _, p, _ in seen if 22 < p < 86]
print('MID_VALUES', mid)
print('PASS' if len(set(mid)) >= 2 else 'FAIL_NO_PROGRESS')