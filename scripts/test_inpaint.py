"""端到端冒烟测试：预览档跑一张，再正式档跑一张并贴回。"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from core import pipeline  # noqa: E402

PROMPT = "一队发光的纸飞机呈对角线编队飞行，拖曳青蓝色粒子尾迹"


def main():
    src = ROOT / "data" / "test_input.png"
    msk = ROOT / "data" / "test_mask.png"
    t = time.time()
    r = pipeline.run(src, msk, PROMPT, ROOT / "data" / "out_preview.png", preview=True)
    print(f"preview ok {time.time() - t:.1f}s {r}")
    t = time.time()
    r = pipeline.run(src, msk, PROMPT, ROOT / "data" / "out_final.png", preview=False)
    print(f"final ok {time.time() - t:.1f}s {r}")


if __name__ == "__main__":
    main()
