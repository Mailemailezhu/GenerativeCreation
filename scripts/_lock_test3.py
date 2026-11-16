"""关 Lightning、16 步 cfg3、denoise 0.6：非蒸馏模型能否锁住草稿构图。"""
import os, sys, time
import numpy as np
from PIL import Image, ImageFilter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
os.chdir(ROOT)
from core import pipeline

orig_bw = pipeline.build_workflow
def patched(*a, **k):
    wf = orig_bw(*a, **k)
    for nid, n in wf.items():
        if n.get("class_type") == "LoraLoaderModelOnly":
            n["inputs"]["strength_model"] = 0.0
            print("LORA_OFF", nid, flush=True)
    return wf
pipeline.build_workflow = patched

P = "十架发光的纸飞机呈对角线编队飞行，拖曳青蓝色粒子尾迹"
base = Image.open("data/_count/C_big_in.png").convert("RGB")
mask = Image.open("data/_count/C_big_mask.png").convert("L")
draft = Image.open("data/_count/C_big.png").convert("RGB")
def hf(im, m):
    g = np.asarray(im.convert("L"), dtype=float)
    r = g - np.asarray(im.convert("L").filter(ImageFilter.GaussianBlur(2)), dtype=float)
    mm = np.asarray(m.resize(im.size), dtype=np.uint8) > 128
    return round(float(r[mm].std()), 3), round(float(g[mm].mean()), 1)

for dn in (0.60,):
    t = time.time()
    info = pipeline.run(base, mask, P, stage="final", draft=draft, steps=16, cfg=3.0,
                        seed=2024, feather=12, denoise=dn, progress=lambda p, m: None)
    out = info["image"]
    p = "data/_count/J_dn%d_nolora.png" % int(dn * 100)
    out.save(p)
    print("DN", dn, "%.0fs" % (time.time() - t), "hf", hf(out, mask), p, flush=True)
