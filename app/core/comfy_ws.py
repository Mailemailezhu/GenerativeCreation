"""监听 ComfyUI 的 /ws，把采样进度换成百分比。"""
import json

from PyQt5.QtCore import QObject, QUrl, pyqtSignal
from PyQt5.QtWebSockets import QWebSocket


class ProgressWatcher(QObject):
    progress = pyqtSignal(int, str)

    def __init__(self, host="127.0.0.1", port=8188, parent=None):
        super().__init__(parent)
        self._url = "ws://%s:%d/ws?clientId=gc-ui" % (host, port)
        self._sock = QWebSocket()
        self._sock.textMessageReceived.connect(self._on_text)
        self._last = 0

    def start(self):
        self._last = 0
        self._sock.open(QUrl(self._url))

    def stop(self):
        self._sock.close()

    def _emit(self, pct, msg):
        if pct > self._last:
            self._last = pct
            self.progress.emit(pct, msg)

    def _on_text(self, text):
        try:
            d = json.loads(text)
        except Exception:
            return
        kind = d.get("type")
        data = d.get("data") or {}
        if kind == "execution_start":
            self._emit(22, "引擎加载模型")
        elif kind == "progress":
            mx = max(1, int(data.get("max") or 1))
            v = int(data.get("value") or 0)
            self._emit(22 + int(62 * v / mx), "采样 %d/%d" % (v, mx))
        elif kind == "executing" and data.get("node") is None:
            self._emit(86, "解码")
