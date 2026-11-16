"""把 LrC 传来的 TIFF / PSD 读成一份 8 位 RGB 图，解码结果只留在内存里。

LrC 的「外部编辑器」只给 TIFF / PSD / JPEG，而画布和 ComfyUI 都要 8 位 sRGB；
以前落一份 data/cache/*.png 当缓存，改图后还得靠 mtime 失效，6000×4000 一次就几十 MB。
现在每次打开直接解到内存，改完关掉就没了。
"""
import os
import time

import numpy as np
from PIL import Image

EXT_DIRECT = (".png", ".jpg", ".jpeg")
EXT_NEED_DECODE = (".tif", ".tiff", ".psd", ".bmp", ".webp")
EXT_ALL = EXT_DIRECT + EXT_NEED_DECODE


def human(n):
    if n >= 1024 * 1024:
        return "%.1f MB" % (n / 1024.0 / 1024.0)
    return "%d KB" % max(1, int(round(n / 1024.0)))


def _to_rgb8(im):
    """16 位 TIFF 会被 Pillow 读成 I;16/I，直接 convert 会压成一团黑。"""
    if im.mode in ("I;16", "I;16B", "I;16L", "I"):
        arr = np.asarray(im).astype(np.uint32)
        return Image.fromarray((arr >> 8).clip(0, 255).astype(np.uint8), "L").convert("RGB")
    if im.mode != "RGB":
        return im.convert("RGB")
    # copy() 会在 with 块里真正读一遍像素，否则关掉文件后这块内存是悬空视图
    return im.copy()


def load(path):
    """返回 (8 位 RGB 的 PIL.Image, 说明)；读不出来返回 (None, 原因)。"""
    t0 = time.time()
    try:
        with Image.open(path) as im:
            img = _to_rgb8(im)
    except (OSError, ValueError) as e:
        return None, str(e)
    msg = "已读入内存 %s（%d × %d，约 %s，%.1f 秒）" % (
        os.path.basename(path), img.width, img.height,
        human(img.width * img.height * 3), time.time() - t0)
    return img, msg