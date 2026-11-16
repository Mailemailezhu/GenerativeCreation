"""创作面板顶部的模型列表，末行是「添加模型」。"""
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from core.hints import load as _load_hints

UI = _load_hints()["ui"]

STATE_TEXT = {"installed": "已安装", "ready": "可安装", "blocked": "装不下"}
API_ID = "@api"


class ModelList(QWidget):
    addRequested = pyqtSignal()
    modelSelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self.list = QListWidget()
        self.list.setFixedHeight(88)
        self.list.setToolTip(UI["model_list"])
        self.list.itemClicked.connect(self._on_click)
        lay.addWidget(self.list)
        self.btn_add = QPushButton("＋ 添加模型")
        self.btn_add.setObjectName("ghost")
        self.btn_add.setToolTip(UI["model_add"])
        self.btn_add.clicked.connect(self.addRequested.emit)
        lay.addWidget(self.btn_add)
        self.set_models([])

    def set_models(self, entries, current=None):
        self.list.clear()
        if not entries:
            it = QListWidgetItem("尚未安装主模型 — 点下方「添加模型」")
            it.setFlags(it.flags() & ~1)
            self.list.addItem(it)
        else:
            for e in entries:
                label = e["name"]
                if e.get("state") and e.get("state") != "installed":
                    label += "  ·  " + STATE_TEXT.get(e.get("state"), "")
                it = QListWidgetItem(label)
                it.setData(0x0100, e["id"])
                self.list.addItem(it)
        it = QListWidgetItem("＋ API 方案…")
        it.setData(0x0100, API_ID)
        self.list.addItem(it)
        row = self.list.sizeHintForRow(0) or 23
        self.list.setFixedHeight(min(5, self.list.count()) * row + 2 * self.list.frameWidth() + 2)
        picked = 0
        for i in range(self.list.count()):
            if current and self.list.item(i).data(0x0100) == current:
                picked = i
                break
        self.list.setCurrentRow(picked)

    def current_id(self):
        it = self.list.currentItem()
        return it.data(0x0100) if it else None

    def _on_click(self, item):
        mid = item.data(0x0100)
        if mid:
            self.modelSelected.emit(mid)
