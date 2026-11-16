# GC — GenerativeCreation

本地 AI 图像创作工作台：ComfyUI 引擎 + PyQt5 画布，面向 Lightroom Classic 修图后的局部生成式创作。

## 目录

| 路径 | 说明 |
|---|---|
| `app/` | PyQt5 界面，独立虚拟环境 `app/venv` |
| `app/core/` | ComfyUI HTTP 客户端 |
| `engine/` | ComfyUI 引擎（submodule），独立虚拟环境 `engine/venv` |
| `models/` | 模型文件，不入库，由 `config/extra_model_paths.yaml` 挂载 |
| `config/` | 引擎与软件配置 |
| `scripts/` | 启动脚本 |
| `data/` | 运行数据，不入库 |

## 环境

- Python 3.12（uv 管理，两个独立 venv，不碰系统 Python）
- PyTorch 2.9.1+cu128（RTX 5070 / sm_120）
- ComfyUI 0.45.0

## 启动

1. 引擎：`scripts/start-engine.ps1`（监听 127.0.0.1:8188）
2. 界面：`app/venv/Scripts/python.exe app/main.py`

## 从 LrC 启动

`app/main.py <路径>`：程序按 **同名 PNG → 同名 JPEG** 的顺序在传入文件所在目录及导出目录里找，
找到就载入；都没有就提示先在 LrC 导出（PNG / sRGB / 8-bit / 原尺寸）。

## 生成

- 「生成预览图」：512 长边草稿档，4 步，约 20 秒
- 「应用预览并生成正式图」：原图 + 草稿 + 素材（≤2048 长边）三参考图重绘，约 90 秒
- 只回贴画笔蒙版形状内的像素，蒙版外逐位不变；结果回填画布并可继续迭代

## 导出

文件 → 导出为…（`Ctrl+Shift+E`），Adobe 式左侧预览 + 右侧设置：

| 格式 | 质量选项 |
|---|---|
| JPEG | 品质 0–12（8 以上走 4:4:4 采样）、渐进式 |
| PNG | 压缩 无 / 低 / 中 / 高（无损，只影响写入时间与体积） |
| TIFF | 压缩 无 / LZW / ZIP |

只写 8 位：源图本身是 8 位 PNG，ComfyUI 内部也是 8 位，补 16 位只是把字节数翻倍。
对话框里的「预估大小」是真编码一次得到的精确值，不是经验公式。
