import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app"))
from core import pipeline
P = "一队发光的纸飞机呈对角线编队飞行，拖曳青蓝色粒子尾迹"
t = time.time()
info = pipeline.run("data/test_input.png", "data/test_mask.png", P, "data/out_final.png",
                    stage="final", draft_path="data/out_draft.png",
                    asset_paths=("data/test_input.png",), steps=4, cfg=1.0, seed=12345)
print("FINAL_OK", round(time.time() - t, 1), info)
