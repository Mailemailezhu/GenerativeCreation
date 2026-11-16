"""局部重绘管线：草稿档 → 定稿档 → 贴回原图。

草稿档（crop 长边 512）只求快，几秒出图，用来看构图、位置、风格对不对；
定稿档（crop 长边 2048）把已认可的草稿当风格参考一起送模型，在原生分辨率上重绘。

两档都只把蒙版内的像素贴回原图，蒙版外保持原像素。
"""
import io
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image

from . import assets, image_ops as ops
from .comfy_client import ComfyClient, ComfyError, first_image

WORKFLOW = Path(__file__).resolve().parents[2] / "workflows" / "qwen_edit_2511_inpaint.json"
DRAFT_SIDE = 512
FINAL_SIDE = 2048


def build_workflow(crop_size, prompt, img_name, mask_name, steps=4, cfg=1.0, seed=0,
                   draft_name=None, asset_name=None):
    """按档位裁掉不用的参考图节点。

    没接上的 LoadImage 会让整个 prompt 校验失败，所以未使用的节点要真的删掉，
    而不是留一张空图。
    """
    wf = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    w, h = crop_size
    wf["6"]["inputs"].update({"width": w, "height": h})
    wf["5"]["inputs"]["image"] = img_name
    wf["7"]["inputs"]["image"] = mask_name
    wf["11"]["inputs"]["prompt"] = prompt
    wf["13"]["inputs"].update({"steps": steps, "cfg": cfg, "seed": seed})

    if draft_name:
        wf["16"]["inputs"]["image"] = draft_name
        wf["17"]["inputs"].update({"width": w, "height": h})
    else:
        wf.pop("16", None)
        wf.pop("17", None)
        for n in ("11", "12"):
            wf[n]["inputs"].pop("image2", None)

    if asset_name:
        wf["18"]["inputs"]["image"] = asset_name
    else:
        wf.pop("18", None)
        for n in ("11", "12"):
            wf[n]["inputs"].pop("image3", None)

    return wf


def prepare(image_path, mask_path, stage="draft", pad=180, min_side=512):
    img = Image.open(image_path).convert("RGB")
    mask = Image.open(mask_path).convert("L")
    if mask.size != img.size:
        mask = mask.resize(img.size, Image.LANCZOS)
    bbox = ops.mask_bbox(np.asarray(mask))
    if bbox is None:
        raise ValueError("蒙版为空")
    max_side = DRAFT_SIDE if stage == "draft" else FINAL_SIDE
    geo = ops.plan_crop(img.width, img.height, bbox, pad=pad, max_side=max_side,
                        min_side=min_side)
    return img, mask, geo


def run(image_path, mask_path, prompt, out_path, stage="draft", draft_path=None,
        asset_paths=(), preview_composite=True, host="127.0.0.1", port=8188,
        steps=4, cfg=1.0, seed=None, feather=None, color_match=True, timeout=900,
        progress=None):
    """跑一档，把结果写到 out_path。

    stage="draft" 时可以 preview_composite=False，只拿 crop 小图不贴回。
    stage="final" 必须给 draft_path —— 没有已认可的草稿就没有定稿的意义。
    """
    if stage not in ("draft", "final"):
        raise ValueError(f"未知档位: {stage}")
    if stage == "final" and not draft_path:
        raise ValueError("定稿档需要草稿图作为风格参考")

    _tick(progress, 2, "准备选区")
    img, mask, geo = prepare(image_path, mask_path, stage=stage)
    crop, size = geo["crop"], geo["size"]
    crop_img = ops.crop_image(img, crop, size)
    crop_mask = ops.crop_mask(mask, crop, size)

    _tick(progress, 6, "连接引擎")
    client = ComfyClient(host=host, port=port)
    if not client.is_up():
        raise ComfyError(f"引擎未启动: {host}:{port}")

    tmp = Path(out_path).parent / "_gc_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    _tick(progress, 10, "上传裁剪图")
    img_name = client.upload_image(_save(crop_img, tmp / "crop.png"))
    mask_name = client.upload_image(_save(crop_mask, tmp / "mask.png"))
    draft_name = client.upload_image(draft_path) if draft_path else None
    asset_name = None
    if len(asset_paths) == 1:
        asset_name = client.upload_image(asset_paths[0])
    elif asset_paths:
        # 模型只有三个参考图槽位，多张素材只能拼成一张再送，顺序写进提示词
        sheet, _cols, _rows = assets.tile(asset_paths)
        asset_name = client.upload_image(_save(sheet, tmp / "assets.png"))
        prompt = prompt + assets.describe(asset_paths)

    if seed is None:
        seed = random.randint(0, 2**31 - 1)

    _tick(progress, 16, "组装工作流")
    wf = build_workflow(size, prompt, img_name, mask_name, steps=steps, cfg=cfg,
                        seed=seed, draft_name=draft_name, asset_name=asset_name)
    _tick(progress, 19, "提交任务")
    pid = client.queue_prompt(wf)
    entry = client.wait_for(pid, timeout=timeout)
    filename, subfolder, ftype = first_image(entry)
    _tick(progress, 88, "读取结果")
    gen = Image.open(io.BytesIO(client.fetch_image(filename, subfolder, ftype))).convert("RGB")

    info = {"stage": stage, "seed": seed, "crop": crop, "size": size}
    if stage == "draft" and not preview_composite:
        _save(gen, out_path)
        return {**info, "composited": False, "out": str(out_path)}

    if feather is None:
        feather = ops.auto_feather(ops.mask_bbox(np.asarray(mask)))
    # 色彩对齐必须在 crop 上做：蒙版外统计用的是原图 crop，贴回后蒙版外是逐位原像素
    if color_match:
        gen = ops.match_color(gen, crop_img, crop_mask)
    _tick(progress, 92, "贴回原图")
    result = ops.composite_back(img, gen, crop_mask, crop, feather=feather)
    _tick(progress, 97, "保存")
    _save(result, out_path)
    return {**info, "composited": True, "feather": feather, "out": str(out_path)}


def _tick(progress, pct, msg):
    if progress:
        progress(pct, msg)


def _save(pil_img, path):
    pil_img.save(path)
    return str(path)
