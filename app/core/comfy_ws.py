"""监听 ComfyUI 的 /ws，把采样步数换算成百分比。

ComfyUI 只把 executing / progress 发给提交任务的那个 client_id，所以这里必须和
ComfyClient.queue_prompt 用同一个 ID；不一致就一条事件都收不到，界面表现是进度卡在
18% 然后直接跳到 90%（那 90% 是 worker 自己报的贴回进度）。
"""
import json

from PyQt5.QtCore import QObject, QUrl, pyqtSignal
from PyQt5.QtNetwork import QAbstractSocket
from PyQt5.QtWebSockets import QWebSocket

from .comfy_client import CLIENT_ID

SAMPLE_LO, SAMPLE_HI = 22, 86


class ProgressWatcher(QObject):
    progress = pyqtSignal(int, str)

    def __init__(self, host="127.0.0.1", port=8188, parent=None):
        super().__init__(parent)
        self._url = "ws://%s:%d/ws?clientId=%s" % (host, port, CLIENT_ID)
        self._sock = QWebSocket()
        self._sock.textMessageReceived.connect(self._on_text)
        self._last = 0

    def start(self):
        # 一直挂着，每次生成只把计数清零：反复开关 socket 容易丢掉最早的事件
        self._last = 0
        if self._sock.state() != QAbstractSocket.ConnectedState:
            self._sock.open(QUrl(self._url))

    def stop(self):
        self._last = 0

    def _emit(self, pct, msg):
        pct = max(0, min(100, int(pct)))
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
            self._emit(SAMPLE_LO - 2, "引擎开始执行")
        elif kind == "execution_cached":
            self._emit(SAMPLE_LO - 1, "命中缓存")
        elif kind == "progress":
            mx = max(1, int(data.get("max") or 1))
            v = int(data.get("value") or 0)
            span = SAMPLE_HI - SAMPLE_LO
            self._emit(SAMPLE_LO + int(span * v / mx), "采样 %d/%d 步" % (v, mx))
        elif kind == "executing" and data.get("node") is None:
            self._emit(SAMPLE_HI, "解码输出")
