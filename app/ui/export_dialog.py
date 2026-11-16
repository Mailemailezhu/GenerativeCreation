"""Adobe「导出为」风格的导出对话框：左侧预览，右侧格式 + 质量子页。"""
import os

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QSlider, QStackedWidget,
                             QVBoxLayout, QWidget)

from core import exporter

STYLE = """
QDialog { background: #1f1f1f; }
QLabel { color: #cfcfcf; font-size: 12px; }
QLabel#h { color: #8a8a8a; font-size: 11px; padding-top: 6px; }
QLabel#big { color: #ffffff; font-size: 13px; font-weight: 600; }
QLabel#est { color: #9a9a9a; font-size: 11px; }
QLineEdit, QComboBox, QSpinBox {
    background: #2b2b2b; border: 1px solid #3d3d3d; border-radius: 3px;
    color: #e6e6e6; padding: 4px 6px; min-height: 18px; }
QComboBox QAbstractItemView { background: #2b2b2b; color: #e6e6e6;
    selection-background-color: #2d8ceb; border: 1px solid #3d3d3d; }
QSlider::groove:horizontal { height: 4px; background: #3a3a3a; border-radius: 2px; }
QSlider::handle:horizontal { width: 12px; margin: -5px 0; border-radius: 6px;
    background: #d8d8d8; }
QSlider::sub-page:horizontal { background: #2d8ceb; border-radius: 2px; }
QPushButton { background: #3a3a3a; border: 1px solid #4a4a4a; border-radius: 3px;
    color: #e6e6e6; padding: 5px 16px; min-height: 20px; }
QPushButton:hover { background: #454545; }
QPushButton#primary { background: #2d8ceb; border: 1px solid #2d8ceb; color: #ffffff; }
QPushButton#primary:hover { background: #3f9bf0; }
QWidget#previewBox { background: #141414; border: 1px solid #333333; border-radius: 3px; }
QCheckBox { color: #cfcfcf; font-size: 12px; }
"""


class SizeWorker(QThread):
    """真正的编码一次拿到精确大小，比按经验公式估靠谱。"""
    done = pyqtSignal(int, int)

    def __init__(self, img, fmt, opts, token):
        super().__init__()
        self.img, self.fmt, self.opts, self.token = img, fmt, opts, token

    def run(self):
        try:
            n = len(exporter.encode(self.img, self.fmt, self.opts))
            self.done.emit(self.token, n)
        except Exception:
            self.done.emit(self.token, -1)


class ExportDialog(QDialog):
    def __init__(self, img, folder="", stem="未命名", parent=None):
        super().__init__(parent)
        self.img = img
        self.folder = folder or os.getcwd()
        self.stem = stem or "未命名"
        self.path = ""
        self._token = 0
        self._worker = None
        self.setWindowTitle("导出为")
        self.resize(860, 580)
        self.setStyleSheet(STYLE)

        root = QHBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 12)
        root.setSpacing(14)
        root.addWidget(self._build_left(), 1)
        root.addWidget(self._build_right(), 0)

        self._refresh_preview()
        self._on_format()

    # ---------- 左：预览 ----------
    def _build_left(self):
        box = QWidget()
        box.setObjectName("previewBox")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(8, 8, 8, 8)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(420, 420)
        lay.addWidget(self.preview, 1)
        self.meta = QLabel("")
        self.meta.setObjectName("est")
        self.meta.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.meta)
        return box

    def _refresh_preview(self):
        pm = QPixmap()
        if self.img is not None:
            from PyQt5.QtGui import QImage
            w, h = self.img.size
            px = self.img.convert("RGB").tobytes()
            qi = QImage(px, w, h, w * 3, QImage.Format_RGB888).copy()
            pm = QPixmap.fromImage(qi)
        if pm.isNull():
            self.preview.setText("没有可导出的图像")
            self.meta.setText("")
            return
        box = self.preview.size()
        self.preview.setPixmap(pm.scaled(max(200, box.width() - 8), max(200, box.height() - 8),
                                         Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.meta.setText("%d × %d px · 8 位/通道 · sRGB" % (pm.width(), pm.height()))

    # ---------- 右：格式与质量 ----------
    def _build_right(self):
        w = QWidget()
        w.setFixedWidth(330)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        t = QLabel("导出设置")
        t.setObjectName("big")
        lay.addWidget(t)

        lay.addWidget(self._h("格式"))
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(list(exporter.FORMATS))
        self.fmt_combo.currentIndexChanged.connect(self._on_format)
        lay.addWidget(self.fmt_combo)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._page_jpeg())
        self.stack.addWidget(self._page_png())
        self.stack.addWidget(self._page_tiff())
        lay.addWidget(self.stack)

        self.est = QLabel("预估大小 计算中…")
        self.est.setObjectName("est")
        lay.addWidget(self.est)
        lay.addStretch(1)

        lay.addWidget(self._h("文件名"))
        self.name_edit = QLineEdit(self.stem)
        self.name_edit.textChanged.connect(lambda *_: self._schedule())
        lay.addWidget(self.name_edit)

        lay.addWidget(self._h("位置"))
        row = QHBoxLayout()
        self.dir_edit = QLineEdit(self.folder)
        row.addWidget(self.dir_edit, 1)
        b = QPushButton("…")
        b.setFixedWidth(34)
        b.clicked.connect(self._pick_dir)
        row.addWidget(b)
        lay.addLayout(row)

        lay.addSpacing(6)
        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        self.ok = QPushButton("导出")
        self.ok.setObjectName("primary")
        self.ok.clicked.connect(self._accept)
        btns.addWidget(self.ok)
        lay.addLayout(btns)
        return w

    def _h(self, text):
        lab = QLabel(text)
        lab.setObjectName("h")
        return lab

    def _page_jpeg(self):
        p = QWidget()
        lay = QVBoxLayout(p)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(self._h("品质"))
        row = QHBoxLayout()
        self.q_slider = QSlider(Qt.Horizontal)
        self.q_slider.setRange(0, 12)
        self.q_slider.setValue(10)
        self.q_slider.valueChanged.connect(self._on_quality)
        row.addWidget(self.q_slider, 1)
        self.q_label = QLabel("")
        self.q_label.setFixedWidth(78)
        row.addWidget(self.q_label)
        lay.addLayout(row)
        self.prog_chk = QCheckBox("渐进式（网页逐步加载）")
        self.prog_chk.stateChanged.connect(lambda *_: self._schedule())
        lay.addWidget(self.prog_chk)
        note = QLabel("数值越大越清晰、文件越大。0–6 明显有块状噪点；8 以上才适合成片。")
        note.setWordWrap(True)
        note.setObjectName("est")
        lay.addWidget(note)
        lay.addStretch(1)
        self._on_quality(self.q_slider.value())
        return p

    def _page_png(self):
        p = QWidget()
        lay = QVBoxLayout(p)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(self._h("压缩"))
        self.png_combo = QComboBox()
        self.png_combo.addItems(["无（最快）", "低", "中", "高（最慢）"])
        self.png_combo.setCurrentIndex(2)
        self.png_combo.currentIndexChanged.connect(lambda *_: self._schedule())
        lay.addWidget(self.png_combo)
        note = QLabel("PNG 是无损格式，压缩只影响写入时间和体积，不影响画质。"
                      "给后续 AI 管线用建议选「无」，省下的时间比分卷存盘值钱。")
        note.setWordWrap(True)
        note.setObjectName("est")
        lay.addWidget(note)
        lay.addStretch(1)
        return p

    def _page_tiff(self):
        p = QWidget()
        lay = QVBoxLayout(p)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(self._h("压缩"))
        self.tif_combo = QComboBox()
        self.tif_combo.addItems(["无", "LZW（无损）", "ZIP（无损，更小）"])
        self.tif_combo.currentIndexChanged.connect(lambda *_: self._schedule())
        lay.addWidget(self.tif_combo)
        note = QLabel("TIFF 用于回到 LrC / PS 继续精修。本程序只写 8 位，"
                      "因为源图本身就是 8 位，补 16 位只是把字节数翻倍。")
        note.setWordWrap(True)
        note.setObjectName("est")
        lay.addWidget(note)
        lay.addStretch(1)
        return p

    # ---------- 交互 ----------
    def _on_quality(self, v):
        words = {0: "最低", 3: "低", 6: "中", 8: "高", 10: "很高", 12: "最高"}
        self.q_label.setText("%d %s" % (v, words.get(v, "")))
        self._schedule()

    def _on_format(self, *_):
        self.stack.setCurrentIndex(self.fmt_combo.currentIndex())
        ext = exporter.EXT[self.fmt()]
        base = os.path.splitext(self.name_edit.text().strip() or self.stem)[0]
        self.name_edit.setText(base)
        self._schedule()

    def fmt(self):
        return self.fmt_combo.currentText()

    def opts(self):
        f = self.fmt()
        if f == "JPEG":
            return {"quality": self.q_slider.value(), "progressive": self.prog_chk.isChecked()}
        if f == "PNG":
            return {"compress_level": [0, 3, 6, 9][self.png_combo.currentIndex()]}
        return {"compression": ["无", "LZW", "ZIP"][self.tif_combo.currentIndex()]}

    def _schedule(self):
        self._token += 1
        QTimer.singleShot(250, lambda: self._estimate(self._token))

    def _estimate(self, token):
        if token != self._token or self.img is None:
            return
        self.est.setText("预估大小 计算中…")
        self._worker = SizeWorker(self.img, self.fmt(), self.opts(), token)
        self._worker.done.connect(self._on_estimate)
        self._worker.start()

    def _on_estimate(self, token, n):
        if token != self._token:
            return
        self.est.setText("预估大小 —" if n < 0 else "预估大小 %s" % exporter.human(n))

    def _pick_dir(self):
        d = QFileDialog.getExistingDirectory(self, "导出到文件夹", self.dir_edit.text())
        if d:
            self.dir_edit.setText(d)

    def _accept(self):
        name = self.name_edit.text().strip()
        if not name:
            self.est.setText("文件名不能为空")
            return
        ext = exporter.EXT[self.fmt()]
        if not name.lower().endswith(ext):
            name += ext
        folder = self.dir_edit.text().strip()
        if not os.path.isdir(folder):
            self.est.setText("文件夹不存在：" + folder)
            return
        self.path = os.path.join(folder, name)
        self.accept()

    def showEvent(self, e):
        super().showEvent(e)
        self._refresh_preview()
