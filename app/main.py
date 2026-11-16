"""GC：本地 AI 图像创作工作台。"""
import os
import sys

import numpy as np
from PIL import Image
from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QCheckBox, QComboBox,
                             QDockWidget,
                             QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
                             QLabel, QMainWindow, QMessageBox, QProgressBar, QPushButton,
                             QSlider, QSpinBox, QTextEdit, QToolBar, QVBoxLayout, QWidget)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)
ROOT = os.path.dirname(APP_DIR)
DATA = os.path.join(ROOT, "data")
MODELS = os.path.join(ROOT, "models")
API_PATH = os.path.join(ROOT, "config", "api_models.json")
os.makedirs(DATA, exist_ok=True)

from core import apimodels, cache, catalog, exporter, hwprobe, lrc, pipeline, prompt_tools
from core.comfy_ws import ProgressWatcher
from ui.api_page import ApiPage
from ui.canvas import CanvasView
from ui.cards import AssetStrip, SourceCard
from ui.export_dialog import ExportDialog
from ui.model_list import ModelList
from ui.model_page import ModelPage
from ui.gear_button import GearButton
from ui.preview import PreviewWindow
from ui.preview_settings import PreviewSettings
from ui.worker import EngineProbe, GenWorker

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
QSpinBox:disabled, QDoubleSpinBox:disabled {
    color: #5f5f5f; background: #242424; border-color: #333333; }
QPushButton { background: #3a3a3a; border: 1px solid #4a4a4a; border-radius: 3px;
    padding: 6px 10px; color: #d0d0d0; }
QPushButton:hover { background: #454545; }
QPushButton#primary { background: #2d8ceb; border: none; color: #ffffff; font-weight: bold; }
QPushButton#primary:hover { background: #3d9cfb; }
QPushButton#primary:disabled { background: #444444; color: #888888; }
QLabel#title { color: #8a8a8a; font-weight: bold; padding: 6px 0 2px 0; }
QLabel#hint { color: #6a6a6a; font-size: 11px; }
QLabel#est { color: #7a7a7a; font-size: 11px; }
QPushButton#ghost { background: transparent; border: 1px solid #4a4a4a; color: #b8b8b8;
    padding: 3px 10px; border-radius: 5px; font-size: 11px; }
QPushButton#ghost:hover { background: #3a3a3a; color: #e6e6e6; }
QPushButton#ghost:disabled { color: #5a5a5a; border-color: #3a3a3a; }
QFrame#srcCard { background: #262626; border: 1px solid #3a3a3a; border-radius: 8px; }
QLabel#srcThumb { background: #1a1a1a; border-radius: 6px; }
QLabel#srcName { color: #e2e2e2; font-weight: bold; }
QLabel#srcMeta { color: #787878; font-size: 11px; }
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
QProgressBar#gen { background: #1e1e1e; border: none; border-radius: 4px; }
QProgressBar#gen::chunk { background: #2d8ceb; border-radius: 4px; }
QScrollBar:vertical { background: #252525; width: 10px; }
QScrollBar::handle:vertical { background: #4a4a4a; border-radius: 5px; min-height: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
"""

TOOLS = [
    ("brush", "画", "画笔蒙版 (B)：在画面上涂出要重新生成的范围"),
    ("eraser", "擦", "橡皮 (E)：把涂到的蒙版擦掉"),
    ("hand", "手", "抓手 (H)：拖动画面，也可以按住空格拖"),
    ("zoom", "缩", "缩放 (Z)：滚轮以鼠标为中心放大缩小"),
]

TIPS = {
    "steps": ("采样步数：模型去噪迭代多少次。\n"
              "本机实测每步约 5 秒（RTX 5070 12GB + Q5 模型）。\n"
              "预览档 4 步约 20 秒采样；调到 8 步约 40 秒，画质提升有限。\n"
              "步数翻倍时间就翻倍，和显存无关。"),
    "cfg": ("CFG = 提示词引导强度（Classifier-Free Guidance）。\n"
            "数值越高越死板地贴提示词、色彩更硬；越低越自由。\n"
            "本工作流挂了 4 步加速 LoRA，CFG 必须保持 1.0，调高会过曝、发糊甚至崩图。"),
    "gen": ("先用低分辨率出一张预览：选区裁切后长边 512，约 20 秒。\n"
            "只看构图和效果，不代表最终画质；重新生成会覆盖上一张。"),
    "apply": ("把这张预览当作风格参考，用 原图 + 预览 + 素材图 三张参考重绘正式图。\n"
              "选区裁切后长边 2048，耗时约为预览的 4 到 5 倍。\n"
              "必须先有一张预览。"),
    "assets": ("素材图：可缺省，也可以放好几张。\n"
               "模型只有三个参考图槽位，多张素材会自动拼成一张，按从左到右、从上到下排列。"),
    "norm": "把口语化的描述整理成更贴近 AI 提示词的写法；本地模型不在时用规则整理。",
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GC")
        self.resize(1440, 900)
        self.canvas = CanvasView(self)
        self.setCentralWidget(self.canvas)
        # LrC 传进来的是导出副本路径，和实际打开的 PNG 分开记
        self._lrc_source = None
        self._source_png = None
        self._draft_path = None
        self._busy = False
        self._worker = None
        # 预览档按原图长边等比缩放的百分比，0.10 就是 10%
        self.preview_ratio = 0.10
        self._src_orig = None
        self.model_id = None
        self.preview = PreviewWindow(self)
        self.watcher = ProgressWatcher()
        self.watcher.progress.connect(self.on_progress)
        self._build_menu()
        self._build_toolbar()
        self._build_options()
        self._build_dock()
        self._build_status()
        self._wire()
        self.setStyleSheet(QSS)
        self.refresh_models()
        self._probe = None
        self._engine_timer = QTimer(self)
        self._engine_timer.timeout.connect(self.check_engine)
        self._engine_timer.start(6000)
        self.check_engine()

    def _build_menu(self):
        mb = self.menuBar()
        m = mb.addMenu("文件")
        for text, sc, slot in (("打开图像…", "Ctrl+O", self.open_image),
                               ("保存结果…", "Ctrl+S", self.save_result),
                               ("导出为…", "Ctrl+Shift+E", self.export_as)):
            a = QAction(text, self)
            a.setShortcut(sc)
            a.triggered.connect(slot)
            m.addAction(a)
        m.addSeparator()
        a = QAction("退出", self)
        a.setShortcut("Ctrl+Q")
        a.triggered.connect(self.close)
        m.addAction(a)

        m = mb.addMenu("编辑")
        for text, sc, slot in (("撤销", "Ctrl+Z", self.canvas.undo),
                               ("重做", "Ctrl+Y", self.canvas.redo)):
            a = QAction(text, self)
            a.setShortcut(sc)
            a.triggered.connect(slot)
            m.addAction(a)
        m.addSeparator()
        a = QAction("清空蒙版", self)
        a.triggered.connect(self.canvas.clear_mask)
        m.addAction(a)
        a = QAction("反选蒙版", self)
        a.triggered.connect(self.canvas.invert_mask)
        m.addAction(a)

        m = mb.addMenu("视图")
        a = QAction("适应窗口", self)
        a.setShortcut("Ctrl+0")
        a.triggered.connect(self.canvas.fit_view)
        m.addAction(a)
        a = QAction("实际像素", self)
        a.setShortcut("Ctrl+1")
        a.triggered.connect(lambda: self.canvas.zoom_to(1.0))
        m.addAction(a)

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
        ob.addWidget(QLabel("硬度"))
        self.hard_slider = QSlider(Qt.Horizontal)
        self.hard_slider.setRange(0, 100)
        self.hard_slider.setValue(80)
        self.hard_slider.setFixedWidth(96)
        self.hard_slider.setToolTip("笔刷边缘的软硬：100 是硬边，0 是整笔柔化（同 PS 的硬度）")
        self.hard_slider.valueChanged.connect(self.on_hardness)
        ob.addWidget(self.hard_slider)
        self.hard_label = QLabel("80%")
        self.hard_label.setMinimumWidth(42)
        ob.addWidget(self.hard_label)
        ob.addWidget(QLabel("不透明度"))
        self.op_slider = QSlider(Qt.Horizontal)
        self.op_slider.setRange(5, 100)
        self.op_slider.setValue(100)
        self.op_slider.setFixedWidth(90)
        self.op_slider.setToolTip("单笔最大浓度；调低后同一处反复涂抹才逐渐加深")
        self.op_slider.valueChanged.connect(self.on_opacity)
        ob.addWidget(self.op_slider)
        self.op_label = QLabel("100%")
        self.op_label.setMinimumWidth(42)
        ob.addWidget(self.op_label)
        ob.addWidget(QLabel("羽化"))
        self.feather_spin = QSpinBox()
        self.feather_spin.setRange(0, 80)
        self.feather_spin.setValue(0)
        self.feather_spin.setFixedWidth(62)
        self.feather_spin.setSpecialValueText("自动")
        self.feather_spin.setToolTip("生成时蒙版边缘的过渡宽度；自动 = 按选区短边的 6% 算。改完可点右侧按钮直接柔化蒙版")
        ob.addWidget(self.feather_spin)
        self.btn_feather = QPushButton("羽化选区")
        self.btn_feather.setToolTip("对当前蒙版本身做羽化，可 Ctrl+Z 撤销（同 PS 的选择 → 修改 → 羽化）")
        self.btn_feather.clicked.connect(self.on_feather_mask)
        ob.addWidget(self.btn_feather)
        ob.addWidget(QLabel("模式"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["添加", "减去"])
        self.mode_combo.setFixedWidth(64)
        self.mode_combo.setToolTip("添加 = 扩大选区；减去 = 从选区里擦掉")
        self.mode_combo.currentIndexChanged.connect(self.on_brush_mode)
        ob.addWidget(self.mode_combo)
        ob.addSeparator()
        self.show_mask_cb = QCheckBox("显示蒙版")
        self.show_mask_cb.setChecked(True)
        self.show_mask_cb.setToolTip("关掉后画布上只显示原图，用来检查生成效果")
        self.show_mask_cb.toggled.connect(lambda v: self.canvas.set_mask_visible(v))
        ob.addWidget(self.show_mask_cb)
        ob.addSeparator()
        ob.addWidget(QLabel("选区"))
        self.region_label = QLabel("无")
        ob.addWidget(self.region_label)

    def _build_dock(self):
        dock = QDockWidget("创作", self)
        dock.setFeatures(QDockWidget.DockWidgetMovable)
        dock.setMinimumWidth(360)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(6)

        lay.addWidget(self._section("模型"))
        self.model_list = ModelList()
        self.model_list.addRequested.connect(self.open_model_page)
        self.model_list.modelSelected.connect(self.on_model_selected)
        lay.addWidget(self.model_list)
        lay.addSpacing(8)

        lay.addWidget(self._section("原始图"))
        self.src_card = SourceCard()
        lay.addWidget(self.src_card)
        lay.addSpacing(8)

        head = QHBoxLayout()
        head.addWidget(self._section("素材图"))
        self.asset_hint = QLabel("可缺省")
        self.asset_hint.setObjectName("hint")
        self.asset_hint.setToolTip(TIPS["assets"])
        head.addWidget(self.asset_hint)
        head.addStretch(1)
        lay.addLayout(head)
        self.asset_strip = AssetStrip()
        self.asset_strip.setToolTip(TIPS["assets"])
        self.asset_strip.changed.connect(self.on_assets_changed)
        lay.addWidget(self.asset_strip)
        lay.addSpacing(8)

        head = QHBoxLayout()
        head.addWidget(self._section("文本"))
        head.addStretch(1)
        self.btn_norm = QPushButton("规范化")
        self.btn_norm.setObjectName("ghost")
        self.btn_norm.setToolTip(TIPS["norm"])
        self.btn_norm.clicked.connect(self.on_normalize_prompt)
        head.addWidget(self.btn_norm)
        lay.addLayout(head)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("描述要在蒙版区域生成什么，例如：一队发光的纸飞机呈对角线编队飞行，拖曳青蓝色粒子尾迹…")
        self.prompt_edit.setMinimumHeight(92)
        lay.addWidget(self.prompt_edit)
        lay.addSpacing(6)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setSpacing(6)
        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(1, 50)
        self.steps_spin.setValue(4)
        self.steps_spin.setToolTip(TIPS["steps"])
        form.addRow(self._tip("步数", TIPS["steps"]), self.steps_spin)
        self.cfg_spin = QDoubleSpinBox()
        self.cfg_spin.setRange(0.0, 10.0)
        self.cfg_spin.setSingleStep(0.5)
        self.cfg_spin.setValue(1.0)
        self.cfg_spin.setToolTip(TIPS["cfg"])
        form.addRow(self._tip("CFG", TIPS["cfg"]), self.cfg_spin)
        lay.addLayout(form)

        self.estimate_label = QLabel("")
        self.estimate_label.setObjectName("est")
        lay.addWidget(self.estimate_label)
        self.steps_spin.valueChanged.connect(self.on_steps_changed)
        self.on_steps_changed()

        self.btn_gen = GearButton("生成预览图")
        self.btn_gen.setMinimumHeight(34)
        self.btn_gen.setToolTip(TIPS["gen"])
        self.btn_gen.clicked.connect(self.on_generate)
        self.btn_gen.gearClicked.connect(self.open_preview_settings)
        self.btn_gen.gear.setToolTip("预览大小设置")
        lay.addWidget(self.btn_gen)

        self.btn_apply = QPushButton("应用预览并生成正式图")
        self.btn_apply.setEnabled(False)
        self.btn_apply.setToolTip(TIPS["apply"])
        self.btn_apply.clicked.connect(self.on_apply)
        lay.addWidget(self.btn_apply)

        lay.addStretch(1)
        dock.setWidget(body)

    def _section(self, text):
        lab = QLabel(text)
        lab.setObjectName("title")
        return lab

    def _tip(self, text, tip):
        lab = QLabel(text)
        lab.setToolTip(tip)
        return lab

    def refresh_models(self):
        try:
            entries = [e for e in catalog.evaluate(MODELS, hwprobe.summary(MODELS))
                       if e.get("state") == "installed"]
        except Exception:
            entries = []
        for it in apimodels.load(API_PATH):
            entries.append({"id": "api:" + apimodels.mask_key(it),
                            "name": "API · " + it.get("name", it.get("model", "未命名"))})
        ids = [e["id"] for e in entries]
        if not ids:
            self.model_id = None
        elif self.model_id not in ids:
            self.model_id = ids[0]
        self.model_list.set_models(entries, self.model_id)
        if hasattr(self, "steps_spin"):
            self._sync_param_state()

    def on_model_selected(self, mid):
        if mid == "@api":
            self.open_api_page()
            return
        if mid.startswith("api:"):
            item = self._api_item(mid)
            if item:
                self.model_id = mid
                self.statusBar().showMessage(
                    "已切换到远程方案：%s（%s）" % (item.get("name"), item.get("model")), 6000)
            self.refresh_models()
            return
        e = catalog.by_id(mid)
        if not e:
            return
        self.model_id = mid
        self.refresh_models()
        self.statusBar().showMessage("已切换主模型：%s（下一次生成生效）" % e["name"], 5000)

    def _api_item(self, mid=None):
        mid = mid or self.model_id or ""
        if not mid.startswith("api:"):
            return None
        for it in apimodels.load(API_PATH):
            if "api:" + apimodels.mask_key(it) == mid:
                return it
        return None

    def open_api_page(self):
        dlg = ApiPage(parent=self)
        if not dlg.exec_() or not dlg.item:
            self.refresh_models()
            return
        key = apimodels.mask_key(dlg.item)
        items = [it for it in apimodels.load(API_PATH) if apimodels.mask_key(it) != key]
        items.append(dlg.item)
        apimodels.save(API_PATH, items)
        self.model_id = "api:" + key
        self.refresh_models()
        self.statusBar().showMessage("已添加并选中 API 方案：%s" % dlg.item["name"], 6000)

    def _unet(self):
        e = catalog.by_id(self.model_id) if self.model_id else None
        return e["file"] if e else None

    def check_engine(self):
        if self._probe and self._probe.isRunning():
            return
        self._probe = EngineProbe()
        self._probe.result.connect(self.on_engine_state)
        self._probe.start()

    def on_engine_state(self, ok):
        if ok:
            self.sb_engine.setText("● 引擎就绪")
            self.sb_engine.setStyleSheet("color:#5cb85c;")
        else:
            self.sb_engine.setText("● 引擎未启动")
            self.sb_engine.setStyleSheet("color:#e0a030;")

    def open_model_page(self):
        dlg = ModelPage(MODELS, self)
        dlg.exec_()
        self.refresh_models()

    def on_assets_changed(self):
        n = len(self.asset_strip.paths())
        self.asset_hint.setText("可缺省" if n == 0 else "%d 张" % n)

    def on_steps_changed(self, *_):
        self._sync_param_state()

    def _sync_param_state(self):
        """本地档的步数/CFG/素材对远程接口没有意义，选中 API 方案时直接禁用，免得用户白调。"""
        local = self._api_item() is None
        self.steps_spin.setEnabled(local)
        self.cfg_spin.setEnabled(local)
        self.asset_strip.setEnabled(local)
        self.asset_strip.setToolTip("" if local else "远程接口只接受一张原图，素材图暂不参与")
        if not local:
            self.estimate_label.setText("预计：耗时与画质取决于远程服务")
            return
        s = self.steps_spin.value()
        self.estimate_label.setText("预计：预览约 %d 秒 · 正式图约 %d 秒"
                                    % (max(3, s * 5), max(8, s * 22)))

    def on_normalize_prompt(self):
        src = self.prompt_edit.toPlainText().strip()
        if not src:
            QMessageBox.information(self, "提示", "先写一句描述，再点规范化。")
            return
        self.btn_norm.setEnabled(False)
        self.btn_norm.setText("整理中…")
        QApplication.processEvents()
        try:
            out, how = prompt_tools.normalize(src)
            if out:
                self.prompt_edit.setPlainText(out)
                tip = "本地模型" if how == "llm" else "规则整理"
                self.statusBar().showMessage("规范化完成（%s）" % tip, 4000)
        finally:
            self.btn_norm.setText("规范化")
            self.btn_norm.setEnabled(True)

    def _build_status(self):
        sb = self.statusBar()
        self.sb_zoom = QLabel("缩放 100%")
        self.sb_pos = QLabel("0, 0")
        self.sb_mask = QLabel("蒙版 0%")
        self.pb = QProgressBar()
        self.pb.setObjectName("gen")
        self.pb.setRange(0, 100)
        self.pb.setTextVisible(False)
        self.pb.setFixedWidth(150)
        self.pb.setFixedHeight(8)
        self.pb.hide()
        self.pb_label = QLabel("")
        self.pb_label.setStyleSheet("color:#2d8ceb;")
        self.pb_label.hide()
        self.sb_engine = QLabel("● 引擎未启动")
        self.sb_engine.setStyleSheet("color:#e0a030;")
        for w in (self.sb_zoom, self.sb_pos, self.sb_mask):
            sb.addPermanentWidget(self._sep())
            sb.addPermanentWidget(w)
        sb.addPermanentWidget(self._sep())
        sb.addPermanentWidget(self.pb)
        sb.addPermanentWidget(self.pb_label)
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

    def set_tool(self, key):
        self.canvas.tool = key
        names = {"brush": "画笔蒙版", "eraser": "橡皮", "hand": "抓手", "zoom": "缩放"}
        self.tool_label.setText(" " + names.get(key, key))

    def on_brush_size(self, v):
        self.canvas.brush_size = v
        self.size_label.setText("%d px" % v)

    def on_zoom(self, z):
        self.sb_zoom.setText("缩放 %d%%" % (z * 100))

    def on_cursor(self, x, y):
        if self.canvas.image and 0 <= x < self.canvas.image.width():
            self.sb_pos.setText("%d, %d" % (x, y))

    def on_mask_changed(self):
        b = self.canvas.mask_bounds()
        if b is None:
            self.region_label.setText("无")
            self.sb_mask.setText("蒙版 0%")
            return
        self.region_label.setText("%d×%d" % (int(b.width()), int(b.height())))
        self.sb_mask.setText("蒙版 %.1f%%" % (self.canvas.mask_ratio() * 100))

    def on_hardness(self, v):
        self.canvas.hardness = v
        self.hard_label.setText("%d%%" % v)

    def on_opacity(self, v):
        self.canvas.opacity = v
        self.op_label.setText("%d%%" % v)

    def on_brush_mode(self, idx):
        self.canvas.brush_mode = "subtract" if idx == 1 else "add"

    def on_feather_mask(self):
        if self.canvas.image is None:
            return
        if self.canvas.mask_bounds() is None:
            QMessageBox.information(self, "提示", "蒙版是空的，先涂一点再羽化。")
            return
        px = self.feather_spin.value() or 12
        if self.canvas.apply_feather(px):
            self.statusBar().showMessage("已羽化 %.0f px（Ctrl+Z 可撤销）" % px, 4000)

    def _draft_side(self):
        """预览档送模型的 crop 长边。按原图长边乘比例，再夹到 256~2048。"""
        if self.canvas.image is None:
            return 512
        long_edge = max(self.canvas.image.width(), self.canvas.image.height())
        return max(256, min(2048, int(round(long_edge * self.preview_ratio))))

    def open_preview_settings(self):
        img = self.canvas.image
        size = (img.width(), img.height()) if img else (0, 0)
        pop = PreviewSettings(size, self.preview_ratio, self)
        pop.changed.connect(self.on_preview_ratio)
        br = self.btn_gen.mapToGlobal(self.btn_gen.rect().bottomRight())
        pop.move(br.x() - 272, br.y() + 6)
        pop.show()

    def on_preview_ratio(self, r):
        self.preview_ratio = r
        self.btn_gen.setText("重新生成预览图" if self._draft_path else "生成预览图")
        self.statusBar().showMessage(
            "预览大小 %.0f%%：送模型的 crop 长边约 %d px" % (r * 100, self._draft_side()), 5000)

    def _load_source(self, path, note=""):
        """TIFF/PSD 之类先转成无压缩 PNG 缓存再进画布，画布只认 8 位 RGB。"""
        png, msg = cache.ensure(path, os.path.join(DATA, "cache"))
        if not png or not self.canvas.load_image(png):
            return False
        self._source_png = png
        self._src_orig = path
        self.setWindowTitle("GC — %s" % os.path.basename(path))
        self.src_card.set_image(png, self.canvas.image.width(), self.canvas.image.height(),
                                 label=os.path.basename(path))
        self._reset_buttons()
        self.statusBar().showMessage(note or msg, 8000)
        return True

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开图像", "", "图像 (*.png *.jpg *.jpeg *.tif *.tiff *.psd *.bmp *.webp)")
        if not path:
            return
        if not self._load_source(path):
            QMessageBox.warning(self, "打开失败", "无法读取该图像。")

    def open_from_lrc(self, path):
        """从 LrC 的「编辑于」启动。外部编辑器的格式下拉没有 PNG，主流做法是给 TIFF。"""
        self._lrc_source = path
        src, msg = lrc.resolve(path)
        if not src:
            QMessageBox.information(self, "没有可用的图像", msg)
            self.statusBar().showMessage(
                "请在 LrC 用「编辑于 → 在外部编辑器中打开」，格式选 TIFF", 0)
            return
        if not self._load_source(src, msg):
            QMessageBox.warning(self, "打开失败", "LrC 传来的文件读不出来：\n" + src)

    def save_result(self):
        if self.canvas.image is None:
            QMessageBox.information(self, "提示", "还没有打开图像。")
            return
        start = ""
        if self._src_orig:
            start = os.path.splitext(self._src_orig)[0] + "-AI.png"
        path, _ = QFileDialog.getSaveFileName(self, "保存结果", start, "PNG (*.png)")
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        if self.canvas.image.save(path):
            self.statusBar().showMessage("已保存 %s" % path, 5000)
        else:
            QMessageBox.warning(self, "保存失败", "写入文件失败。")

    def export_as(self):
        if self.canvas.image is None:
            QMessageBox.information(self, "提示", "还没有打开图像。")
            return
        base = self._src_orig or self._source_png or os.path.join(DATA, "export.png")
        dlg = ExportDialog(self.canvas.image, os.path.dirname(base),
                           os.path.splitext(os.path.basename(base))[0], self)
        if not dlg.exec_():
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            n = exporter.save(self.canvas.image, dlg.path, dlg.fmt(), dlg.opts())
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "导出失败", str(e))
            return
        QApplication.restoreOverrideCursor()
        self.statusBar().showMessage("已导出 %s（%s）" % (dlg.path, exporter.human(n)), 8000)

    def _save_mask(self):
        """把画布上的蒙版落成灰度 PNG：Alpha8 的单通道就是蒙版值。"""
        a = self.canvas.mask_alpha()
        w, h = a.width(), a.height()
        buf = a.constBits().asstring(a.byteCount())
        arr = np.frombuffer(buf, np.uint8).reshape(h, a.bytesPerLine())[:, :w]
        path = os.path.join(DATA, "_gc_mask.png")
        Image.fromarray(arr.copy(), "L").save(path)
        return path

    def on_generate(self):
        if self._busy:
            return
        if self.canvas.image is None or not self._source_png:
            QMessageBox.information(self, "提示", "请先打开一张图像。")
            return
        if self.canvas.mask_bounds() is None:
            QMessageBox.information(self, "提示", "请先用画笔涂出要生成或修改的区域。")
            return
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.information(self, "提示", "请先写提示词。")
            return
        self._start(self._gen_kw(
            prompt=prompt,
            out_path=os.path.join(DATA, "_gc_preview.png"),
            stage="draft",
        ), "预览")

    def on_apply(self):
        if self._busy or not self._draft_path:
            return
        base = self._src_orig or os.path.join(DATA, "result.png")
        out = os.path.splitext(base)[0] + "-AI.png"
        self._start(self._gen_kw(
            prompt=self.prompt_edit.toPlainText().strip(),
            out_path=out,
            stage="final",
        ), "正式图")

    def _gen_kw(self, prompt, out_path, stage):
        """本地档和 API 档参数不同，在这里统一组装，避免两处各写一份。"""
        kw = dict(
            image_path=self._source_png,
            mask_path=self._save_mask(),
            prompt=prompt,
            out_path=out_path,
            stage=stage,
            feather=self.feather_spin.value() or None,
        )
        api = self._api_item()
        if api:
            kw["fn"] = pipeline.run_api
            kw["api"] = api
            kw["draft_side"] = self._draft_side()
        else:
            kw.update(
                asset_paths=tuple(self.asset_strip.paths()),
                steps=self.steps_spin.value(),
                cfg=self.cfg_spin.value(),
                draft_side=self._draft_side(),
                unet=self._unet(),
            )
            if stage == "final" and self._draft_path:
                kw["draft_path"] = self._draft_path
        return kw

    def _start(self, kw, label):
        self._busy = True
        self._label = label
        self.btn_gen.setEnabled(False)
        self.btn_apply.setEnabled(False)
        self.pb.setValue(0)
        self.pb_label.setText("0%")
        self.pb.show()
        self.pb_label.show()
        self.statusBar().showMessage("正在生成%s…" % label)
        self.watcher.start()
        fn = kw.pop("fn", None)
        self._worker = GenWorker(fn=fn, **kw)
        self._worker.progress.connect(self.on_progress)
        self._worker.done.connect(self.on_gen_done)
        self._worker.failed.connect(self.on_gen_failed)
        self._worker.start()

    def on_progress(self, pct, msg):
        pct = max(0, min(100, int(pct)))
        self.pb.setValue(pct)
        self.pb_label.setText("%d%%" % pct)
        self.pb_label.setToolTip(msg)
        self.statusBar().showMessage(msg)

    def on_gen_done(self, info):
        self._busy = False
        self.watcher.stop()
        self._worker = None
        self.pb.setValue(100)
        self.pb_label.setText("100%")
        QTimer.singleShot(3000, self.pb.hide)
        QTimer.singleShot(3000, self.pb_label.hide)
        self.btn_gen.setEnabled(True)
        out = info.get("out")
        if info.get("stage") == "draft":
            self._draft_path = out
            self.btn_gen.setText("重新生成预览图")
            self.btn_gen.set_look(False)
            self.btn_apply.setEnabled(True)
            self._repolish(self.btn_apply, "primary")
            self.preview.show_image(out, "预览")
            self.statusBar().showMessage("预览完成：%s" % out, 8000)
        else:
            # 正式图回填画布，导出和下一轮创作都基于它
            self.canvas.load_image(out)
            self._source_png = out
            self.src_card.set_image(out, self.canvas.image.width(), self.canvas.image.height())
            self.setWindowTitle("GC — %s" % os.path.basename(out))
            self._reset_buttons()
            self.preview.show_image(out, "正式图")
            self.statusBar().showMessage("正式图已保存：%s" % out, 10000)

    def on_gen_failed(self, msg):
        self._busy = False
        self.watcher.stop()
        self._worker = None
        self.pb.hide()
        self.pb_label.hide()
        self.btn_gen.setEnabled(True)
        self.btn_apply.setEnabled(bool(self._draft_path))
        QMessageBox.warning(self, "生成失败", msg)

    def _repolish(self, w, name):
        w.setObjectName(name)
        w.style().unpolish(w)
        w.style().polish(w)

    def _reset_buttons(self):
        self._draft_path = None
        self.btn_gen.setText("生成预览图")
        self.btn_gen.set_look(True)
        self.btn_gen.setEnabled(True)
        self.btn_apply.setEnabled(False)
        self._repolish(self.btn_apply, "")


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName("GC")
    w = MainWindow()
    w.show()
    # LrC 的「编辑于」把导出副本的路径追加在命令行末尾
    files = [a for a in sys.argv[1:] if not a.startswith("-")]
    if files:
        w.open_from_lrc(files[0])
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()