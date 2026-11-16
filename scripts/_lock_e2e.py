"""端到端：草稿 -> 锁构图正式档（2048），确认全尺寸下不崩、耗时与贴回正常。"""
import os, sys, time
import numpy as np
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
os.chdir(ROOT)
from core import cache, pipeline

img, msg = cache.load("data/test_input.png")
mask = Image.new("L", img.size, 0)
from PIL import ImageDraw
d = ImageDraw.Draw(mask)
d.ellipse((700, 300, 1020, 540), fill=255)
P = "一队发光的纸飞机呈对角线编队飞行，拖曳青蓝色粒子尾迹"
t0 = time.time()
dr = pipeline.run(img, mask, P, stage="draft", steps=4, cfg=1.0, seed=99,
                  progress=lambda p, m: None)
print("DRAFT %.0fs" % (time.time() - t0), dr["image"].size, dr["crop"], flush=True)
draft = dr["image"]
for lock in (0.55, 0.70):
    t = time.time()
    info = pipeline.run(img, mask, P, stage="final", draft=draft, steps=4, cfg=1.0,
                        seed=99, feather=14, lock=lock, progress=lambda p, m: None)
    out = info["image"]
    p = "data/_lock_e2e_%d.png" % int(lock * 100)
    out.save(p)
    a = np.asarray(img.convert("RGB")).astype(int)
    b = np.asarray(out).astype(int)
    dev = np.abs(a - b).max(axis=2)
    mm = np.asarray(mask) > 8
    print("LOCK", lock, "%.0fs" % (time.time() - t), info["crop"], info["size"],
          "changed", int((dev > 2).sum()), "inside", int(((dev > 2) & mm).sum()), p, flush=True)
