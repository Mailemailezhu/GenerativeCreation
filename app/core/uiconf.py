"""界面缩放配置：Qt 默认按系统 DPI 放大，2K 屏 175% 下每个控件都巨大，这里接管。"""
import json
import os

DEFAULT = 1.0  # 0 = 跟随系统
DEFAULT_FONT = 12  # 界面字号（px）


def path(root):
    return os.path.join(root, "config", "ui.json")


def load(root):
    try:
        with open(path(root), "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def save(root, **kw):
    d = load(root)
    d.update(kw)
    p = path(root)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)
    return d
