"""局部重绘管线：草稿档 → 定稿档 → 贴回原图。

草稿档（crop 长边 512）只求快，几秒出图，用来看构图、位置、风格对不对；
定稿档（crop 长边 2048）把已认可的草稿当风格参考一起送模型，在原生分辨率上重绘。

两档都只把蒙版内的像素贴回原图，蒙版外保持原像素。
中间产物（裁剪图、蒙版、素材拼图）都在内存里编码成 PNG 上传，不落盘。
"""
import io
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image

from . import apimodels, assets, image_ops as ops, paths
from .comfy_client import ComfyClient, ComfyError, first_image

WORKFLOW = Path(paths.root()) / "workflows" / "qwen_edit_2511_inpaint.json"
FLUX_WORKFLOW = Path(paths.root()) / "workflows" / "flux_fill_inpaint.json"
DRAFT_SIDE = 512
FINAL_SIDE = 2048


def build_workflow(crop_size, prompt, img_name, mask_name, steps=4, cfg=1.0, seed=0,
                   draft_name=None, asset_name=None, unet=None, denoise=1.0,
                   lock_name=None, lock_denoise=0.55):
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
    wf["13"]["inputs"].update({"steps": steps, "cfg": cfg, "seed": seed,
                              "denoise": denoise})
    if unet:
        wf["1"]["inputs"]["unet_name"] = unet

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

    if lock_name:
        # 锁构图：初始 latent 换成"放大后的草稿"而不是原图，模型只细化、不重新构图
        wf["19"] = {"class_type": "LoadImage", "inputs": {"image": lock_name}}
        wf["20"] = {"class_type": "ImageScale",
                    "inputs": {"image": ["19", 0], "upscale_method": "lanczos",
                               "width": w, "height": h, "crop": "disabled"}}
        wf["9"]["inputs"]["pixels"] = ["20", 0]
        wf["13"]["inputs"]["denoise"] = lock_denoise

    return wf


def build_flux_workflow(prompt, img_name, mask_name, steps=20, guidance=30.0, seed=0,
                        unet=None, t5="t5xxl_fp8_e4m3fn.safetensors",
                        clip_l="clip_l.safetensors", vae="ae.safetensors"):
    """FLUX.1 Fill 是专用 inpaint 模型：蒙版和 latent 都由 InpaintModelConditioning 生成，
    提示词只写正向，负向必须留空（guidance 蒸馏模型不认 CFG 文本）。"""
    wf = json.loads(FLUX_WORKFLOW.read_text(encoding="utf-8"))
    wf["4"]["inputs"]["image"] = img_name
    wf["5"]["inputs"]["image"] = mask_name
    wf["7"]["inputs"]["text"] = prompt
    wf["10"]["inputs"]["guidance"] = guidance
    wf["11"]["inputs"].update({"steps": steps, "seed": seed})
    wf["2"]["inputs"].update({"clip_name1": t5, "clip_name2": clip_l})
    wf["3"]["inputs"]["vae_name"] = vae
    if unet:
        wf["1"]["inputs"]["unet_name"] = unet
    return wf


def _as_image(src, mode):
    """PIL 直接用，路径才打开；返回的图像与文件句柄无关。"""
    if isinstance(src, Image.Image):
        return src if src.mode == mode else src.convert(mode)
    with Image.open(src) as im:
        return im.convert(mode)


def prepare(image, mask, stage="draft", pad=180, min_side=512, max_side=None):
    img = _as_image(image, "RGB")
    m = _as_image(mask, "L")
    if m.size != img.size:
        m = m.resize(img.size, Image.LANCZOS)
    bbox = ops.mask_bbox(np.asarray(m))
    if bbox is None:
        raise ValueError("蒙版为空")
    if max_side is None:
        max_side = DRAFT_SIDE if stage == "draft" else FINAL_SIDE
    geo = ops.plan_crop(img.width, img.height, bbox, pad=pad, max_side=max_side,
                        min_side=min_side)
    return img, m, geo


def _png_bytes(pil_img):
    buf = io.BytesIO()
    pil_img.save(buf, "PNG")
    return buf.getvalue()


def run(image, mask, prompt, out_path=None, stage="draft", draft=None,
        asset_paths=(), preview_composite=True, host="127.0.0.1", port=8188,
        steps=4, cfg=1.0, seed=None, feather=None, color_match=True, timeout=900,
        progress=None, draft_side=None, unet=None, denoise=1.0, lock=0.0,
        family="qwen", guidance=30.0, final_side=None):
    """跑一档，结果以 PIL 图放在返回值的 image 里。

    stage="draft" 时可以 preview_composite=False，只拿 crop 小图不贴回。
    stage="final" 必须给 draft —— 没有已认可的草稿就没有定稿的意义。
    out_path 只给命令行脚本留的口子，界面调用不传，结果不落盘。
    """
    if stage not in ("draft", "final"):
        raise ValueError("未知档位: %s" % stage)
    # FLUX Fill 是专用修图模型，不靠草稿传风格，定稿档可以单独跑
    if stage == "final" and draft is None and family == "qwen":
        raise ValueError("定稿档需要草稿图作为风格参考")

    _tick(progress, 2, "准备选区")
    img, m, geo = prepare(image, mask, stage=stage,
                          max_side=draft_side if stage == "draft" else final_side)
    crop, size = geo["crop"], geo["size"]
    crop_img = ops.crop_image(img, crop, size)
    crop_mask = ops.crop_mask(m, crop, size)

    _tick(progress, 6, "连接引擎")
    client = ComfyClient(host=host, port=port)
    if not client.is_up():
        raise ComfyError("引擎未启动: %s:%s" % (host, port))

    _tick(progress, 10, "上传裁剪图")
    img_name = client.upload_image(_png_bytes(crop_img), "gc_crop.png")
    mask_name = client.upload_image(_png_bytes(crop_mask.convert("L")), "gc_mask.png")
    draft_name = None
    if draft is not None:
        draft_name = client.upload_image(_png_bytes(_as_image(draft, "RGB")), "gc_draft.png")
    # 锁构图：草稿是整张画布，按比例裁出同一块再放大到 crop 尺寸，作为初始 latent
    lock_name = None
    if lock > 0 and draft is not None:
        draft_img = _as_image(draft, "RGB")
        kx = draft_img.width / float(img.width)
        ky = draft_img.height / float(img.height)
        box = (int(round(crop[0] * kx)), int(round(crop[1] * ky)),
               int(round(crop[2] * kx)), int(round(crop[3] * ky)))
        seed_crop = draft_img.crop(box)
        if seed_crop.size != size:
            seed_crop = seed_crop.resize(size, Image.LANCZOS)
        lock_name = client.upload_image(_png_bytes(seed_crop), "gc_lock.png")

    asset_name = None
    if len(asset_paths) == 1:
        asset_name = client.upload_image(asset_paths[0])
    elif asset_paths:
        # 模型只有三个参考图槽位，多张素材只能拼成一张再送，顺序写进提示词
        sheet, _cols, _rows = assets.tile(asset_paths)
        asset_name = client.upload_image(_png_bytes(sheet), "gc_assets.png")
        prompt = prompt + assets.describe(asset_paths)

    if seed is None:
        seed = random.randint(0, 2**31 - 1)

    _tick(progress, 16, "组装工作流")
    if family == "flux":
        wf = build_flux_workflow(prompt, img_name, mask_name, steps=steps,
                                 guidance=guidance, seed=seed, unet=unet)
    else:
        # 融合强度只对定稿档有意义：草稿是全重画，再压低 denoise 就看不到新内容
        wf = build_workflow(size, prompt, img_name, mask_name, steps=steps, cfg=cfg,
                            seed=seed, draft_name=draft_name, asset_name=asset_name,
                            unet=unet, denoise=denoise if stage == "final" else 1.0,
                            lock_name=lock_name, lock_denoise=lock)
    _tick(progress, 19, "提交任务")
    pid = client.queue_prompt(wf)
    entry = client.wait_for(pid, timeout=timeout)
    filename, subfolder, ftype = first_image(entry)
    _tick(progress, 88, "读取结果")
    raw = client.fetch_image(filename, subfolder, ftype)
    drop_output(host, filename, subfolder)
    gen = Image.open(io.BytesIO(raw)).convert("RGB")

    info = {"stage": stage, "seed": seed, "crop": crop, "size": size}
    if stage == "draft" and not preview_composite:
        if out_path:
            gen.save(out_path)
        return {**info, "image": gen, "composited": False}

    if feather is None:
        feather = ops.auto_feather(ops.mask_bbox(np.asarray(m)))
    # 色彩对齐必须在 crop 上做：蒙版外统计用的是原图 crop，贴回后蒙版外是逐位原像素
    if color_match:
        gen = ops.match_color(gen, crop_img, crop_mask)
    _tick(progress, 92, "贴回原图")
    result = ops.composite_back(img, gen, crop_mask, crop, feather=feather)
    _tick(progress, 97, "完成")
    if out_path:
        result.save(out_path)
    return {**info, "image": result, "composited": True, "feather": feather}


def _tick(progress, pct, msg):
    if progress:
        progress(pct, msg)


def _output_dir():
    return Path(paths.root()) / "engine" / "ComfyUI" / "output"


def drop_output(host, filename, subfolder=None):
    """本地引擎的 output 只当传输通道用：取完字节就把那张图删掉。

    远程引擎删不到，也不能假设布局，直接跳过。
    """
    if host not in ("127.0.0.1", "localhost"):
        return
    p = _output_dir() / (subfolder or "") / filename
    try:
        p.unlink()
    except OSError:
        pass


def purge_output():
    """清掉以前版本留在引擎 output 里的生成图。"""
    try:
        for p in _output_dir().glob("gc_*.png"):
            try:
                p.unlink()
            except OSError:
                pass
    except OSError:
        pass


def run_api(image, mask, prompt, api, out_path=None, stage="draft", draft_side=None,
            feather=None, preview_composite=True, progress=None, timeout=600):
    """走远程 /images/edits：贴回逻辑和本地档完全一样，只是采样在别人机器上跑。"""
    _tick(progress, 2, "准备选区")
    img, m, geo = prepare(image, mask, stage=stage,
                          max_side=draft_side if stage == "draft" else None)
    crop, size = geo["crop"], geo["size"]
    crop_img = ops.crop_image(img, crop, size)
    crop_mask = ops.crop_mask(m, crop, size)

    _tick(progress, 10, "对齐接口尺寸")
    api_size = apimodels.pick_size(size[0], size[1])
    payload = crop_img.resize(api_size, Image.LANCZOS)
    scaled_mask = crop_mask.resize(api_size, Image.LANCZOS)
    # OpenAI 约定：蒙版里透明的地方才会被重画
    alpha = scaled_mask.point(lambda v: 0 if v > 96 else 255)
    mask_img = Image.new("RGBA", api_size, (255, 255, 255, 255))
    mask_img.putalpha(alpha)
    bi, bm = io.BytesIO(), io.BytesIO()
    payload.save(bi, "PNG")
    mask_img.save(bm, "PNG")

    _tick(progress, 20, "上传并等待远程生成")
    raw, used = apimodels.edit(api["base"], api["key"], api["model"], bi.getvalue(),
                               bm.getvalue(), prompt, api_size, timeout=timeout)
    _tick(progress, 88, "读取结果")
    gen = Image.open(io.BytesIO(raw)).convert("RGB")
    if gen.size != api_size:
        gen = gen.resize(api_size, Image.LANCZOS)
    gen = gen.resize(size, Image.LANCZOS)

    info = {"stage": stage, "api": api.get("name"), "size": used, "crop": crop}
    if stage == "draft" and not preview_composite:
        if out_path:
            gen.save(out_path)
        return {**info, "image": gen, "composited": False}

    if feather is None:
        feather = ops.auto_feather(ops.mask_bbox(np.asarray(m)))
    gen = ops.match_color(gen, crop_img, crop_mask)
    _tick(progress, 92, "贴回原图")
    result = ops.composite_back(img, gen, crop_mask, crop, feather=feather)
    _tick(progress, 97, "完成")
    if out_path:
        result.save(out_path)
    return {**info, "image": result, "composited": True, "feather": feather}