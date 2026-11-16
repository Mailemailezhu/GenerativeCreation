"""局部重绘的几何与合成。

核心原则：送模型的 crop 范围和贴回的蒙版范围是两回事。
crop 要带上下文（蒙版外扩），贴回只发生在蒙版内，蒙版外逐位保留原图。
"""
import numpy as np
from PIL import Image, ImageFilter

ALIGN = 8  # ComfyUI 的 latent 要求宽高是 8 的倍数


def mask_bbox(mask: np.ndarray, threshold: int = 8):
    """返回 (x0, y0, x1, y1)，蒙版为空时返回 None。"""
    ys, xs = np.nonzero(np.asarray(mask) > threshold)
    if xs.size == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def plan_crop(img_w, img_h, bbox, pad=180, max_side=2048, min_side=512):
    """算出送模型的 crop 框和缩放后尺寸。

    外扩 pad 是为了给模型足够的上下文；缩放是为了落在模型能力范围内。
    """
    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(img_w, x1 + pad)
    y1 = min(img_h, y1 + pad)
    w, h = x1 - x0, y1 - y0
    longest = max(w, h)
    scale = 1.0
    if longest > max_side:
        scale = max_side / longest
    elif longest < min_side:
        scale = min_side / longest
    tw = max(ALIGN, int(round(w * scale)) // ALIGN * ALIGN)
    th = max(ALIGN, int(round(h * scale)) // ALIGN * ALIGN)
    return {"crop": (x0, y0, x1, y1), "size": (tw, th), "scale": scale}


def crop_image(img, crop, size):
    return img.crop(crop).resize(size, Image.LANCZOS)


def crop_mask(mask, crop, size):
    return mask.crop(crop).resize(size, Image.LANCZOS)


def auto_feather(bbox, lo=6, hi=40):
    """羽化半径按蒙版短边自适应。

    固定 28px 对小蒙版是灾难：450x210 的椭圆周长约 1100px，28px 高斯会把
    84px 宽的过渡带铺到蒙版外，等于改了一大片本该逐位保留的像素。
    """
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    return int(max(lo, min(hi, min(w, h) * 0.06)))


def feather_mask(mask, feather=12):
    """羽化只在贴回时做，送模型的是硬边蒙版（否则模型会犹豫该不该画）。"""
    return mask.convert("L").filter(ImageFilter.GaussianBlur(feather))


def composite_back(base, generated_crop, mask_crop, crop, feather=12, grow=None):
    """把生成结果按蒙版贴回 base 的 crop 区域，蒙版外不动。"""
    x0, y0, x1, y1 = crop
    w, h = x1 - x0, y1 - y0
    gen = generated_crop.convert("RGB").resize((w, h), Image.LANCZOS)
    # 先放大回 crop 原尺寸再羽化，否则 feather 会被当成 crop 缩放后的像素，扩散范围放大 1/scale 倍
    hard = mask_crop.convert("L").resize((w, h), Image.LANCZOS)
    # 关键：先把蒙版往外扩 feather，再模糊。否则高斯尾巴会伸进蒙版内侧，
    # 用户画的细条带（比如 30px 高）会被原图稀释成半透明，等于没生成。
    # grow=0 表示严格逐位保留蒙版外像素，代价是羽化尾巴会伸进蒙版内侧
    grow = feather if grow is None else grow
    soft = hard
    if grow > 0:
        soft = soft.filter(ImageFilter.MaxFilter(2 * grow + 1))
    soft = soft.filter(ImageFilter.GaussianBlur(max(0.5, feather * 0.6)))
    out = base.copy()
    region = out.crop(crop)
    out.paste(Image.composite(gen, region, soft), (x0, y0))
    return out


def match_color(generated, original_crop, mask_crop, strength=1.0):
    """把生成图的 LAB 均值/标准差向原图对齐。

    只在蒙版外的像素上统计：蒙版内本来就要变，拿它当基准会把生成内容拉回原样。
    对齐系数强度 <1 时保守，避免整体偏色。
    """
    gen = np.asarray(generated.convert("RGB")).astype(np.float32)
    ref = np.asarray(original_crop.convert("RGB")).astype(np.float32)
    m = np.asarray(mask_crop.convert("L")) < 32
    if m.sum() < 64:
        return generated
    g = gen[m]
    r = ref[m]
    gm, gs = g.mean(0), g.std(0) + 1e-6
    rm, rs = r.mean(0), r.std(0) + 1e-6
    out = (gen - gm) / gs * rs + rm
    out = gen * (1 - strength) + out * strength
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def save_mask_png(mask, path):
    """蒙版存成灰度 PNG：白=重绘区，黑=保留区。"""
    if isinstance(mask, np.ndarray):
        mask = Image.fromarray(mask)
    mask.convert("L").save(path)
