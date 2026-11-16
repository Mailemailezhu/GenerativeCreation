# GC — GenerativeCreation

本地 AI 图像创作工作台：ComfyUI 引擎 + PyQt5 画布，面向 Lightroom Classic 修图后的局部生成式创作。

## 目录

| 路径 | 说明 |
|---|---|
| `app/` | PyQt5 界面，独立虚拟环境 `app/venv` |
| `app/core/` | ComfyUI 客户端、局部重绘管线、模型目录、缓存、导出 |
| `engine/` | ComfyUI 引擎（submodule），独立虚拟环境 `engine/venv` |
| `models/` | 模型文件，不入库，由 `config/extra_model_paths.yaml` 挂载 |
| `config/` | 引擎与软件配置（`api_models.json` 含密钥，不入库） |
| `scripts/` | 启动脚本、冒烟脚本、本地 mock 接口 |
| `data/` | 运行数据与缓存，不入库 |

## 环境

- Python 3.12（uv 管理，两个独立 venv，不碰系统 Python）
- PyTorch 2.9.1+cu130（RTX 5070 / sm_120；cu128 构建会打印性能警告）
- ComfyUI 0.45.0 + ComfyUI-GGUF

## 启动

1. 界面：`app/venv/Scripts/python.exe app/main.py`，或双击项目根目录的 `GC.lnk`（打包版）
2. 引擎：不用手动开。第一次点「生成预览图」时程序自己拉起 `engine/venv` 里的 ComfyUI
   （监听 127.0.0.1:8188，`--fast-disk` 让权重从 NVMe 流式加载，约 40 秒起好），
   日志写到 `data/engine.log`。想提前预热可以走「文件 → 启动本地引擎」，或运行 `scripts/start-engine.ps1`。

## 界面缩放

程序自己接管缩放，默认 100%（不跟随系统 DPI），所以 2K 屏 + 175% 不会把每个控件再放大一遍。
「视图 → 界面缩放」可改 100 / 125 / 150 / 175% 或跟随系统，写进 `config/ui.json`，重启生效。

## 打包版

`scripts/build-release.ps1` 用 PyInstaller 打成 `dist/GC/GC.exe`（onedir），并生成：

- `GC.lnk`：项目根目录的快捷方式，工作目录指向项目根，所以 `models/`、`workflows/`、`config/` 都按相对路径找到
- `release/GC-<版本>-windows-x64.zip`：不含模型（体积太大），解压到项目根旁边即可复用同一套 `models/`

自检：`dist/GC/GC.exe --selftest` 会在 `data/_selftest.png` 截图并写 `data/_selftest.txt`，
用来确认打包后资源路径没断。

## 从 LrC 启动

LrC 15.1 的「编辑于 → 在外部编辑器中打开」格式下拉只有 TIFF / PSD / JPEG，没有 PNG。
推荐 **TIFF（8 位 / sRGB）**：程序把它转成未压缩 PNG 缓存到 `data/cache/`（同一文件只转一次，
按路径+大小+修改时间取键），之后按 **同名 PNG → 同名 JPEG** 兜底查找。
结果不写回 LrC，成品只走「导出为…」。

## 选区工具

工具栏照着 PS 排：

| 工具 | 键 | 用法 |
| --- | --- | --- |
| 画笔蒙版 | B | 涂抹要重新生成的范围；大小 / 硬度 / 不透明度可用 |
| 橡皮 | E | 擦掉涂过的蒙版 |
| 矩形选框 | M | 拖出矩形直接加入选区 |
| 魔棒 | W | 点一下选中颜色相近的连续区域，容差 1–255 |
| 快速选择 | Q | 按住拖动，只吸附按下时那种颜色 |
| 抓手 | H | 左键拖动画面（空格或中键也行） |
| 缩放 | Z | 点击放大，Alt+点击缩小，滚轮以鼠标为中心 |

抓手和缩放时画笔参数会自动收起，选项栏只剩选区信息和对照按钮。
模式「添加 / 减去」对所有选区工具生效；「羽化选区」对现有蒙版整体软化，Ctrl+Z / Ctrl+Y 撤销重做。
蒙版按 Alpha 存灰度 PNG 送引擎。

## 生成

- 「生成预览图」：草稿档，长边由按钮内齿轮决定（默认原图 10%，限制 256–2048），4 步，约 20 秒
- 「应用预览并生成正式图」：原图 + 草稿 + 素材（≤2048 长边）三参考图重绘，约 90 秒
- 只回贴画笔蒙版形状内的像素，蒙版外逐位不变；羽化环由蒙版外扩+高斯生成，边缘过渡自然

## 对照

预览图不再弹独立窗口，直接贴回画布做原图 / 预览对照（同 LrC 的参考视图）：

- 顶部「原图 / 对比 / 预览」三个按钮，或「视图 → 查看」（Ctrl+Alt+0/1/2/3）
- 对比模式下中间有一条线，拖动它改两侧占比；点 ⇄ / ⇅ 换左右或上下分割（Ctrl+Alt+X）
- 分割线中点有个蓝色圆点，鼠标靠近时指针会变成左右 / 上下箭头

## 模型

右侧列表只显示已安装的本地模型和已配置的 API 方案。
「＋ 添加模型」会读取本机显存与内存，列出这台机器能直接跑的档位并一键下载
（每档 = GGUF 主模型 + text encoder + VAE + Lightning LoRA）。

## API 方案

列表最后一行「＋ API 方案…」打开配置页：名称 / 接口地址 / 模型 / API Key，
「测试连接」用 `GET {base}/models` 探活（鉴权、延迟、可用模型一起验证）。
应用后该方案即成为当前模型，生成改走 `POST {base}/images/edits`（原图 + 蒙版 + 提示词），
返回图缩回 crop 尺寸后走同一套色彩对齐与贴回逻辑。
选中 API 方案时步数 / CFG / 素材图自动禁用——远程接口不接受这些参数。
密钥只存本地 `config/api_models.json`，该文件已加入 `.gitignore`。

## 导出

文件 → 导出为…（`Ctrl+Shift+E`），Adobe 式左侧预览 + 右侧设置：

| 格式 | 质量选项 |
|---|---|
| JPEG | 品质 0–12（8 以上走 4:4:4 采样）、渐进式 |
| PNG | 压缩 无 / 低 / 中 / 高（无损，只影响写入时间与体积） |
| TIFF | 压缩 无 / LZW / ZIP |

只写 8 位：源图本身是 8 位 PNG，ComfyUI 内部也是 8 位，补 16 位只是把字节数翻倍。
对话框里的「预估大小」是真编码一次得到的精确值，不是经验公式。

## 验证脚本

| 脚本 | 作用 |
|---|---|
| `scripts/mock_api.py` | 本地假 OpenAI 接口（/models 与 /images/edits），密钥 `sk-mock` |
| `scripts/test_api.py` | 探活、列表并入、run_api 全链路与蒙版外保真度 |
| `scripts/test_stage.py` | 画笔/羽化/预览比例/模型选择离线自检 |