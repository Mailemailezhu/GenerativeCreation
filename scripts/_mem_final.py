"""正式档内存验证：草稿 PIL 直接当参考图，不落 crop/mask 中间文件。"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
import bootstrap  # noqa: E402

bootstrap.apply()

from PIL import Image, ImageDraw  # noqa: E402

from core import pipeline  # noqa: E402

img = Image.new("RGB", (1600, 1000), (40, 80, 120))
ImageDraw.Draw(img).ellipse((600, 300, 1100, 700), fill=(220, 160, 120))
mask = Image.new("L", img.size, 0)
ImageDraw.Draw(mask).ellipse((700, 380, 1000, 620), fill=255)
draft = Image.open(os.path.join(ROOT, "data", "_mem_draft.png")).convert("RGB")

t0 = time.time()
info = pipeline.run(img, mask, "a flock of glowing cyan paper airplanes", None,
                    stage="final", draft=draft, steps=4, cfg=1.0, seed=777,
                    denoise=0.7, progress=lambda p, m: print("TICK", p, m, flush=True))
out = info["image"]
print("FINAL", round(time.time() - t0, 1), "s", out.size, info.get("crop"), info.get("feather"))
out.save(os.path.join(ROOT, "data", "_mem_final.png"))
print("OK")