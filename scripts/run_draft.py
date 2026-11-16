import sys, time
sys.path.insert(0, "app")
from core import pipeline

PROMPT = "一队发光的纸飞机呈对角线编队飞行，拖曳青蓝色粒子尾迹，写实摄影质感，自然光影过渡"
t0 = time.time()
info = pipeline.run("data/test_input.png", "data/test_mask.png", PROMPT,
                    "data/out_draft.png", stage="draft", steps=4, cfg=1.0, seed=12345)
print("DRAFT_OK", round(time.time() - t0, 1), info)
