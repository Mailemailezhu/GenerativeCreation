"""走 exporter.save 的 PSD 分支，再用 Pillow 独立读回核对合成图。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app"))

from PIL import Image, ImageChops, ImageDraw

from core import exporter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "_psd")
os.makedirs(OUT, exist_ok=True)

W, H = 400, 260
base = Image.new("RGB", (W, H), (30, 45, 70))
ImageDraw.Draw(base).ellipse((30, 30, 180, 230), fill=(200, 160, 130))
gen = Image.new("RGB", (W, H), (240, 235, 210))
ImageDraw.Draw(gen).polygon([(220, 20), (380, 90), (300, 240)], fill=(90, 220, 255))
mask = Image.new("L", (W, H), 0)
ImageDraw.Draw(mask).ellipse((200, 10, 390, 250), fill=255)

layer = gen.convert("RGBA")
layer.putalpha(mask)
comp = base.copy()
comp.paste(gen, (0, 0), mask)

path = os.path.join(OUT, "export_test.psd")
n = exporter.save(comp, path, "PSD", {}, stack=[("原始图", base.convert("RGBA")),
                                              ("生成内容", layer)])
print("SAVED", n)

im = Image.open(path)
print("PILLOW", im.size, im.mode)
back = im.convert("RGB")
diff = ImageChops.difference(back, comp)
print("MAXDIFF", max(diff.convert("L").getdata()))
print("FORMATS", exporter.FORMATS, exporter.EXT["PSD"])
