"""API 方案页：填地址/模型/密钥，测连通性，应用后即选中该方案。"""
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QVBoxLayout)

from core import apimodels

STYLE = """
QDialog, QWidget { background: #2d2d2d; color: #d0d0d0;
    font-family: "Microsoft YaHei UI", "Segoe UI"; font-size: 12px; }
QLabel { color: #cfcfcf; }
QLabel#h { color: #8a8a8a; font-size: 11px; }
QLabel#t { color: #ffffff; font-size: 15px; font-weight: 600; }
QLineEdit { background: #252525; border: 1px solid #414141; border-radius: 3px;
    padding: 5px 7px; color: #e0e0e0; selection-background-color: #2d8ceb; }
QLineEdit:focus { border-color: #2d8ceb; }
QPushButton { background: #3a3a3a; border: 1px solid #4a4a4a; border-radius: 3px;
    color: #d0d0d0; padding: 6px 14px; min-height: 20px; }
QPushButton:hover { background: #454545; }
QPushButton#primary { background: #2d8ceb; border-color: #2d8ceb; color: #ffffff; }
QPushButton#primary:hover { background: #3f9bf0; }
QPushButton#primary:disabled { background: #333333; border-color: #3a3a3a; color: #777777; }
"""


class ProbeWorker(QThread):
    result = pyqtSignal(bool, str)

    def __init__(self, base, key):
        super().__init__()
        self.base = base
        self.key = key

    def run(self):
        ok, msg = apimodels.probe(self.base, self.key)
        self.result.emit(ok, msg)


class ApiPage(QDialog):
    def __init__(self, item=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API 方案")
        self.setStyleSheet(STYLE)
        self.resize(560, 330)
        self.item = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(10)
        t = QLabel("接一个远程模型")
        t.setObjectName("t")
        lay.addWidget(t)
        sub = QLabel("填 OpenAI 兼容服务的地址、模型名和密钥。应用后模型列表里会多这一项，"
                     "生成时改走远程接口。")
        sub.setObjectName("h")
        sub.setWordWrap(True)
        lay.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.ed_name = QLineEdit()
        self.ed_name.setPlaceholderText("给自己看的名字，例如 云端-快速版")
        self.ed_base = QLineEdit()
        self.ed_base.setPlaceholderText("https://api.example.com/v1")
        self.ed_model = QLineEdit()
        self.ed_model.setPlaceholderText("模型 id，例如 gpt-image-1")
        self.ed_key = QLineEdit()
        self.ed_key.setEchoMode(QLineEdit.Password)
        self.ed_key.setPlaceholderText("sk-…")
        form.addRow("名称", self.ed_name)
        form.addRow("接口地址", self.ed_base)
        form.addRow("模型", self.ed_model)
        form.addRow("API Key", self.ed_key)
        lay.addLayout(form)

        self.note = QLabel("生成走 /images/edits（上传原图 + 蒙版 + 提示词）。"
                           "只支持实现了这个接口的服务。")
        self.note.setObjectName("h")
        self.note.setWordWrap(True)
        lay.addWidget(self.note)
        lay.addStretch(1)

        row = QHBoxLayout()
        self.btn_test = QPushButton("测试连接")
        self.btn_test.clicked.connect(self.on_test)
        row.addWidget(self.btn_test)
        self.status = QLabel("")
        self.status.setObjectName("h")
        self.status.setWordWrap(True)
        row.addWidget(self.status, 1)
        self.btn_ok = QPushButton("应用")
        self.btn_ok.setObjectName("primary")
        self.btn_ok.setEnabled(False)
        self.btn_ok.clicked.connect(self.on_apply)
        row.addWidget(self.btn_ok)
        lay.addLayout(row)

        if item:
            self.ed_name.setText(item.get("name", ""))
            self.ed_base.setText(item.get("base", ""))
            self.ed_model.setText(item.get("model", ""))
            self.ed_key.setText(item.get("key", ""))
            if item.get("ok"):
                self._set_status(True, "上次测试通过，可以直接应用")

    def _set_status(self, ok, msg):
        self.status.setText(msg)
        self.status.setStyleSheet("color:%s;" % ("#5cb85c" if ok else "#e0a030"))
        self.btn_ok.setEnabled(bool(ok))

    def _fields(self):
        base = apimodels.norm_base(self.ed_base.text())
        return {"name": self.ed_name.text().strip() or base,
                "base": base,
                "model": self.ed_model.text().strip(),
                "key": self.ed_key.text().strip()}

    def on_test(self):
        f = self._fields()
        if not f["base"] or not f["key"]:
            self._set_status(False, "先填接口地址和 API Key")
            return
        self.btn_test.setEnabled(False)
        self._set_status(False, "正在测试…")
        self.worker = ProbeWorker(f["base"], f["key"])
        self.worker.result.connect(self.on_test_done)
        self.worker.start()

    def on_test_done(self, ok, msg):
        self.btn_test.setEnabled(True)
        self._set_status(ok, msg)
        self.note.setText(msg)

    def on_apply(self):
        f = self._fields()
        if not f["model"]:
            self._set_status(False, "还要填模型 id")
            return
        f["ok"] = True
        f["kind"] = "openai-images"
        self.item = f
        self.accept()
