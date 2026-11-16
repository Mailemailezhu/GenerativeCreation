"""探测本机硬件，供模型页判断哪些模型装得下。"""
import ctypes
import shutil
import subprocess


class _MemStat(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def ram_gb():
    m = _MemStat()
    m.dwLength = ctypes.sizeof(_MemStat)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ullTotalPhys / 1024 ** 3, m.ullAvailPhys / 1024 ** 3


def gpu():
    """nvidia-smi 是最快也最可信的路，失败就当没有 N 卡。"""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15)
        line = out.stdout.strip().splitlines()[0]
        name, mb = [s.strip() for s in line.rsplit(",", 1)]
        return name, float(mb) / 1024
    except Exception:
        return "未检测到 NVIDIA 显卡", 0.0


def summary(root):
    name, vram = gpu()
    total, avail = ram_gb()
    return {"gpu": name, "vram_gb": round(vram, 1),
            "ram_gb": round(total, 1), "ram_avail_gb": round(avail, 1),
            "disk_free_gb": round(shutil.disk_usage(root).free / 1024 ** 3, 1)}


def describe(hw):
    return (f"{hw['gpu']} · 显存 {hw['vram_gb']:.0f} GB · 内存 {hw['ram_gb']:.0f} GB · "
            f"可用磁盘 {hw['disk_free_gb']:.0f} GB")
