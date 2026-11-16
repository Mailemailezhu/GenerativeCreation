"""大选区复现：50% 宽高的蒙版，检查送模型 mask 覆盖率与输出改动范围。"""
import os, sys, shutil
import numpy as np
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
os.chdir(ROOT)
from core import cache, pipeline

img, _ = cache.load("data/test_input.png")
W, H = img.size
mask = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(mask)
d.ellipse((int(W*0.18), int(H*0.15), int(W*0.82), int(H*0.85)), fill=255)
P = "一团发光的青蓝色星云漩涡，边缘散射粒子"
os.makedirs("data/_big", exist_ok=True)
info = pipeline.run(img, mask, P, stage="draft", steps=4, cfg=1.0, seed=4242,
                    progress=lambda p, m: None)
out = info["image"]
print("CROP", info["crop"], "SIZE", info["size"], flush=True)

inp = "engine/ComfyUI/input"
for name in ("gc_crop.png", "gc_mask.png"):
    p = os.path.join(inp, name)
    if os.path.exists(p):
        shutil.copy(p, "data/_big/" + name)
        im = Image.open(p)
        frac = np.asarray(im.convert("L"), dtype=np.uint8)
        print(name, im.size, "mask>128 frac %.3f" % ((frac > 128).mean() if name == "gc_mask.png" else -1), flush=True)

a = np.asarray(img.convert("RGB")).astype(int)
b = np.asarray(out).astype(int)
dev = np.abs(a - b).max(axis=2)
ch = dev > 2
mm = np.asarray(mask) > 128
print("MASK_AREA %d" % int(mm.sum()), "CHANGED %d" % int(ch.sum()),
      "INSIDE %d" % int((ch & mm).sum()), "OUTSIDE %d" % int((ch & ~mm).sum()), flush=True)
print("COVERAGE %.3f" % ((ch & mm).sum() / max(1, mm.sum())), flush=True)
out.save("data/_big/out.png")
mask.save("data/_big/mask_orig.png")
