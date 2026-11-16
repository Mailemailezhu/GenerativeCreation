"""路径解析：源码运行时根目录在 app/ 上一层，打包后从 exe 往上找带 workflows/ 的目录。"""
import os
import sys

MARKER = "workflows"


def frozen():
    return bool(getattr(sys, "frozen", False))


def _has_root(path):
    return os.path.isfile(os.path.join(path, MARKER, "qwen_edit_2511_inpaint.json"))


def root():
    if not frozen():
        # app/core/paths.py -> app/core -> app -> 项目根
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    here = os.path.dirname(os.path.abspath(sys.executable))
    for _ in range(4):
        if _has_root(here):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    return os.path.dirname(os.path.abspath(sys.executable))


def asset(name):
    """打包资源优先从 PyInstaller 的解包目录取，源码运行取 app/assets。"""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        p = os.path.join(base, "assets", name)
        if os.path.exists(p):
            return p
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", name)
