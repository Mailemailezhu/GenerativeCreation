"""进程启动引导：必须在 import PyQt5 之前跑。

Qt 在加载平台插件时就读 QT_SCALE_FACTOR，等到 main() 里再设完全无效——打包后的 exe
就因为这个一直按系统的 175% 渲染，字看起来特别大。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from core import paths, uiconf  # noqa: E402

ROOT = paths.root()


def apply():
    """把 config/ui.json 的 scale 交给 Qt。

    只设 QT_SCALE_FACTOR 不够：QApplication 上再开 AA_EnableHighDpiScaling 会让 Qt 在
    系统 175% 的基础上再乘一遍，窗口被放大成 2406px 宽。所以这里始终给一个明确的值，
    main() 里不再碰 DPI 属性，缩放完全由 ui.json 决定。
    """
    try:
        scale = float(uiconf.load(ROOT).get("scale", uiconf.DEFAULT))
    except (TypeError, ValueError):
        scale = uiconf.DEFAULT
    if not scale or scale <= 0:
        scale = uiconf.DEFAULT
    if not scale or scale <= 0:
        scale = 1.0
    os.environ["QT_SCALE_FACTOR"] = "%.2f" % scale
    return scale


def font_size():
    try:
        return int(uiconf.load(ROOT).get("font", uiconf.DEFAULT_FONT))
    except (TypeError, ValueError):
        return uiconf.DEFAULT_FONT
