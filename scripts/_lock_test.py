"""对照：以草稿为参考、降 denoise 是否既保构图又不留草稿瑕疵。"""
import os, sys
import numpy as np
from PIL import Image, ImageFilter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
os.chdir(ROOT)
from core import pipeline

P = "十架发光的纸飞机呈对角线编队飞行，拖曳青蓝色粒子尾迹"
base = Image.open("data/_count/C_big_in.png").convert("RGB")
mask = Image.open("data/_count/C_big_mask.png").convert("L")
draft = Image.open("data/_count/C_big.png").convert("RGB")
print("IN", base.size, "draft", draft.size, flush=True)

def hf(im, m):
    g = np.asarray(im.convert("L"), dtype=float)
    r = g - np.asarray(im.convert("L").filter(ImageFilter.GaussianBlur(2)), dtype=float)
    mm = np.asarray(m.resize(im.size), dtype=np.uint8) > 128
    return round(float(r[mm].std()), 3), round(float(g[mm].mean()), 1)

print("DRAFT_HF", hf(draft, mask), flush=True)
for dn in (0.55, 0.70):
    info = pipeline.run(base, mask, P, stage="final", draft=draft, steps=4, cfg=1.0,
                        seed=2024, feather=12, denoise=dn, progress=lambda p, m: None)
    out = info["image"]
    p = "data/_count/H_dn%d.png" % int(dn * 100)
    out.save(p)
    print("DN", dn, "size", out.size, "hf", hf(out, mask), p, flush=True)
