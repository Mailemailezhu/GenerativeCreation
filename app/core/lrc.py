"""LrC 入口：把 LrC 传进来的路径解析成真正要创作的那张 PNG。

LrC 的「外部编辑器」只做两件事：先把照片导出成一份副本，再把副本路径当命令行参数
交给外部程序；程序退出后它检查这个副本有没有被改过，改过就导回目录并堆叠。

但 LrC 外部编辑器的格式选项里没有 PNG，而 ComfyUI 不读 ICC profile（Adobe RGB
的数值会被当 sRGB 解释，整张发灰）。所以约定是：用户先用 LrC「导出」出 PNG
（sRGB / 8-bit / 原尺寸），我们只拿 LrC 传来的文件名去导出目录里找同名 PNG。
"""
from pathlib import Path


EXTS = (".png", ".jpg", ".jpeg")   # PNG 优先，找不到才退 JPEG


def resolve(input_path, export_dirs=()):
    """返回 (图像路径 | None, 提示文本)。

    input_path 为空表示不是从 LrC 启动的，调用方走默认界面。
    PNG 优先：无损，送进 ComfyUI 不会二次压缩；JPEG 只是兜底。
    """
    if not input_path:
        return None, ""
    p = Path(input_path)
    if p.suffix.lower() in EXTS and p.is_file():
        return str(p), f"已载入 {p.name}"

    # 同名副本可能就在 LrC 导出的临时目录里，也可能在用户指定的导出文件夹
    for d in [p.parent, *[Path(x) for x in export_dirs if x]]:
        for ext in EXTS:
            cand = d / (p.stem + ext)
            if cand.is_file():
                kind = "PNG" if cand.suffix.lower() == ".png" else "JPEG"
                return str(cand), f"已载入同目录 {kind}：{cand.name}"

    return None, (
        f"LrC 传进来的是 {p.name}，没找到同名 PNG 或 JPEG。\n\n"
        "请在 LrC 里「导出」一张 PNG（sRGB / 8-bit / 原尺寸）到同一文件夹，"
        "再重新从 LrC 打开本程序；也可以直接拖一张 PNG 进来。"
    )


def siblings(png_path):
    """列出同一张照片可能存在的其它版本，方便界面上切换。"""
    p = Path(png_path)
    return sorted(str(x) for x in p.parent.glob(p.stem + "*") if x.suffix.lower() in
                  {".png", ".jpg", ".jpeg", ".tif", ".tiff"})
