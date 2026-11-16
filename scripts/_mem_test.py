"""验证改造后管线全程走内存：prepare 收 PIL、mask_pil 不落盘、上传走字节。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
import bootstrap  # noqa: E402

bootstrap.apply()
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image, ImageDraw  # noqa: E402
from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtGui import QColor, QPainter  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from core import pipeline  # noqa: E402
from ui.canvas import CanvasView  # noqa: E402

app = QApplication(sys.argv)

img = Image.new("RGB", (1600, 1000), (40, 80, 120))
d = ImageDraw.Draw(img)
d.ellipse((600, 300, 1100, 700), fill=(220, 160, 120))
mask = Image.new("L", img.size, 0)
ImageDraw.Draw(mask).ellipse((700, 380, 1000, 620), fill=255)

got, m, geo = pipeline.prepare(img, mask, stage="draft", max_side=512)
print("PREPARE", got.size, m.size, geo["crop"], geo["size"])
png = pipeline._png_bytes(got)
print("PNG_BYTES", len(png), png[:8] == b"\x89PNG\r\n\x1a\n")

cv = CanvasView()
assert cv.load_image(img), "画布吃 PIL 失败"
p = QPainter(cv.mask)
p.setPen(Qt.NoPen)
p.setBrush(QColor(255, 0, 0, 255))
p.drawEllipse(700, 380, 300, 240)
p.end()
mp = cv.mask_pil()
print("MASK_PIL", mp.size, mp.mode, len(pipeline.ops.mask_bbox(__import__("numpy").asarray(mp))))
print("MASK_BBOX", pipeline.ops.mask_bbox(__import__("numpy").asarray(mp)))
print("RESULT_SRC", cv.set_result(img.resize((800, 500))), cv.view_mode, cv.has_result())
print("OK")