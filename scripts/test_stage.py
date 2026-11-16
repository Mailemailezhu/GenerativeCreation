import os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
os.chdir(ROOT)
from core import cache, pipeline

png, msg = cache.ensure(os.path.join(ROOT, "data", "test_input.tif"),
                        os.path.join(ROOT, "data", "cache"))
print("CACHE", os.path.basename(png), msg[:30])

wf = pipeline.build_workflow((512, 384), "x", "a.png", "b.png",
                             unet="qwen-image-edit-2511-Q5_K_M.gguf")
print("UNET_IN_WF", wf["1"]["inputs"]["unet_name"])

t0 = time.time()
info = pipeline.run(png, os.path.join(ROOT, "data", "test_mask.png"),
                    "一队发光的纸飞机呈对角线编队飞行，拖曳青蓝色粒子尾迹",
                    os.path.join(ROOT, "data", "out_draft2.png"),
                    stage="draft", draft_side=384, seed=7,
                    unet="qwen-image-edit-2511-Q5_K_M.gguf")
print("DRAFT_OK %.1f" % (time.time() - t0), info)
