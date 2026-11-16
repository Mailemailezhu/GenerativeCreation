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

## 画笔

大小、硬度、不透明度、羽化（自动或手动像素值）都在顶部选项栏；模式可切 add / subtract，
「羽化选区」对现有蒙版整体软化，Ctrl+Z / Ctrl+Y 撤销重做。蒙版按 Alpha 存灰度 PNG 送引擎。

## 生成

- 「生成预览图」：草稿档，长边由按钮内齿轮决定（默认原图 10%，限制 256–2048），4 步，约 20 秒
- 「应用预览并生成正式图」：原图 + 草稿 + 素材（≤2048 长边）三参考图重绘，约 90 秒
- 只回贴画笔蒙版形状内的像素，蒙版外逐位不变；羽化环由蒙版外扩+高斯生成，边缘过渡自然

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