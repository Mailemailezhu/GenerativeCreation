"""GC：本地 AI 图像创作工作台。"""
import os
import sys

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QKeySequence
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QCheckBox, QDockWidget,
                             QFileDialog, QFormLayout, QHBoxLayout, QLabel, QListWidget,
                             QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
                             QSlider, QSpinBox, QDoubleSpinBox, QTextEdit, QToolBar,
                             QVBoxLayout, QWidget, QGroupBox)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)
from ui.canvas import CanvasView

QSS = """
QMainWindow, QWidget { background: #2d2d2d; color: #d0d0d0;
    font-family: "Microsoft YaHei UI", "Segoe UI"; font-size: 12px; }
QMenuBar { background: #252525; border-bottom: 1px solid #1a1a1a; }
QMenuBar::item { padding: 5px 10px; background: transparent; }
QMenuBar::item:selected { background: #3a3a3a; }
QMenu { background: #2d2d2d; border: 1px solid #3f3f3f; padding: 4px; }
QMenu::item { padding: 5px 26px 5px 22px; }
QMenu::item:selected { background: #2d8ceb; color: #ffffff; }
QToolBar { background: #252525; border: none; spacing: 2px; padding: 3px; }
QToolBar::separator { background: #3a3a3a; width: 1px; margin: 4px 3px; }
QToolButton { background: transparent; border-radius: 4px; padding: 4px; }
QToolButton:hover { background: #3a3a3a; }
QToolButton:checked { background: #2d8ceb; }
QToolButton:pressed { background: #1f6fb5; }
QDockWidget { color: #9a9a9a; titlebar-close-icon: none; titlebar-normal-icon: none; }
QDockWidget::title { background: #252525; padding: 6px 8px; }
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox {
    background: #1e1e1e; border: 1px solid #3f3f3f; border-radius: 3px;
    padding: 4px; color: #d0d0d0; selection-background-color: #2d8ceb; }
QPushButton { background: #3a3a3a; border: 1px solid #4a4a4a; border-radius: 3px;
    padding: 6px 10px; color: #d0d0d0; }
QPushButton:hover { background: #454545; }
QPushButton#primary { background: #2d8ceb; border: none; color: #ffffff; font-weight: bold; }
QPushButton#primary:hover { background: #3d9cfb; }
QPushButton#primary:disabled { background: #444444; color: #888888; }
QSlider::groove:horizontal { height: 3px; background: #1a1a1a; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #4a4a4a; border-radius: 2px; }
QSlider::handle:horizontal { width: 11px; margin: -5px 0; border-radius: 5px; background: #a0a0a0; }
QSlider::handle:horizontal:hover { background: #c8c8c8; }
QListWidget { background: #252525; border: none; outline: none; }
QListWidget::item { padding: 5px 6px; border-radius: 3px; }
QListWidget::item:selected { background: #2d8ceb; color: #ffffff; }
QCheckBox::indicator { width: 13px; height: 13px; }
QCheckBox::indicator:unchecked { background: #1e1e1e; border: 1px solid #4a4a4a; border-radius: 2px; }
QCheckBox::indicator:checked { background: #2d8ceb; border: 1px solid #2d8ceb; border-radius: 2px; }
QStatusBar { background: #252525; color: #909090; border-top: 1px solid #1a1a1a; }
QStatusBar::item { border: none; }
QLabel#title { color: #8a8a8a; font-weight: bold; padding: 6px 0 2px 0; }
QScrollBar:vertical { background: #252525; width: 10px; }
QScrollBar::handle:vertical { background: #4a4a4a; border-radius: 5px; min-height: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
"""

TOOLS = [
    ("brush", "画", "画笔蒙版 (B)"),
    ("eraser", "擦", "橡皮 (E)"),
    ("hand", "手", "抓手 / 空格拖拽 (H)"),
    ("zoom", "缩", "缩放 / 滚轮 (Z)"),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GC")
        self.resize(1440, 900)
        self.canvas = CanvasView(self)
        self.setCentralWidget(self.canvas)
        self._build_menu()
        self._build_toolbar()
        self._build_options()
        self._build_dock()
        self._build_status()
        self._wire()
        self.setStyleSheet(QSS)

    def _build_menu(self):
        mb = self.menuBar()
        m = mb.addMenu("文件")
        a = QAction("打开图像…", self); a.setShortcut(QKeySequence.Open)
        a.triggered.connect(self.open_image); m.addAction(a)
        a = QAction("保存结果…", self); a.setShortcut(QKeySequence.Save)
        a.triggered.connect(self.save_result); m.addAction(a)
        m.addSeparator()
        a = QAction("退出", self); a.setShortcut(QKeySequence.Quit)
        a.triggered.connect(self.close); m.addAction(a)

        m = mb.addMenu("编辑")
        a = QAction("撤销", self); a.setShortcut(QKeySequence.Undo)
        a.triggered.connect(self.canvas.undo); m.addAction(a)
        a = QAction("重做", self); a.setShortcut(QKeySequence.Redo)
        a.triggered.connect(self.canvas.redo); m.addAction(a)
        m.addSeparator()
        a = QAction("清空蒙版", self)
        a.triggered.connect(self.canvas.clear_mask); m.addAction(a)
        a = QAction("反选蒙版", self)
        a.triggered.connect(self.canvas.invert_mask); m.addAction(a)

        m = mb.addMenu("视图")
        a = QAction("适应窗口", self); a.setShortcut("Ctrl+0")
        a.triggered.connect(self.canvas.fit_view); m.addAction(a)
        a = QAction("实际像素", self); a.setShortcut("Ctrl+1")
        a.triggered.connect(lambda: self.canvas.zoom_to(1.0)); m.addAction(a)

    def _build_toolbar(self):
        tb = QToolBar("工具", self)
        tb.setOrientation(Qt.Vertical)
        tb.setMovable(False)
        tb.setIconSize(QSize(20, 20))
        tb.addSeparator()
        self.addToolBar(Qt.LeftToolBarArea, tb)

        self.tool_group = QActionGroup(self)
        self.tool_group.setExclusive(True)
        for key, glyph, tip in TOOLS:
            act = QAction(glyph, self)
            act.setToolTip(tip)
            act.setCheckable(True)
            act.setData(key)
            act.triggered.connect(lambda checked, k=key: self.set_tool(k))
            self.tool_group.addAction(act)
            tb.addAction(act)
            if key == "brush":
                act.setChecked(True)
        tb.addSeparator()

    def _build_options(self):
        ob = QToolBar("选项", self)
        ob.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, ob)

        self.tool_label = QLabel(" 画笔蒙版")
        self.tool_label.setMinimumWidth(84)
        ob.addWidget(self.tool_label)

        ob.addWidget(QLabel("大小"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(2, 400)
        self.size_slider.setValue(45)
        self.size_slider.setFixedWidth(150)
        ob.addWidget(self.size_slider)
        self.size_label = QLabel("45 px")
        self.size_label.setMinimumWidth(46)
        ob.addWidget(self.size_label)
        self.size_slider.valueChanged.connect(self.on_brush_size)

        ob.addSeparator()
        self.show_mask_cb = QCheckBox("显示蒙版")
        self.show_mask_cb.setChecked(True)
        self.show_mask_cb.toggled.connect(lambda v: self.canvas.set_mask_visible(v))
        ob.addWidget(self.show_mask_cb)

        ob.addSeparator()
        ob.addWidget(QLabel("选区"))
        self.region_label = QLabel("无")
        ob.addWidget(self.region_label)

    def _build_dock(self):
        dock = QDockWidget("创作", self)
        dock.setFeatures(QDockWidget.DockWidgetMovable)
        dock.setMinimumWidth(300)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(8)

        t = QLabel("图层")
        t.setObjectName("title")
        lay.addWidget(t)
        self.layer_list = QListWidget()
        self.layer_list.setMaximumHeight(96)
        for name in ("生成结果", "原图", "蒙版"):
            it = QListWidgetItem("●  " + name)
            if name != "生成结果":
                it.setForeground(QColor("#c8c8c8"))
            else:
                it.setForeground(QColor("#6a6a6a"))
            self.layer_list.addItem(it)
        lay.addWidget(self.layer_list)

        t = QLabel("提示词")
        t.setObjectName("title")
        lay.addWidget(t)
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("描述要在蒙版区域生成什么，例如：\n一队纸飞机呈对角线编队飞行，拖曳青蓝色发光粒子尾迹…")
        self.prompt_edit.setMinimumHeight(92)
        lay.addWidget(self.prompt_edit)

        t = QLabel("参数")
        t.setObjectName("title")
        lay.addWidget(t)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(6)
        row = QHBoxLayout()
        self.ref_label = QLabel("未选择")
        self.ref_label.setStyleSheet("color:#7a7a7a;")
        btn_ref = QPushButton("参考图…")
        btn_ref.setFixedWidth(74)
        btn_ref.clicked.connect(self.pick_reference)
        row.addWidget(self.ref_label, 1)
        row.addWidget(btn_ref)
        form.addRow("素材", row)

        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(1, 50)
        self.steps_spin.setValue(4)
        form.addRow("步数", self.steps_spin)

        self.cfg_spin = QDoubleSpinBox()
        self.cfg_spin.setRange(0.0, 10.0)
        self.cfg_spin.setSingleStep(0.5)
        self.cfg_spin.setValue(1.0)
        form.addRow("CFG", self.cfg_spin)
        lay.addLayout(form)

        self.btn_gen = QPushButton("生成")
        self.btn_gen.setObjectName("primary")
        self.btn_gen.setMinimumHeight(34)
        self.btn_gen.clicked.connect(self.on_generate)
        lay.addWidget(self.btn_gen)

        self.btn_apply = QPushButton("应用结果")
        self.btn_apply.setEnabled(False)
        lay.addWidget(self.btn_apply)

        lay.addStretch(1)
        dock.setWidget(body)

    def _build_status(self):
        sb = self.statusBar()
        self.sb_zoom = QLabel("缩放 100%")
        self.sb_pos = QLabel("0, 0")
        self.sb_mask = QLabel("蒙版 0%")
        self.sb_engine = QLabel("● 引擎未启动")
        self.sb_engine.setStyleSheet("color:#e0a030;")
        for w in (self.sb_zoom, self.sb_pos, self.sb_mask):
            sb.addPermanentWidget(self._sep())
            sb.addPermanentWidget(w)
        sb.addPermanentWidget(self._sep())
        sb.addPermanentWidget(self.sb_engine)

    def _sep(self):
        lbl = QLabel("│")
        lbl.setStyleSheet("color:#3f3f3f;")
        return lbl

    def _wire(self):
        self.canvas.zoomChanged.connect(self.on_zoom)
        self.canvas.cursorMoved.connect(self.on_cursor)
        self.canvas.maskChanged.connect(self.on_mask_changed)

    # ---------- 槽 ----------
    def set_tool(self, key):
        self.canvas.tool = key
        names = {"brush": "画笔蒙版", "eraser": "橡皮", "hand": "抓手", "zoom": "缩放"}
        self.tool_label.setText(" " + names.get(key, key))

    def on_brush_size(self, v):
        self.canvas.brush_size = v
        self.size_label.setText(f"{v} px")

    def on_zoom(self, z):
        self.sb_zoom.setText(f"缩放 {z * 100:.0f}%")

    def on_cursor(self, x, y):
        if 0 <= x < (self.canvas.image.width() if self.canvas.image else 0):
            self.sb_pos.setText(f"{x}, {y}")

    def on_mask_changed(self):
        b = self.canvas.mask_bounds()
        if b is None:
            self.region_label.setText("无")
            self.sb_mask.setText("蒙版 0%")
            return
        self.region_label.setText(f"{int(b.width())}×{int(b.height())}")
        self.sb_mask.setText(f"蒙版 {self.canvas.mask_ratio() * 100:.1f}%")

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开图像", "", "图像 (*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.webp)")
        if not path:
            return
        if self.canvas.load_image(path):
            self.setWindowTitle(f"GC — {os.path.basename(path)}")
            self.statusBar().showMessage(f"已打开 {path}", 4000)
        else:
            QMessageBox.warning(self, "打开失败", "无法读取该图像。")

    def pick_reference(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择参考图", "", "图像 (*.png *.jpg *.jpeg *.webp)")
        if path:
            self.ref_label.setText(os.path.basename(path))
            self.ref_label.setStyleSheet("color:#c8c8c8;")
            self._ref_path = path

    def save_result(self):
        if self.canvas.image is None:
            QMessageBox.information(self, "提示", "还没有打开图像。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存结果", "", "PNG (*.png)")
        if not path:
            return
        ext = ".png" if not os.path.splitext(path)[1] else ""
        if ext and not path.lower().endswith(".png"):
            path += ".png"
        if self.canvas.image.save(path):
            self.statusBar().showMessage(f"已保存 {path}", 5000)
        else:
            QMessageBox.warning(self, "保存失败", "写入文件失败。")

    def on_generate(self):
        if self.canvas.image is None:
            QMessageBox.information(self, "提示", "请先打开一张图像。")
            return
        b = self.canvas.mask_bounds()
        if b is None:
            QMessageBox.information(self, "提示", "请先用画笔涂出要生成/修改的区域。")
            return
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.information(self, "提示", "请先写提示词。")
            return
        QMessageBox.information(
            self, "选区就绪",
            f"蒙版区域：{int(b.width())} × {int(b.height())} px\n"
            f"占画面 {self.canvas.mask_ratio() * 100:.1f}%\n"
            f"步数 {self.steps_spin.value()}，CFG {self.cfg_spin.value():.1f}\n\n"
            "引擎尚未接上，下一步接 ComfyUI 后此按钮会真正出图。")


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName("GC")
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
