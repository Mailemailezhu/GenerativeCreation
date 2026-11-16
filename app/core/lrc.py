"""LrC 入口：把 LrC 传进来的路径解析成真正要创作的那张图。

LrC 的「外部编辑器」只有 TIFF / PSD / JPEG 这些选项，没有 PNG。所以约定改成：
用户在 LrC 里右键「编辑于 → GC」，LrC 导出一份 TIFF 副本并传路径进来，
GC 自己把它转成无压缩 PNG 缓存（core/cache.py）再用。

如果传进来的不是 TIFF 而是别的格式（或只是文件名），再按 同名 PNG → JPEG 兜底找。
"""
from pathlib import Path

DIRECT = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".psd")
FALLBACK = (".png", ".jpg", ".jpeg")


def resolve(input_path, export_dirs=()):
    """返回 (图像路径 | None, 提示文本)。

    input_path 为空表示不是从 LrC 启动的，调用方走默认界面。
    """
    if not input_path:
        return None, ""
    p = Path(input_path)
    if p.suffix.lower() in DIRECT and p.is_file():
        return str(p), ""

    # LrC 有时只把副本放进临时目录，同名 PNG/JPEG 可能在导出文件夹里
    for d in [p.parent, *[Path(x) for x in export_dirs if x]]:
        for ext in FALLBACK:
            cand = d / (p.stem + ext)
            if cand.is_file():
                kind = "PNG" if cand.suffix.lower() == ".png" else "JPEG"
                return str(cand), "已载入同目录 %s：%s" % (kind, cand.name)

    return None, (
        "LrC 传进来的是 %s，没找到能读的副本。\n\n"
        "请在 LrC 里「编辑于 → 在外部编辑器中打开」，文件格式选 TIFF"
        "（8 位 / sRGB），再打开一次；也可以直接把图片拖进本程序。"
    ) % p.name
