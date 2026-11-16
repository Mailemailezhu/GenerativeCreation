"""手写 PSD 的自测：造两张图写成两图层，再用 psd-tools 读回核对。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app"))

from PIL import Image, ImageDraw

from core import psd

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "_psd")
os.makedirs(OUT, exist_ok=True)

W, H = 320, 200
base = Image.new("RGB", (W, H), (40, 60, 90))
d = ImageDraw.Draw(base)
d.ellipse((40, 40, 160, 160), fill=(190, 150, 120))
d.rectangle((200, 60, 290, 150), fill=(60, 120, 90))

gen = Image.new("RGB", (W, H), (250, 240, 200))
gd = ImageDraw.Draw(gen)
gd.polygon([(210, 30), (300, 90), (250, 170)], fill=(120, 230, 255))

mask = Image.new("L", (W, H), 0)
ImageDraw.Draw(mask).ellipse((180, 20, 310, 180), fill=255)

layer = gen.convert("RGBA")
layer.putalpha(mask)

comp = base.copy()
comp.paste(gen, (0, 0), mask)

path = os.path.join(OUT, "two_layers.psd")
n = psd.write(path, [("原始图", base.convert("RGBA")), ("生成内容", layer)], comp)
print("WROTE", n, path)

with open(path, "rb") as f:
    head = f.read(26)
print("SIG", head[:4], "VER", int.from_bytes(head[4:6], "big"),
      "CH", int.from_bytes(head[12:14], "big"),
      "H", int.from_bytes(head[14:18], "big"), "W", int.from_bytes(head[18:22], "big"),
      "DEPTH", int.from_bytes(head[22:24], "big"), "MODE", int.from_bytes(head[24:26], "big"))
