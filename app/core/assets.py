"""多张素材图 → 一张参考拼版。

TextEncodeQwenImageEditPlus 只有三个参考图槽位：草稿档占 1 个（原图），定稿档占 2 个
（原图 + 草稿），留给素材的只有 1 个。所以多张素材按阅读顺序铺成网格当一张送进去，
再在提示词里说明排布顺序。
"""
import math
from pathlib import Path

from PIL import Image


def tile(paths, cell=512, gap=10, bg=(26, 26, 26)):
    """返回 (拼版图, 列数, 行数)。"""
    imgs = [Image.open(p).convert("RGB") for p in paths]
    n = len(imgs)
    cols = max(1, math.ceil(math.sqrt(n)))
    rows = math.ceil(n / cols)
    sheet = Image.new("RGB", (cols * cell + (cols - 1) * gap,
                              rows * cell + (rows - 1) * gap), bg)
    for i, im in enumerate(imgs):
        im.thumbnail((cell, cell), Image.LANCZOS)
        x = (i % cols) * (cell + gap) + (cell - im.width) // 2
        y = (i // cols) * (cell + gap) + (cell - im.height) // 2
        sheet.paste(im, (x, y))
    return sheet, cols, rows


def describe(paths):
    if len(paths) <= 1:
        return ""
    names = "、".join(Path(p).stem for p in paths)
    return f"（参考图按从左到右、从上到下排列，依次是：{names}）"
