"""按 Adobe「导出为」的口径保存图像：JPEG / PNG / TIFF / PSD，各自带选项。

只写 8-bit：ComfyUI 内部就是 8-bit，源图也是 8-bit PNG；Pillow 又不支持
RGB 16-bit TIFF（硬写只会得到 8 位数据戴上 16 位的帽子），所以不放这一档。
PSD 走自带的 psd.py：合成图 + 图层栈，导出后能在 PS/Affinity 里单独关掉生成层。
"""
import io

from . import psd

FORMATS = ("JPEG", "PNG", "TIFF", "PSD")

EXT = {"JPEG": ".jpg", "PNG": ".png", "TIFF": ".tif", "PSD": ".psd"}


def _jpeg_quality(v):
    """Adobe 的品质是 0–12，Pillow 是 1–100；8 以上改用 4:4:4 采样。"""
    return max(1, min(100, int(round(float(v) / 12.0 * 100))))


def encode(img, fmt, opts):
    buf = io.BytesIO()
    if fmt == "JPEG":
        q = _jpeg_quality(opts.get("quality", 10))
        img.convert("RGB").save(buf, "JPEG", quality=q,
                                progressive=bool(opts.get("progressive")),
                                subsampling=0 if q >= 75 else 2, optimize=True)
    elif fmt == "PNG":
        img.convert("RGB").save(buf, "PNG", compress_level=int(opts.get("compress_level", 6)))
    elif fmt == "TIFF":
        comp = {"无": None, "LZW": "tiff_lzw", "ZIP": "tiff_deflate"}.get(
            opts.get("compression", "LZW"))
        kw = {"compression": comp} if comp else {}
        img.convert("RGB").save(buf, "TIFF", **kw)
    elif fmt == "PSD":
        raise ValueError("PSD 需要图层，请用 save()")
    else:
        raise ValueError("不支持的格式：" + str(fmt))
    return buf.getvalue()


def save(img, path, fmt, opts, stack=None):
    """返回写入的字节数。stack 只在 PSD 用，是自下而上的 (名称, RGBA) 列表。"""
    if fmt == "PSD":
        if not stack:
            raise ValueError("PSD 需要至少一个图层")
        return psd.write(path, stack, img)
    data = encode(img, fmt, opts)
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def human(n):
    if n >= 1024 * 1024:
        return "%.1f MB" % (n / 1024.0 / 1024.0)
    return "%d KB" % max(1, int(round(n / 1024.0)))
