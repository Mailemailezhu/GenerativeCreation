"""添加模型页：读硬件、列可装模型、一键装。"""
from PyQt5.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QProgressBar,
                             QPushButton, QScrollArea, QVBoxLayout, QWidget)

from core import catalog, hwprobe
from ui.worker import InstallWorker


class ModelCard(QFrame):
    def __init__(self, entry, on_install, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setObjectName("modelCard")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)

        left = QVBoxLayout()
        left.setSpacing(3)
        head = QHBoxLayout()
        name = QLabel(entry["name"])
        name.setObjectName("cardName")
        head.addWidget(name)
        tag = QLabel(entry["tag"])
        tag.setObjectName("cardTag")
        head.addWidget(tag)
        head.addStretch(1)
        left.addLayout(head)
        desc = QLabel(entry["desc"])
        desc.setObjectName("cardDesc")
        desc.setWordWrap(True)
        left.addWidget(desc)
        self.reason = QLabel(entry["reason"])
        self.reason.setObjectName("cardReason")
        left.addWidget(self.reason)
        lay.addLayout(left, 1)

        self.btn = QPushButton()
        self.btn.setMinimumWidth(84)
        self.btn.setMinimumHeight(30)
        if entry["state"] == "installed":
            self.btn.setText("已安装")
            self.btn.setEnabled(False)
        elif entry["state"] == "blocked":
            self.btn.setText("装不下")
            self.btn.setEnabled(False)
        else:
            self.btn.setText("安装")
            self.btn.setObjectName("primary")
            self.btn.clicked.connect(lambda: on_install(entry))
        lay.addWidget(self.btn)


class ModelPage(QDialog):
    def __init__(self, models_root, parent=None):
        super().__init__(parent)
        self.models_root = models_root
        self.setWindowTitle("添加模型")
        self.resize(760, 620)
        self._worker = None
        self.setStyleSheet(STYLE)

        hw = hwprobe.summary(models_root)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 12)
        lay.setSpacing(10)

        title = QLabel("这台电脑能用的模型")
        title.setObjectName("pageTitle")
        lay.addWidget(title)
        spec = QLabel(hwprobe.describe(hw))
        spec.setObjectName("pageSpec")
        lay.addWidget(spec)
        tip = QLabel("只列能直接驱动当前工作流的模型；缺的依赖会自动一起下。"
                     "显存或内存不够的档位标成「装不下」，不会让你装完才发现跑不动。")
        tip.setObjectName("pageTip")
        tip.setWordWrap(True)
        lay.addWidget(tip)

        self.body = QWidget()
        self.body_lay = QVBoxLayout(self.body)
        self.body_lay.setContentsMargins(0, 0, 0, 0)
        self.body_lay.setSpacing(8)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(self.body)
        area.setFrameShape(QFrame.NoFrame)
        lay.addWidget(area, 1)

        foot = QHBoxLayout()
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(6)
        self.bar.hide()
        self.pct = QLabel("")
        self.pct.setObjectName("pageTip")
        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(self.reject)
        foot.addWidget(self.bar, 1)
        foot.addWidget(self.pct)
        foot.addWidget(self.btn_close)
        lay.addLayout(foot)

        self.reload()

    def reload(self):
        while self.body_lay.count():
            it = self.body_lay.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()
        hw = hwprobe.summary(self.models_root)
        self.entries = catalog.evaluate(self.models_root, hw)
        for e in self.entries:
            self.body_lay.addWidget(ModelCard(e, self.install))
        self.body_lay.addStretch(1)

    def install(self, entry):
        if self._worker and self._worker.isRunning():
            return
        self.bar.show()
        self.bar.setValue(0)
        self.pct.setText("0%")
        for i in range(self.body_lay.count()):
            w = self.body_lay.itemAt(i).widget()
            if isinstance(w, ModelCard):
                w.btn.setEnabled(False)
        self._worker = InstallWorker(catalog.missing(self.models_root, entry), self.models_root)
        self._worker.progress.connect(self.on_progress)
        self._worker.done.connect(self.on_done)
        self._worker.failed.connect(self.on_failed)
        self._worker.start()

    def on_progress(self, pct, msg):
        self.bar.setValue(pct)
        self.pct.setText("%d%%" % pct)
        self.pct.setToolTip(msg)

    def on_done(self):
        self.bar.setValue(100)
        self.pct.setText("100%")
        self.reload()

    def on_failed(self, msg):
        self.pct.setText("失败")
        self.pct.setToolTip(msg)
        self.bar.hide()


STYLE = """
QDialog { background: #2d2d2d; }
QLabel#pageTitle { font-size: 16px; font-weight: bold; color: #e8e8e8; }
QLabel#pageSpec { color: #8fb8e0; font-size: 12px; }
QLabel#pageTip { color: #888888; font-size: 11px; }
QFrame#modelCard { background: #262626; border: 1px solid #3a3a3a; border-radius: 8px; }
QLabel#cardName { font-size: 13px; font-weight: bold; color: #e8e8e8; }
QLabel#cardTag { color: #2d8ceb; border: 1px solid #2d8ceb; border-radius: 7px;
    padding: 0 6px; font-size: 10px; }
QLabel#cardDesc { color: #9a9a9a; font-size: 11px; }
QLabel#cardReason { color: #7f9f7f; font-size: 11px; }
QProgressBar { background: #1e1e1e; border: none; border-radius: 3px; }
QProgressBar::chunk { background: #2d8ceb; border-radius: 3px; }
QScrollArea { border: none; background: transparent; }
"""
