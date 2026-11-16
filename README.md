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
