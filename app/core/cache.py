"""LrC 的「外部编辑器」只给 TIFF / PSD / JPEG，而下游要的是 8 位 sRGB 位图。

这里把 LrC 传来的副本转成一份无压缩 PNG 缓存（compress_level=0）：
- 缓存名按 源路径 + 大小 + mtime 生成，同一张图第二次打开直接命中；
- 16 位 TIFF 只解码一次，画布和 ComfyUI 之后都吃同一份 8 位 PNG；
- 无压缩写盘快，data/ 本来就不进版本库。
"""
import hashlib
import os
import time

import numpy as np
from PIL import Image

EXT_DIRECT = (".png", ".jpg", ".jpeg")
EXT_NEED_CACHE = (".tif", ".tiff", ".psd", ".bmp")
EXT_ALL = EXT_DIRECT + EXT_NEED_CACHE


def human(n):
    if n >= 1024 * 1024:
        return "%.1f MB" % (n / 1024.0 / 1024.0)
    return "%d KB" % max(1, int(round(n / 1024.0)))


def _key(path):
    st = os.stat(path)
    raw = "%s|%d|%d" % (os.path.abspath(path).lower(), st.st_size, int(st.st_mtime))
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def _to_rgb8(im):
    """16 位 TIFF 会被 Pillow 读成 I;16/I，直接 convert 会压成一团黑。"""
    if im.mode in ("I;16", "I;16B", "I;16L", "I"):
        arr = np.asarray(im).astype(np.uint32)
        return Image.fromarray((arr >> 8).clip(0, 255).astype(np.uint8), "L").convert("RGB")
    if im.mode != "RGB":
        return im.convert("RGB")
    # copy() 会在 with 块里真正读一遍像素，否则 with 一关文件 save() 就 assert fp
    return im.copy()


def prune(cache_dir, keep=8):
    """缓存只留最近几张，免得 6000×4000 的原图把 data 盘吃满。"""
    try:
        files = [os.path.join(cache_dir, f) for f in os.listdir(cache_dir) if f.endswith(".png")]
    except OSError:
        return
    if len(files) <= keep:
        return
    files.sort(key=os.path.getmtime)
    for f in files[:len(files) - keep]:
        try:
            os.remove(f)
        except OSError:
            pass


def ensure(path, cache_dir):
    """返回 (可直接用的 8 位 PNG 路径, 说明文本)。"""
    ext = os.path.splitext(path)[1].lower()
    if ext in EXT_DIRECT:
        return path, ""
    os.makedirs(cache_dir, exist_ok=True)
    png = os.path.join(cache_dir, _key(path) + ".png")
    if os.path.isfile(png):
        return png, "命中缓存 %s（%s）" % (os.path.basename(png), human(os.path.getsize(png)))
    t0 = time.time()
    with Image.open(path) as im:
        img = _to_rgb8(im)
    img.save(png, "PNG", compress_level=0)
    prune(cache_dir)
    return png, "已缓存 %s → %s（%s，%.1f 秒）" % (
        os.path.basename(path), os.path.basename(png),
        human(os.path.getsize(png)), time.time() - t0)
