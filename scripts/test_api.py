"""验证 API 方案：探活 -> 列表并入 -> run_api 贴回保真度。"""
import json
import os
import sys
import numpy as np
from PIL import Image
from PyQt5.QtWidgets import QApplication

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
os.chdir(ROOT)

from core import apimodels, pipeline

BASE = "http://127.0.0.1:8931/v1"
KEY = "sk-mock"
CFG = os.path.join(ROOT, "config", "api_models.json")

print("PROBE", apimodels.probe(BASE, KEY))
print("BADKEY", apimodels.probe(BASE, "sk-wrong")[0])

item = {"name": "本地模拟", "base": BASE, "model": "mock-edit-1", "key": KEY,
        "ok": True, "kind": "openai-images"}
apimodels.save(CFG, [item])
print("SAVED", len(apimodels.load(CFG)), apimodels.mask_key(item))

app = QApplication(sys.argv)
import main as appmain
w = appmain.MainWindow()
w.model_id = "api:" + apimodels.mask_key(item)
w.refresh_models()
labels = [w.model_list.list.item(i).text() for i in range(w.model_list.list.count())]
print("ROWS", labels)
print("CUR", w.model_list.current_id(), w.model_id)
print("API_ITEM", bool(w._api_item()), w._api_item().get("model"))
print("UNET_NONE", w._unet())

info = pipeline.run_api("data/test_input.png", "data/test_mask.png",
                        "一队发光的纸飞机", "data/out_api.png", item, stage="draft",
                        draft_side=512, progress=lambda p, m: None)
print("RUN_API", json.dumps({k: str(v) for k, v in info.items()}, ensure_ascii=False))

base = Image.open("data/test_input.png").convert("RGB")
out = Image.open("data/out_api.png").convert("RGB")
mask = Image.open("data/test_mask.png").convert("L")
a, b = np.asarray(base).astype(int), np.asarray(out).astype(int)
m = np.asarray(mask)
dev = np.abs(a - b).max(axis=2)
changed = dev > 2
inside = m > 200
outside = ~inside
print("CHANGED", int(changed.sum()), "INSIDE", int((changed & inside).sum()))
print("OUTSIDE_CHANGED", int((changed & outside).sum()), "MAXDEV_OUT", int(dev[outside].max() if outside.any() else 0))
print("SIZE", base.size, out.size)
