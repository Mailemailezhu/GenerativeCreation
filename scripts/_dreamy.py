"""梦幻后处理：光绕（light wrap）把生成物体的边缘融进背景光，再加亮部辉光与蒙版内柔焦。"""
import os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
import numpy as np
from PIL import Image, ImageFilter

def _f(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))

def light_wrap(gen, orig, mask, radius=None, strength=0.45):
    a = np.asarray(gen.convert("RGB"), np.float32) / 255.0
    o = np.asarray(orig.convert("RGB"), np.float32) / 255.0
    h, w = a.shape[:2]
    r = radius or max(6, int(w * 0.004))
    d = np.abs(a - o).max(axis=2)
    alpha = np.clip((d - 0.012) / 0.06, 0, 1)
    if mask is not None:
        m = np.asarray(mask.convert("L").resize((w, h)), np.float32) / 255.0
        alpha = alpha * m
    base = np.asarray(_f(alpha).filter(ImageFilter.GaussianBlur(r * 3)), np.float32)
    edge = np.clip(np.abs(alpha - base) * 3.0, 0, 1)
    band = edge
    ww = np.clip(band * strength, 0, 0.55)
    bg = np.asarray(_f(o).filter(ImageFilter.GaussianBlur(r * 2.5)), np.float32) / 255.0
    out = a * (1 - ww[..., None]) + bg * ww[..., None]
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))

def bloom(im, mask=None, amount=0.55, radius=None):
    a = np.asarray(im.convert("RGB"), np.float32) / 255.0
    h, w = a.shape[:2]
    r = radius or max(6, int(w * 0.008))
    lum = a.max(axis=2)
    wgt = np.clip((lum - 0.80) / 0.20, 0, 1) ** 1.6
    if mask is not None:
        m = np.asarray(mask.convert("L").resize((w, h)), np.float32) / 255.0
        m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(int(r * 0.8))), np.float32) / 255.0
        wgt = wgt * m
    glow = np.asarray(_f(a * wgt[..., None]).filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0
    glow[..., 0] *= 0.78
    glow[..., 1] *= 1.04
    glow[..., 2] *= 1.12
    out = 1.0 - (1.0 - a) * (1.0 - np.clip(glow * amount, 0, 1))
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))

def orton(im, mask, amount=0.10, radius=None):
    a = np.asarray(im.convert("RGB"), np.float32) / 255.0
    h, w = a.shape[:2]
    r = radius or max(6, int(w * 0.01))
    m = np.asarray(mask.convert("L").resize((w, h)), np.float32) / 255.0
    soft = np.asarray(_f(a).filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0
    blend = (a * 0.6 + soft * 0.4) * amount
    out = a * (1 - amount * m[..., None]) + blend * m[..., None]
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))

def full(gen_path, orig_path, mask_path, dst, wrap=0.45, glow=0.55, soft=0.10):
    gen = Image.open(gen_path)
    orig = Image.open(orig_path)
    mask = Image.open(mask_path)
    out = light_wrap(gen, orig, mask, strength=wrap)
    out = bloom(out, mask, amount=glow)
    out = orton(out, mask, amount=soft)
    out.save(dst)
    return out

if __name__ == "__main__":
    a = sys.argv
    out = full(a[1], a[2], a[3], a[4],
               wrap=float(a[5]) if len(a) > 5 else 0.45,
               glow=float(a[6]) if len(a) > 6 else 0.55,
               soft=float(a[7]) if len(a) > 7 else 0.10)
    print("POST_OK", a[4], out.size)