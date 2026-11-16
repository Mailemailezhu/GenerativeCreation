"""真机验证：管线用内存 PIL 输入跑一次草稿，并确认 data 下没有新增中间文件。"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
import bootstrap  # noqa: E402

bootstrap.apply()

from PIL import Image, ImageDraw  # noqa: E402

from core import pipeline  # noqa: E402

DATA = os.path.join(ROOT, "data")
before = set(os.listdir(DATA))

img = Image.new("RGB", (1600, 1000), (40, 80, 120))
ImageDraw.Draw(img).ellipse((600, 300, 1100, 700), fill=(220, 160, 120))
mask = Image.new("L", img.size, 0)
ImageDraw.Draw(mask).ellipse((700, 380, 1000, 620), fill=255)

t0 = time.time()
info = pipeline.run(img, mask, "a flock of glowing cyan paper airplanes", None,
                    stage="draft", steps=4, cfg=1.0, seed=12345,
                    progress=lambda p, m: print("TICK", p, m, flush=True))
out = info.get("image")
print("DRAFT", round(time.time() - t0, 1), "s", out.size, out.mode, info.get("crop"))
out.save(os.path.join(DATA, "_mem_draft.png"))
after = set(os.listdir(DATA))
print("NEW_FILES", sorted(after - before))
print("OK")