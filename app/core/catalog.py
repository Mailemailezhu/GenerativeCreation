"""模型目录：只放能直接喂给本软件工作流的模型，以及它们要多少显存/内存。"""
import os

SITE = "https://modelscope.cn/models/{repo}/resolve/master/{file}"


def _f(repo, file, dest, note=""):
    return {"url": SITE.format(repo=repo, file=file), "dest": dest, "note": note}


ENC_REPO = "Comfy-Org/Qwen-Image-Edit_ComfyUI"
LORA_REPO = "lightx2v/Qwen-Image-Edit-2511-Lightning"

DEPS = [
    _f(ENC_REPO, "split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors",
       "text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors", "文本编码器 · 必装"),
    _f(ENC_REPO, "split_files/vae/qwen_image_vae.safetensors",
       "vae/qwen_image_vae.safetensors", "VAE · 必装"),
    _f(LORA_REPO, "Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors",
       "loras/Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors", "4 步加速 LoRA · 必装"),
]

GGUF = [
    {"id": "qwen2511-q5", "name": "Qwen-Image-Edit-2511 · Q5_K_M", "tag": "推荐",
     "desc": "20B 主力模型，15.4GB。实测 4 步出 512 预览约 20 秒采样，画质与体积的平衡点。",
     "vram": 11, "ram": 26, "file": "qwen-image-edit-2511-Q5_K_M.gguf"},
    {"id": "qwen2511-q4", "name": "Qwen-Image-Edit-2511 · Q4_K_M", "tag": "省显存",
     "desc": "12.9GB。显存或内存吃紧时的备选，细节略软，速度反而比 Q5 快。",
     "vram": 10, "ram": 22, "file": "qwen-image-edit-2511-Q4_K_M.gguf"},
    {"id": "qwen2511-q8", "name": "Qwen-Image-Edit-2511 · Q8_0", "tag": "最高画质",
     "desc": "22.4GB。几乎无量化损失，但 32GB 内存下开 LrC 会频繁换页，出图慢一倍以上。",
     "vram": 12, "ram": 30, "file": "qwen-image-edit-2511-Q8_0.gguf"},
]

for _e in GGUF:
    _e["files"] = DEPS + [_f("unsloth/Qwen-Image-Edit-2511-GGUF", _e["file"],
                             "diffusion_models/" + _e["file"], "主模型")]


def by_id(mid):
    """按 id 取档位；判断主模型用哪份权重文件靠它。"""
    for e in GGUF:
        if e["id"] == mid:
            return e
    return None


def installed(models_root, entry):
    for f in entry["files"]:
        p = os.path.join(models_root, f["dest"])
        if not os.path.isfile(p) or os.path.getsize(p) < 1024 * 1024:
            return False
    return True


def missing(models_root, entry):
    return [f for f in entry["files"] if not os.path.isfile(os.path.join(models_root, f["dest"]))
            or os.path.getsize(os.path.join(models_root, f["dest"])) < 1024 * 1024]


def evaluate(models_root, hw):
    """给每个档位打上 已安装 / 可安装 / 装不下 三种状态。"""
    out = []
    for e in GGUF:
        e = dict(e)
        if installed(models_root, e):
            e["state"] = "installed"
            e["reason"] = "已安装"
        elif hw["vram_gb"] < e["vram"] or hw["ram_gb"] < e["ram"]:
            e["state"] = "blocked"
            e["reason"] = "显存需 %.0f GB / 内存需 %.0f GB" % (e["vram"], e["ram"])
        else:
            e["state"] = "ready"
            e["reason"] = "可直接安装"
        out.append(e)
    return out
