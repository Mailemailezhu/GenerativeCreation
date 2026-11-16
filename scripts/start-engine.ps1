# 启动 ComfyUI 引擎，监听本机 8188（仅本机可访问）
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py   = Join-Path $root "engine\venv\Scripts\python.exe"
$main = Join-Path $root "engine\ComfyUI\main.py"
$fmt  = Join-Path $root "config\extra_model_paths.yaml"
if (-not (Test-Path $py))   { throw "找不到引擎虚拟环境: $py" }
if (-not (Test-Path $main)) { throw "找不到 ComfyUI: $main" }
# extra_model_paths.yaml 里的相对路径按进程 cwd 解析，所以先切到项目根
Set-Location $root
# --fast-disk: 三块盘都是 NVMe，权重直接从磁盘流式加载，比压进内存再搬运更快
& $py $main --listen 127.0.0.1 --port 8188 --extra-model-paths-config $fmt --fast-disk
