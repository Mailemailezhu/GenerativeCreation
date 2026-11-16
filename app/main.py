"""GC：本地 AI 图像创作工作台。"""
import os
import shutil
import subprocess
import sys

import bootstrap  # 先定缩放再碰 PyQt5：Qt 加载时就读 QT_SCALE_FACTOR

from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QCheckBox, QComboBox,
                             QDockWidget, QFrame,
                             QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
                             QLabel, QMainWindow, QMessageBox, QProgressBar, QPushButton,
                             QScrollArea, QSizePolicy, QSlider, QSpinBox, QTextEdit, QToolBar, QVBoxLayout,
                             QWidget)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)
from core import paths
ROOT = paths.root()
UI_SCALE = bootstrap.apply()
UI_FONT = bootstrap.font_size()
DATA = os.path.join(ROOT, "data")
MODELS = os.path.join(ROOT, "models")
API_PATH = os.path.join(ROOT, "config", "api_models.json")
ENGINE_PY = os.path.join(ROOT, "engine", "venv", "Scripts", "python.exe")
ENGINE_ARGS = [os.path.join("engine", "ComfyUI", "main.py"),
               "--listen", "127.0.0.1", "--port", "8188",
               "--extra-model-paths-config", os.path.join("config", "extra_model_paths.yaml"),
               "--fast-disk"]  # 三块盘都是 NVMe，权重直接从磁盘流式加载
os.makedirs(DATA, exist_ok=True)

from core import (apimodels, cache, catalog, exporter, hints, hwprobe, lrc, pipeline,
                  prompt_tools, uiconf)
from core.comfy_client import ComfyClient
from core.comfy_ws import ProgressWatcher
from ui.api_page import ApiPage
from ui.canvas import CanvasView
from ui.cards import AssetStrip, SourceCard
from ui.export_dialog import ExportDialog
from ui.model_list import ModelList
from ui.model_page import ModelPage
from ui.gear_button import GearButton
from ui.options_bar import OptionsBar
from ui.preview_settings import PreviewSettings
from ui.sidebar import SideRail
from ui.worker import EngineProbe, EngineStarter, GenWorker

_QSS = """
QMainWindow, QDialog { background: #2d2d2d; }
QWidget { background: #2d2d2d; color: #d0d0d0;
    font-family: "Microsoft YaHei UI", "Segoe UI"; font-size: $FSpx; }
QLabel, QCheckBox, QToolBar QLabel, QToolBar QCheckBox { background: transparent; }
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
    background: transparent; border: 1px solid #3f3f3f; border-radius: 3px;
    padding: 4px; color: #d0d0d0; selection-background-color: #2d8ceb; }
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #2d8ceb; }
QTextEdit { background: transparent; }
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
QSpinBox:disabled, QDoubleSpinBox:disabled {
    color: #5f5f5f; background: #242424; border-color: #333333; }
QPushButton { background: #3a3a3a; border: 1px solid #4a4a4a; border-radius: 3px;
    padding: 6px 10px; color: #d0d0d0; }
QPushButton:hover { background: #454545; }
QPushButton#primary { background: #2d8ceb; border: none; color: #ffffff; font-weight: bold; }
QPushButton#primary:hover { background: #3d9cfb; }
QPushButton#primary:disabled { background: #444444; color: #888888; }
QLabel#title { color: #8a8a8a; font-weight: bold; padding: 6px 0 2px 0; }
QLabel#hint { color: #6a6a6a; font-size: $FS2px; }
QLabel#est { color: #7a7a7a; font-size: $FS2px; }
QPushButton#ghost { background: transparent; border: 1px solid #4a4a4a; color: #b8b8b8;
    padding: 3px 10px; border-radius: 5px; font-size: $FS2px; }
QPushButton#ghost:hover { background: #3a3a3a; color: #e6e6e6; }
QPushButton#ghost:disabled { color: #5a5a5a; border-color: #3a3a3a; }
QPushButton#seg { background: transparent; border: 1px solid #4a4a4a; border-radius: 4px;
    padding: 4px 10px; color: #b0b0b0; }
QPushButton#seg:hover { background: #3a3a3a; }
QPushButton#seg:checked { background: #2d8ceb; border-color: #2d8ceb; color: #ffffff; }
QPushButton#seg:disabled { color: #4f4f4f; border-color: #333333; }
QFrame#srcCard { background: rgba(255, 255, 255, 18); border: 1px solid #3f3f3f; border-radius: 8px; }
QFrame#srcCard:hover { background: rgba(255, 255, 255, 32); border-color: #5a5a5a; }
QPushButton#collapse { background: transparent; border: none; color: #8a8a8a;
    font-weight: bold; text-align: left; padding: 6px 0 2px 0; }
QPushButton#collapse:hover { color: #d0d0d0; }
QLabel#srcThumb { background: #1a1a1a; border-radius: 6px; }
QLabel#srcName { color: #e2e2e2; font-weight: bold; }
QLabel#srcMeta { color: #787878; font-size: $FS2px; }
QSlider::groove:horizontal { height: 3px; background: #1a1a1a; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #4a4a4a; border-radius: 2px; }
QSlider::handle:horizontal { width: 11px; margin: -5px 0; border-radius: 5px; background: #a0a0a0; }
QSlider::handle:horizontal:hover { background: #c8c8c8; }
QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item { padding: 5px 6px; border-radius: 3px; }
QListWidget::item:selected { background: #2d8ceb; color: #ffffff; }
QCheckBox::indicator { width: 13px; height: 13px; }
QCheckBox::indicator:unchecked { background: #1e1e1e; border: 1px solid #4a4a4a; border-radius: 2px; }
QCheckBox::indicator:checked { background: #2d8ceb; border: 1px solid #2d8ceb; border-radius: 2px; }
QScrollBar:vertical { background: transparent; width: 9px; margin: 0; }
QScrollBar::handle:vertical { background: #4a4a4a; min-height: 26px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #5f5f5f; }
QScrollBar:horizontal { background: transparent; height: 9px; margin: 0; }
QScrollBar::handle:horizontal { background: #4a4a4a; min-width: 26px; border-radius: 4px; }
QScrollBar::handle:horizontal:hover { background: #5f5f5f; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QStatusBar { background: #252525; color: #909090; border-top: 1px solid #1a1a1a; }
QStatusBar::item { border: none; }
QProgressBar#gen { background: #1e1e1e; border: none; border-radius: 4px; }
QProgressBar#gen::chunk { background: #2d8ceb; border-radius: 4px; }
QLabel#dockTitle { background: #252525; color: #9a9a9a; font-weight: bold; padding: 7px 0 5px 10px; }
QWidget#rail { background: #252525; }
QWidget#optionsBar { background: #252525; }
QFrame#vline { background: #3a3a3a; }
QFrame#railLine { background: #3a3a3a; border: none; }
QPushButton#tool { background: transparent; border: 1px solid transparent; border-radius: 5px;
    padding: 0; color: #b8b8b8; font-size: $FSpx; }
QPushButton#tool:hover { background: #3a3a3a; color: #e6e6e6; }
QPushButton#tool:checked { background: #2d8ceb; border-color: #2d8ceb; color: #ffffff; }
QPushButton#railseg { background: transparent; border: 1px solid #4a4a4a; border-radius: 5px;
    padding: 0; color: #b0b0b0; font-size: $FS2px; }
QPushButton#railseg:hover { background: #3a3a3a; }
QPushButton#railseg:checked { background: #2d8ceb; border-color: #2d8ceb; color: #ffffff; }
QPushButton#railseg:disabled { color: #4f4f4f; border-color: #333333; }
"""


def qss(font=UI_FONT):
    """字号来自 config/ui.json；只重刷样式表就能改，不用重启。"""
    return _QSS.replace("$FS2", str(max(9, font - 2))).replace("$FS", str(font))

HINTS = hints.load()  # 界面文案全部来自 config/hints.xml，缺项回落 hints.DEFAULT
TOOLS = HINTS["tools"]
TIPS = HINTS["tips"]
UI = HINTS["ui"]



def _grow(slider, minimum=80):
    """滑块按剩余宽度伸缩：固定像素宽在换界面缩放后会顶爆整行。"""
    slider.setMinimumWidth(minimum)
    slider.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed))
    return slider


TOOL_KEYS = {"brush": "B", "eraser": "E", "rect": "M", "wand": "W",
             "quick": "Q", "hand": "H", "zoom": "Z"}

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
    "denoise": ("融合强度 = 正式图重绘时保留原图的程度（denoise）。\n"
                  "1.0 = 蒙版内完全重画，最像模型原图，但风格容易和周围不同；\n"
                  "0.6~0.8 会保留原片的颗粒、光线和质感，融得更自然，代价是造型自由度下降。\n"
                  "预览档永远是 1.0，这个只影响「应用预览并生成正式图」。"),
    "feather": ("羽化 = 蒙版边缘的过渡宽度（像素）。自动按选区短边的 6% 算。\n"
                "太大把周围原图也抹模糊，太小会看到硬边。24 MP 的照片一般 10~16 就够。"),
    "seed": "种子＝随机数起点。固定一个数字，同样的蒙版和提示词就能复现同一张图；保持「随机」则每次都不一样。想微调某张结果时先把它记下来。",
    "cmatch": "贴回前把生成片段的整体色调统计对齐到蒙版外的原图（LAB 均值与标准差）。关掉它颜色会更贴提示词，但和周围天空/皮肤的色温容易不一样。",
    "assets": ("素材图：可缺省，也可以放好几张。\n"
               "模型只有三个参考图槽位，多张素材会自动拼成一张，按从左到右、从上到下排列。"),
    "norm": "把口语化的描述整理成更贴近 AI 提示词的写法；本地模型不在时用规则整理。",
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GC")
        self.font_px = UI_FONT
        scr = QApplication.primaryScreen().availableGeometry()
        self.resize(min(1440, int(scr.width() * 0.94)),
                    min(900, int(scr.height() * 0.94)))
        self.canvas = CanvasView(self)
        # 参数栏放在中心布局里，才能和画布一起按窗口宽度分配空间；QToolBar 不参与拉伸
        self.opts = OptionsBar()
        central = QWidget(self)
        cv = QVBoxLayout(central)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)
        cv.addWidget(self.opts)
        cv.addWidget(self.canvas, 1)
        self.setCentralWidget(central)
        # LrC 传进来的是导出副本路径，解码后的像素和它分开记
        self._lrc_source = None
        self._src_orig = None
        # 原图、当前图、预览图都只在内存里，不落任何中间文件
        self._orig_pil = None
        self._cur_pil = None
        self._draft_pil = None
        self._clean_tmp()
        self._busy = False
        self._engine_ok = False
        self._engine_proc = None
        self._pending = None
        self._worker = None
        # 预览档按原图长边等比缩放的百分比，0.10 就是 10%
        self.preview_ratio = 0.10
        self.model_id = None
        self.watcher = ProgressWatcher()
        self.watcher.progress.connect(self.on_progress)
        self._build_menu()
        self._build_toolbar()
        self._build_options()
        self._build_dock()
        self._build_status()
        self._wire()
        self.setStyleSheet(qss(UI_FONT))
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
        a = QAction("启动本地引擎", self)
        a.triggered.connect(self.launch_engine)
        m.addAction(a)
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
        m.addSeparator()
        sub = m.addMenu("查看")
        for text, mode, sc in (("编辑蒙版", "edit", "Ctrl+Alt+0"),
                               ("原图与预览对比", "split", "Ctrl+Alt+1"),
                               ("仅原图", "original", "Ctrl+Alt+2"),
                               ("仅预览", "result", "Ctrl+Alt+3")):
            a = QAction(text, self)
            a.setShortcut(sc)
            a.triggered.connect(lambda _=False, mm=mode: self.on_view_mode(mm))
            sub.addAction(a)
        a = QAction("切换分割线方向", self)
        a.setShortcut("Ctrl+Alt+X")
        a.triggered.connect(self.on_split_axis)
        sub.addAction(a)
        m = mb.addMenu("选项")
        self.font_menu = m.addMenu("字体大小")
        self.font_group = QActionGroup(self)
        self.font_group.setExclusive(True)
        for px in (11, 12, 13, 14, 16, 18):
            a = QAction("%d px" % px, self)
            a.setCheckable(True)
            a.setChecked(px == self.font_px)
            a.triggered.connect(lambda _=False, p=px: self.set_font(p))
            self.font_group.addAction(a)
            self.font_menu.addAction(a)
        m.addSeparator()
        sm = m.addMenu("界面缩放")
        for pct in (100, 125, 150, 175):
            a = QAction("%d%%" % pct, self)
            a.triggered.connect(lambda _=False, p=pct: self.set_ui_scale(p))
            sm.addAction(a)
        a = QAction("恢复默认（%d%%）" % round(uiconf.DEFAULT * 100), self)
        a.triggered.connect(lambda: self.set_ui_scale(uiconf.DEFAULT))
        sm.addAction(a)

    def _build_toolbar(self):
        # 左侧用无框 QDockWidget 装自定义控件：竖向 QToolBar 只按 sizeHint 给高度，
        # 底部的原图/对比/预览贴不到窗口底边
        dock = QDockWidget("", self)
        dock.setObjectName("railDock")
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        empty = QWidget()
        empty.setFixedHeight(0)
        dock.setTitleBarWidget(empty)
        self.rail = SideRail(TOOLS, views=HINTS["views"], axis_tip=UI["axis"])
        self.rail.toolPicked.connect(self.set_tool)
        self.rail.viewPicked.connect(self.on_view_mode)
        self.rail.axisPicked.connect(self.on_split_axis)
        dock.setWidget(self.rail)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        # 快捷键挂在窗口上：按钮不再是 QAction，仍要能按 B/M/W… 切工具
        for key, sc in TOOL_KEYS.items():
            a = QAction(self)
            a.setShortcut(sc)
            a.triggered.connect(lambda _=False, k=key: self.set_tool(k))
            self.addAction(a)

    def _build_options(self):
        ob = self.opts
        self.tool_label = QLabel("画笔蒙版")
        self.tool_label.setMinimumWidth(84)
        ob.add_widget(self.tool_label)

        # 画笔组：只有画笔 / 橡皮 / 快速选择用得到，抓手和缩放时整组隐藏
        self.grp_brush = QWidget()
        gb = QHBoxLayout(self.grp_brush)
        gb.setContentsMargins(0, 0, 0, 0)
        gb.setSpacing(6)
        gb.addWidget(QLabel("大小"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(2, 400)
        self.size_slider.setValue(45)
        _grow(self.size_slider)
        gb.addWidget(self.size_slider, 3)
        self.size_label = QLabel("45 px")
        self.size_label.setMinimumWidth(46)
        gb.addWidget(self.size_label)
        self.size_slider.valueChanged.connect(self.on_brush_size)
        gb.addWidget(QLabel("硬度"))
        self.hard_slider = QSlider(Qt.Horizontal)
        self.hard_slider.setRange(0, 100)
        self.hard_slider.setValue(80)
        _grow(self.hard_slider)
        self.hard_slider.setToolTip(UI["brush_hard"])
        self.hard_slider.valueChanged.connect(self.on_hardness)
        gb.addWidget(self.hard_slider, 2)
        self.hard_label = QLabel("80%")
        self.hard_label.setMinimumWidth(42)
        gb.addWidget(self.hard_label)
        gb.addWidget(QLabel("不透明度"))
        self.op_slider = QSlider(Qt.Horizontal)
        self.op_slider.setRange(5, 100)
        self.op_slider.setValue(100)
        _grow(self.op_slider)
        self.op_slider.setToolTip(UI["brush_opacity"])
        self.op_slider.valueChanged.connect(self.on_opacity)
        gb.addWidget(self.op_slider, 2)
        self.op_label = QLabel("100%")
        self.op_label.setMinimumWidth(42)
        gb.addWidget(self.op_label)
        self.act_brush = ob.add_widget(self.grp_brush, 3)

        # 容差组：魔棒与快速选择按颜色吸附，容差决定吸多宽
        self.grp_tol = QWidget()
        gt = QHBoxLayout(self.grp_tol)
        gt.setContentsMargins(0, 0, 0, 0)
        gt.setSpacing(6)
        gt.addWidget(QLabel("容差"))
        self.tol_spin = QSpinBox()
        self.tol_spin.setRange(1, 255)
        self.tol_spin.setValue(32)
        self.tol_spin.setFixedWidth(62)
        self.tol_spin.setToolTip(UI["tolerance"])
        self.tol_spin.valueChanged.connect(self.on_tolerance)
        gt.addWidget(self.tol_spin)
        self.act_tol = ob.add_widget(self.grp_tol)

        # 选区组：羽化与加减模式，所有选区类工具共用，抓手/缩放时隐藏
        self.grp_sel = QWidget()
        gs = QHBoxLayout(self.grp_sel)
        gs.setContentsMargins(0, 0, 0, 0)
        gs.setSpacing(6)
        self.btn_feather = QPushButton("羽化选区")
        self.btn_feather.setToolTip(UI["feather_btn"])
        self.btn_feather.clicked.connect(self.on_feather_mask)
        gs.addWidget(self.btn_feather)
        gs.addWidget(QLabel("模式"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["添加", "减去"])
        self.mode_combo.setFixedWidth(64)
        self.mode_combo.setToolTip(UI["mode"])
        self.mode_combo.currentIndexChanged.connect(self.on_brush_mode)
        gs.addWidget(self.mode_combo)
        self.act_sel = ob.add_widget(self.grp_sel, 1)
        ob.add_sep()
        self.show_mask_cb = QCheckBox("显示蒙版")
        self.show_mask_cb.setChecked(True)
        self.show_mask_cb.setToolTip(UI["show_mask"])
        self.show_mask_cb.toggled.connect(lambda v: self.canvas.set_mask_visible(v))
        ob.add_widget(self.show_mask_cb)
        ob.add_sep()
        ob.add_widget(QLabel("选区"))
        self.region_label = QLabel("无")
        ob.add_widget(self.region_label)

        # 缩放组：只有缩放工具时出现，给 PS 那种「适应窗口」
        ob.add_sep()
        self.grp_zoom = QWidget()
        gz = QHBoxLayout(self.grp_zoom)
        gz.setContentsMargins(0, 0, 0, 0)
        gz.setSpacing(4)
        self.btn_zoom_in = QPushButton("放大")
        self.btn_zoom_out = QPushButton("缩小")
        self.btn_zoom_fit = QPushButton("适应窗口")
        self.btn_zoom_fit.setToolTip(UI["zoom_fit"])
        self.btn_zoom_in.clicked.connect(lambda: self.zoom_center(1.25))
        self.btn_zoom_out.clicked.connect(lambda: self.zoom_center(1 / 1.25))
        self.btn_zoom_fit.clicked.connect(self.canvas.fit_view)
        for b in (self.btn_zoom_in, self.btn_zoom_out, self.btn_zoom_fit):
            b.setObjectName("ghost")
            gz.addWidget(b)
        self.act_zoom = ob.add_widget(self.grp_zoom)
        ob.finish()
        self.set_tool("brush")

    def _build_dock(self):
        dock = QDockWidget("创作", self)
        dock.setFeatures(QDockWidget.DockWidgetMovable)
        dock.setMinimumWidth(370)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(0, 0, 8, 0)
        lay.setSpacing(6)

        self.model_head = QPushButton("▸ 模型")
        self.model_head.setObjectName("collapse")
        self.model_head.setCheckable(True)
        self.model_head.setToolTip(UI["model_head"])
        self.model_head.toggled.connect(self.on_model_toggle)
        lay.addWidget(self.model_head)
        self.model_list = ModelList()
        self.model_list.addRequested.connect(self.open_model_page)
        self.model_list.modelSelected.connect(self.on_model_selected)
        self.model_list.setVisible(False)
        lay.addWidget(self.model_list)
        lay.addSpacing(8)

        lay.addWidget(self._section("原始图"))
        self.src_card = SourceCard()
        self.src_card.clicked.connect(self.open_image)
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

        # 所有会改生成结果的数字都收进这里：默认值已经配好 4 步 LoRA，平时只调提示词和蒙版
        self.adv_head = QPushButton("▸ 高级设置")
        self.adv_head.setObjectName("collapse")
        self.adv_head.setCheckable(True)
        self.adv_head.setToolTip(UI["adv_head"])
        self.adv_head.toggled.connect(self.on_adv_toggle)
        lay.addWidget(self.adv_head)

        self.adv_box = QWidget()
        af = QFormLayout(self.adv_box)
        af.setContentsMargins(0, 2, 0, 4)
        af.setLabelAlignment(Qt.AlignRight)
        af.setSpacing(6)
        self.denoise_spin = QDoubleSpinBox()
        self.denoise_spin.setRange(0.30, 1.00)
        self.denoise_spin.setSingleStep(0.05)
        self.denoise_spin.setValue(1.00)
        self.denoise_spin.setToolTip(TIPS["denoise"])
        af.addRow(self._tip("融合强度", TIPS["denoise"]), self.denoise_spin)
        self.feather_spin = QSpinBox()
        self.feather_spin.setRange(0, 80)
        self.feather_spin.setValue(0)
        self.feather_spin.setSpecialValueText("自动")
        self.feather_spin.setToolTip(TIPS["feather"])
        af.addRow(self._tip("羽化", TIPS["feather"]), self.feather_spin)
        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(1, 50)
        self.steps_spin.setValue(4)
        self.steps_spin.setToolTip(TIPS["steps"])
        self.steps_spin.valueChanged.connect(self.on_steps_changed)
        af.addRow(self._tip("步数", TIPS["steps"]), self.steps_spin)
        self.cfg_spin = QDoubleSpinBox()
        self.cfg_spin.setRange(0.0, 10.0)
        self.cfg_spin.setSingleStep(0.1)
        self.cfg_spin.setValue(1.0)
        self.cfg_spin.setToolTip(TIPS["cfg"])
        af.addRow(self._tip("CFG", TIPS["cfg"]), self.cfg_spin)
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(-1, 2 ** 31 - 1)
        self.seed_spin.setValue(-1)
        self.seed_spin.setSpecialValueText("随机")
        self.seed_spin.setToolTip(TIPS["seed"])
        af.addRow(self._tip("种子", TIPS["seed"]), self.seed_spin)
        self.cm_check = QCheckBox("对齐周围色彩")
        self.cm_check.setChecked(True)
        self.cm_check.setToolTip(TIPS["cmatch"])
        af.addRow(self._tip("调色", TIPS["cmatch"]), self.cm_check)
        self.adv_box.setVisible(False)
        lay.addWidget(self.adv_box)

        lay.addStretch(1)

        # 上半部分（模型/素材/文本/参数）比窗口高时滚动；生成与应用钉在底部，永远点得到
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(body)
        self.panel_scroll = scroll

        self.estimate_label = QLabel("")
        self.estimate_label.setObjectName("est")
        self.steps_spin.valueChanged.connect(self.on_steps_changed)
        self.on_steps_changed()

        self.btn_gen = GearButton("生成预览图")
        self.btn_gen.setMinimumHeight(34)
        self.btn_gen.setToolTip(TIPS["gen"])
        self.btn_gen.clicked.connect(self.on_generate)
        self.btn_gen.gearClicked.connect(self.open_preview_settings)
        self.btn_gen.gear.setToolTip(UI["preview_size"])

        self.btn_apply = QPushButton("应用预览并生成正式图")
        self.btn_apply.setEnabled(False)
        self.btn_apply.setToolTip(TIPS["apply"])
        self.btn_apply.clicked.connect(self.on_apply)

        self.btn_reset = QPushButton("复位图像")
        self.btn_reset.setMinimumHeight(26)
        self.btn_reset.setEnabled(False)
        self.btn_reset.setToolTip(UI["reset"])
        self.btn_reset.clicked.connect(self.on_reset)

        shell = QWidget()
        outer = QVBoxLayout(shell)
        outer.setContentsMargins(10, 8, 10, 14)
        outer.setSpacing(6)
        outer.addWidget(scroll, 1)
        outer.addWidget(self.estimate_label)
        outer.addWidget(self.btn_gen)
        outer.addWidget(self.btn_apply)
        outer.addWidget(self.btn_reset)
        dock.setWidget(shell)
        title = QLabel("创作")
        title.setObjectName("dockTitle")
        dock.setTitleBarWidget(title)

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
        self._update_model_head(entries)
        if hasattr(self, "steps_spin"):
            self._sync_param_state()

    def _update_model_head(self, entries=None):
        """折叠时把当前模型写在标题上，展开时只留「▾ 模型」。"""
        if entries is None:
            entries = [{"id": self.model_id, "name": "未选择"}] if self.model_id else []
        cur = next((e["name"] for e in entries if e.get("id") == self.model_id), "未选择")
        opened = self.model_head.isChecked()
        self.model_head.setText(("▾ 模型" if opened else "▸ 模型 · " + cur))

    def on_model_toggle(self, opened):
        self.model_list.setVisible(opened)
        self._update_model_head()

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
        self._engine_ok = bool(ok)
        if ok:
            self.sb_engine.setText("● 引擎就绪")
            self.sb_engine.setStyleSheet("color:#5cb85c;")
        else:
            self.sb_engine.setText("● 引擎未启动")
            self.sb_engine.setStyleSheet("color:#e0a030;")

    def launch_engine(self):
        """手动或用例触发时拉起 ComfyUI；已起过就直接复用。"""
        if self._engine_proc and self._engine_proc.poll() is None:
            return True
        try:  # 界面上还没刷新到「就绪」时也别重复拉第二个引擎
            if ComfyClient().is_up():
                self._engine_ok = True
                return True
        except Exception:
            pass
        if not os.path.exists(ENGINE_PY):
            QMessageBox.warning(self, "启动失败",
                                "找不到引擎的 Python：\n%s\n\n先运行 scripts/start-engine.ps1 完成首次安装。" % ENGINE_PY)
            return False
        flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
        log = open(os.path.join(DATA, "engine.log"), "ab")
        self._engine_proc = subprocess.Popen([ENGINE_PY] + ENGINE_ARGS, cwd=ROOT,
                                            creationflags=flags, stdout=log, stderr=log)
        return True

    def ensure_engine(self, kw, label):
        """远程 API 档不需要本地引擎；本地档引擎没起就先拉起来再生成。"""
        if kw.get("fn") is not None or self._engine_ok:
            self._start(kw, label)
            return
        if not self.launch_engine():
            return
        self._pending = (kw, label)
        self._busy = True
        self.btn_gen.setEnabled(False)
        self.btn_apply.setEnabled(False)
        self.pb.setValue(0)
        self.pb_label.setText("0%")
        self.pb.show()
        self.pb_label.show()
        self.statusBar().showMessage("正在启动本地引擎（首次加载约 40 秒）…")
        self._starter = EngineStarter()
        self._starter.result.connect(self.on_engine_ready)
        self._starter.start()

    def on_engine_ready(self, ok):
        self._busy = False
        pending, self._pending = self._pending, None
        if ok and pending:
            self.on_engine_state(True)
            self._start(pending[0], pending[1])
            return
        self.pb.hide()
        self.pb_label.hide()
        self.btn_gen.setEnabled(True)
        self.btn_apply.setEnabled(self._draft_pil is not None)
        self.statusBar().showMessage("引擎启动失败，详见 data/engine.log")
        QMessageBox.warning(self, "引擎启动失败",
                            "端口 8188 在 3 分钟内没有起来。\n日志：data/engine.log"
                            "\n首次使用请先运行 scripts/start-engine.ps1 装好依赖与模型。")

    def open_model_page(self):
        dlg = ModelPage(MODELS, self)
        dlg.exec_()
        self.refresh_models()

    def on_adv_toggle(self, on):
        self.adv_box.setVisible(on)
        self.adv_head.setText(("▾ " if on else "▸ ") + "高级设置")

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
        self.denoise_spin.setEnabled(local)
        self.feather_spin.setEnabled(local)
        self.seed_spin.setEnabled(local)
        self.cm_check.setEnabled(local)
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
        self.canvas.viewChanged.connect(self.on_view_changed)

    def set_tool(self, key):
        self.canvas.tool = key
        self.canvas.setCursor(Qt.CrossCursor if key in ("rect", "wand") else Qt.ArrowCursor)
        self.rail.set_tool(key)
        names = {"brush": "画笔蒙版", "eraser": "橡皮", "rect": "矩形选框",
                 "wand": "魔棒", "quick": "快速选择", "hand": "指针", "zoom": "缩放"}
        self.tool_label.setText(" " + names.get(key, key))
        # 抓手和缩放不看画笔参数，整组收起，选项栏跟着变窄
        # 直接 setVisible 控件会被工具栏的 QWidgetAction 又显示回来，只能关 action
        self.act_brush.setVisible(key in ("brush", "eraser", "quick"))
        self.act_tol.setVisible(key in ("wand", "quick"))
        self.act_sel.setVisible(key in ("brush", "eraser", "rect", "wand", "quick"))
        self.act_zoom.setVisible(key == "zoom")
        # 选区工具默认打开蒙版并切回原图，否则看不见自己在选哪里
        if key in ("brush", "eraser", "rect", "wand", "quick"):
            if not self.show_mask_cb.isChecked():
                self.show_mask_cb.setChecked(True)
            self.canvas.set_mask_visible(True)
            if self.canvas.has_result() and self.canvas.view_mode != "edit":
                self.canvas.set_view_mode("edit")
                self._sync_view_buttons("edit")

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

    def on_tolerance(self, v):
        self.canvas.tolerance = v

    def on_view_mode(self, mode):
        self.canvas.set_view_mode(mode)
        self._sync_view_buttons(mode)

    def on_view_changed(self, mode):
        self._sync_view_buttons(mode)
        self.rail.set_view_enabled(self.canvas.has_result())

    def _sync_view_buttons(self, mode):
        self.rail.sync_view(mode)

    def set_ui_scale(self, pct):
        # 0 表示跟随系统：bootstrap 看到 0 就不设 QT_SCALE_FACTOR
        uiconf.save(ROOT, scale=(0.0 if pct is None else pct / 100.0))
        tip = "跟随系统" if pct is None else "%d%%" % pct
        QMessageBox.information(self, "界面缩放",
                                "已设为 %s，重启 GC 后生效。\n当前窗口仍是旧比例，先关掉重开。" % tip)

    def set_font(self, px):
        """字号只影响样式表，改完立刻生效。"""
        self.font_px = int(px)
        uiconf.save(ROOT, font=self.font_px)
        self.setStyleSheet(qss(self.font_px))
        for a in self.font_menu.actions():
            a.setChecked(a.text() == "%d px" % self.font_px)

    def zoom_center(self, factor):
        self.canvas.zoom_at(self.canvas.viewport().rect().center(), factor)

    def on_split_axis(self):
        axis = "h" if self.canvas.split_axis == "v" else "v"
        self.canvas.set_split_axis(axis)
        self.rail.set_axis(axis)
        self.statusBar().showMessage(
            "分割线改成%s拖动" % ("左右" if axis == "v" else "上下"), 3000)

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
        self.btn_gen.setText("重新生成预览图" if self._draft_pil else "生成预览图")
        self.statusBar().showMessage(
            "预览大小 %.0f%%：送模型的 crop 长边约 %d px" % (r * 100, self._draft_side()), 5000)

    def _load_source(self, path, note=""):
        """TIFF/PSD 之类在这里解成 8 位 RGB 留在内存，画布只认 8 位 RGB。"""
        img, msg = cache.load(path)
        if img is None or not self.canvas.load_image(img):
            return False
        self._orig_pil = img
        self._cur_pil = img
        self._src_orig = path
        self.btn_reset.setEnabled(True)
        self.setWindowTitle("GC — %s" % os.path.basename(path))
        self.src_card.set_image(img, img.width, img.height, label=self._src_label())
        self._reset_buttons()
        self.statusBar().showMessage(note or msg, 8000)
        return True

    def _src_label(self):
        return os.path.basename(self._src_orig) if self._src_orig else "原始图"

    def _clean_tmp(self):
        """旧版本往 data 下写过蒙版、预览图和缓存 PNG，启动时顺手清掉。"""
        for name in ("_gc_mask.png", "_gc_preview.png"):
            p = os.path.join(DATA, name)
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
        for name in ("_gc_tmp", "cache"):
            shutil.rmtree(os.path.join(DATA, name), ignore_errors=True)

    def on_reset(self):
        """丢掉预览和正式图，回到刚打开的原始图像，蒙版一起清空。"""
        if self._orig_pil is None:
            return
        self._cur_pil = self._orig_pil
        self.canvas.clear_result()
        self.canvas.load_image(self._orig_pil)
        self.src_card.set_image(self._orig_pil, self._orig_pil.width,
                                 self._orig_pil.height, label=self._src_label())
        self.setWindowTitle("GC — %s" % self._src_label())
        self._reset_buttons()
        self.rail.set_view_enabled(False)
        self._sync_view_buttons("edit")
        self.statusBar().showMessage("已复位到原始图像", 5000)

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
        base = self._src_orig or os.path.join(DATA, "export.png")
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

    def on_generate(self):
        if self._busy:
            return
        if self.canvas.image is None or self._cur_pil is None:
            QMessageBox.information(self, "提示", "请先打开一张图像。")
            return
        if self.canvas.mask_bounds() is None:
            QMessageBox.information(self, "提示", "请先用画笔涂出要生成或修改的区域。")
            return
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.information(self, "提示", "请先写提示词。")
            return
        self.ensure_engine(self._gen_kw(prompt=prompt, stage="draft"), "预览")

    def on_apply(self):
        if self._busy or self._draft_pil is None:
            return
        self.ensure_engine(self._gen_kw(
            prompt=self.prompt_edit.toPlainText().strip(), stage="final"), "正式图")

    def _gen_kw(self, prompt, stage):
        """本地档和 API 档参数不同，在这里统一组装，避免两处各写一份。"""
        kw = dict(
            image=self._cur_pil,
            mask=self.canvas.mask_pil(),
            prompt=prompt,
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
                denoise=self.denoise_spin.value(),
                seed=self.seed_spin.value() if self.seed_spin.value() >= 0 else None,
                color_match=self.cm_check.isChecked(),
                cfg=self.cfg_spin.value(),
                draft_side=self._draft_side(),
                unet=self._unet(),
            )
            if stage == "final" and self._draft_pil is not None:
                kw["draft"] = self._draft_pil
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
        img = info.get("image")
        if img is None:
            self.on_gen_failed("管线没有返回图像")
            return
        if info.get("stage") == "draft":
            self._draft_pil = img
            self.btn_gen.setText("重新生成预览图")
            self.btn_gen.set_look(False)
            self.btn_apply.setEnabled(True)
            self._repolish(self.btn_apply, "primary")
            # 出图后不弹新窗口，直接在画布上做原图/预览对照（同 LrC 参考视图）
            if self.canvas.set_result(img):
                self.rail.set_view_enabled(True)
                self._sync_view_buttons("split")
            self.statusBar().showMessage("预览完成：拖动中间的分割线对比，满意后点应用", 10000)
        else:
            # 正式图回填画布，导出和下一轮创作都基于它
            self._cur_pil = img
            self.canvas.load_image(img)
            self.src_card.set_image(img, img.width, img.height, label=self._src_label())
            self.setWindowTitle("GC — %s" % self._src_label())
            self._reset_buttons()
            self.statusBar().showMessage("正式图已就绪：可以导出，或在蒙版上继续创作", 10000)

    def on_gen_failed(self, msg):
        self._busy = False
        self.watcher.stop()
        self._worker = None
        self.pb.hide()
        self.pb_label.hide()
        self.btn_gen.setEnabled(True)
        self.btn_apply.setEnabled(self._draft_pil is not None)
        QMessageBox.warning(self, "生成失败", msg)

    def _repolish(self, w, name):
        w.setObjectName(name)
        w.style().unpolish(w)
        w.style().polish(w)

    def _reset_buttons(self):
        self._draft_pil = None
        self.btn_gen.setText("生成预览图")
        self.btn_gen.set_look(True)
        self.btn_gen.setEnabled(True)
        self.btn_apply.setEnabled(False)
        self._repolish(self.btn_apply, "")


def main():
    # 缩放已经在 bootstrap 里按 ui.json 定好了，这里不能再动 DPI 属性：
    # 一旦开 AA_EnableHighDpiScaling，Qt 会在系统 175% 上再乘一次
    app = QApplication(sys.argv)
    app.setApplicationName("GC")
    icon = paths.asset("gc.ico")
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))
    w = MainWindow()
    if os.path.exists(icon):
        w.setWindowIcon(QIcon(icon))
    w.show()
    # LrC 的「编辑于」把导出副本的路径追加在命令行末尾
    files = [a for a in sys.argv[1:] if not a.startswith("-")]
    if files:
        w.open_from_lrc(files[0])
    # 打包后自检：能开窗、能拿到根目录，就说明资源与模型路径都没断
    if "--selftest" in sys.argv:
        def done():
            shot = os.path.join(DATA, "_selftest.png")
            w.grab().save(shot)
            with open(os.path.join(DATA, "_selftest.txt"), "w", encoding="utf-8") as f:
                f.write("SELFTEST_OK %s %s\n" % (ROOT, shot))
            print("SELFTEST_OK", ROOT, shot, flush=True)
            app.quit()
        QTimer.singleShot(1200, done)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()