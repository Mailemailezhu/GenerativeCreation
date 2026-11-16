"""生成与安装的后台线程：UI 线程只搬信号，不碰网络。"""
import os

from PyQt5.QtCore import QThread, pyqtSignal

from core import installer, pipeline


class GenWorker(QThread):
    progress = pyqtSignal(int, str)
    done = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, fn=None, **kw):
        super().__init__()
        # fn 允许把同一套进度/完成信号复用到本地档和远程 API 档
        self.fn = fn or pipeline.run
        self.kw = kw

    def run(self):
        try:
            info = self.fn(progress=lambda p, m: self.progress.emit(p, m), **self.kw)
            self.done.emit(info)
        except Exception as e:
            self.failed.emit("%s: %s" % (type(e).__name__, e))


class EngineProbe(QThread):
    result = pyqtSignal(bool)

    def __init__(self, host="127.0.0.1", port=8188):
        super().__init__()
        self.host = host
        self.port = port

    def run(self):
        try:
            from core.comfy_client import ComfyClient
            self.result.emit(ComfyClient(host=self.host, port=self.port).is_up())
        except Exception:
            self.result.emit(False)


class EngineStarter(QThread):
    """点生成时若引擎没起，就拉起它并轮询端口，用户不必自己开命令行。"""
    result = pyqtSignal(bool)

    def __init__(self, host="127.0.0.1", port=8188, tries=90):
        super().__init__()
        self.host = host
        self.port = port
        self.tries = tries

    def run(self):
        from core.comfy_client import ComfyClient
        c = ComfyClient(host=self.host, port=self.port)
        for _ in range(self.tries):
            try:
                if c.is_up():
                    self.result.emit(True)
                    return
            except Exception:
                pass
            self.msleep(2000)
        self.result.emit(False)


class InstallWorker(QThread):
    progress = pyqtSignal(int, str)
    done = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, files, models_root):
        super().__init__()
        self.files = list(files)
        self.models_root = models_root

    def run(self):
        n = max(1, len(self.files))
        try:
            for i, f in enumerate(self.files):
                dest = os.path.join(self.models_root, f["dest"])
                name = os.path.basename(dest)
                self._one(i, n, f, dest, name)
            self.done.emit()
        except Exception as e:
            self.failed.emit("%s: %s" % (type(e).__name__, e))

    def _one(self, i, n, f, dest, name):
        def cb(got, total, speed):
            frac = (got / total) if total else 0.0
            pct = int((i + frac) / n * 100)
            tot = ("/%.0f" % (total / 1048576.0)) if total else ""
            self.progress.emit(pct, "%s %.0f%s MB · %.1f MB/s"
                               % (name, got / 1048576.0, tot, speed))
        installer.download(f["url"], dest, on_progress=cb)
