"""界面上的所有提示文案，集中放 config/hints.xml，改文案不用碰代码。

XML 缺项时回落到这里的 DEFAULTS，所以删掉文件也不会崩，只是改不了文案。
工具顺序按 XML 里的顺序走：想调整左栏工具顺序，直接挪 <tool> 节点。
"""
import os
import xml.etree.ElementTree as ET

from . import paths

DEFAULT = {
    "tips": {
        "steps": ("采样步数：模型去噪迭代多少次。\n"
                  "本机实测每步约 5 秒（RTX 5070 12GB + Q5 模型）。\n"
                  "预览档 4 步约 20 秒采样；调到 8 步约 40 秒，画质提升有限。\n"
                  "步数翻倍时间就翻倍，和显存无关。"),
        "cfg": ("CFG = 提示词引导强度（Classifier-Free Guidance）。\n"
                "数值越高越死板地贴提示词、色彩更硬；越低越自由。\n"
                "本工作流挂了 4 步加速 LoRA，CFG 必须保持 1.0，调高会过曝、发糊甚至崩图。"),
        "gen": ("先用低分辨率出一张预览：选区裁切后长边 512，约 20 秒。\n"
                "只看构图和效果，不代表最终画质；重新生成会覆盖上一张。"),
        "apply": ("把这张预览当作风格参考，用 原图 + 预览 + 素材图 三张参考重绘正式图。\n"
                  "选区裁切后长边 2048，耗时约为预览的 4 到 5 倍。\n"
                  "必须先有一张预览。"),
        "denoise": ("融合强度 = 正式图重绘时保留原图的程度（denoise）。\n"
                    "1.0 = 蒙版内完全重画，最像模型原图，但风格容易和周围不同；\n"
                    "0.6~0.8 会保留原片的颗粒、光线和质感，融得更自然，代价是造型自由度下降。\n"
                    "预览档永远是 1.0，这个只影响「应用预览并生成正式图」。"),
        "feather": ("羽化 = 蒙版边缘的过渡宽度（像素）。自动按选区短边的 6% 算。\n"
                    "太大把周围原图也抹模糊，太小会看到硬边。24 MP 的照片一般 10~16 就够。"),
        "seed": "种子＝随机数起点。固定一个数字，同样的蒙版和提示词就能复现同一张图；保持「随机」则每次都不一样。想微调某张结果时先把它记下来。",
        "cmatch": "贴回前把生成片段的整体色调统计对齐到蒙版外的原图（LAB 均值与标准差）。关掉它颜色会更贴提示词，但和周围天空/皮肤的色温容易不一样。",
        "lock": "正式图从放大后的预览草稿出发，构图/位置/数量跟着草稿走，只重新渲染细节。\n0.5～0.6 几乎完全跟着草稿；0.7 以上允许模型补细节，可能多出新元素。关闭时草稿只当风格参考。",
        "assets": ("素材图：可缺省，也可以放好几张。\n"
                   "模型只有三个参考图槽位，多张素材会自动拼成一张，按从左到右、从上到下排列。"),
        "norm": "把口语化的描述整理成更贴近 AI 提示词的写法；本地模型不在时用规则整理。",
    },
    "ui": {
        "brush_hard": "笔刷边缘的软硬：100 是硬边，0 是整笔柔化（同 PS 的硬度）",
        "brush_opacity": "单笔最大浓度；调低后同一处反复涂抹才逐渐加深",
        "tolerance": "颜色差多少以内算同一片区域；调大选区更大，调小更挑",
        "feather_btn": "对当前蒙版本身做羽化，可 Ctrl+Z 撤销（同 PS 的选择 → 修改 → 羽化）",
        "mode": "添加 = 扩大选区；减去 = 从选区里擦掉",
        "show_mask": "关掉后画布上只显示原图，用来检查生成效果",
        "zoom_fit": "把整张图塞进画布，快捷键 Ctrl+0",
        "model_head": "点开可以选择主模型、添加模型或接远程 API",
        "adv_head": "融合强度、羽化、步数、CFG、种子、色彩对齐。默认值适合当前模型，改之前先看提示",
        "preview_size": "预览大小设置",
        "model_list": "当前软件能直接驱动的主模型。点「添加模型」可以看这台电脑还能装哪些。",
        "model_add": "读取本机显卡与内存，列出能直接用于本软件的模型，一键安装",
        "asset_plus": "添加素材图（可多选）",
        "asset_remove": "{name}\n右键移除",
        "asset_hint": "点击选择原始图像（也可以从 LrC 用「编辑于」直接打开）",
        "axis": "切换分割线方向：左右拖动 / 上下拖动",
        "reset": "丢掉预览和正式图，回到刚打开的原始图像（蒙版一起清空）",
    },
    "tools": [
        ("brush", "画笔", "画笔蒙版 (B)：涂出要重新生成的范围"),
        ("eraser", "橡皮", "橡皮 (E)：擦掉涂过的蒙版"),
        ("rect", "框选", "矩形选框 (M)：拖出一个矩形并入选区"),
        ("wand", "魔棒", "魔棒 (W)：点一下，选中颜色相近的连续区域"),
        ("quick", "快速", "快速选择 (Q)：按住拖动，吸附相近颜色"),
        ("hand", "指针", "指针 (H)：拖动画面，也可以按住空格拖"),
        ("zoom", "缩放", "缩放 (Z)：点一下放大，Alt+点击缩小，滚轮也行"),
    ],
    "views": [
        ("original", "原图", "只看原始图像"),
        ("split", "对比", "原图与预览并排，拖中间那条线改比例"),
        ("result", "预览", "只看生成结果"),
    ],
}

_CACHE = None


def path(root=None):
    return os.path.join(root or paths.root(), "config", "hints.xml")


def _merge(section, el):
    """按 XML 顺序覆盖 DEFAULTS：只改文字的条目直接换，工具/视图还带 name/label。"""
    if section in ("tools", "views"):
        out = []
        for node in el:
            key = node.get("key")
            if not key:
                continue
            label = node.get("name") if section == "tools" else node.get("label")
            out.append((key, label or key, (node.text or "").strip()))
        return out
    out = {}
    for node in el:
        key = node.get("key")
        if key:
            out[key] = (node.text or "").strip()
    return out


def load(root=None):
    """返回 {tips, ui, tools, views}；tools/views 是三元组列表，顺序即界面顺序。"""
    global _CACHE
    if root is None and _CACHE is not None:
        return _CACHE
    data = {k: (list(v) if isinstance(v, list) else dict(v)) for k, v in DEFAULT.items()}
    try:
        tree = ET.parse(path(root))
    except (OSError, ET.ParseError):
        data = {k: (list(v) if isinstance(v, list) else dict(v)) for k, v in DEFAULT.items()}
    else:
        for el in tree.getroot():
            section = "tips" if el.tag == "tips" else el.tag
            if section in data:
                data[section] = _merge(section, el)
    if root is None:
        _CACHE = data
    return data


def reset():
    """测试用：把缓存丢掉，下一次 load() 重新读盘。"""
    global _CACHE
    _CACHE = None