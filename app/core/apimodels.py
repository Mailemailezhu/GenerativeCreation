"""远程 API 方案：存连接信息、探活、走 OpenAI 兼容的图像编辑接口。"""
import base64
import io
import json
import os
import time
import urllib.error
import urllib.request

from PIL import Image

# gpt-image-1 一类接口只认这三档尺寸，送图前要先贴到其中一档
SIZES = ((1024, 1024), (1536, 1024), (1024, 1536))


def load(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)
        return items if isinstance(items, list) else []
    except (OSError, ValueError):
        return []


def save(path, items):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def mask_key(item):
    return "%s|%s" % (item.get("base", "").rstrip("/"), item.get("model", ""))


def norm_base(text):
    b = (text or "").strip().rstrip("/")
    if b and not b.endswith("/v1") and "/v1" not in b:
        b += "/v1"
    return b


def probe(base, key, timeout=15):
    """GET {base}/models：OpenAI 兼容服务的标准探活，通了说明地址和密钥都对。"""
    url = (base or "").rstrip("/") + "/models"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + (key or "")})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(8192)
        ms = (time.time() - t0) * 1000
        try:
            data = json.loads(body.decode("utf-8", "replace"))
            names = [m.get("id") for m in (data.get("data") or []) if isinstance(m, dict)]
        except ValueError:
            names = []
        if names:
            return True, "连接正常（%.0f ms），可用模型 %d 个，例如 %s" % (ms, len(names), names[0])
        return True, "连接正常（%.0f ms）" % ms
    except urllib.error.HTTPError as e:
        try:
            detail = e.read()[:200].decode("utf-8", "replace")
        except Exception:
            detail = ""
        return False, ("服务返回 %d %s %s" % (e.code, e.reason, detail)).strip()
    except Exception as e:
        return False, "连不上：%s" % e


def pick_size(w, h):
    ratio = w / float(h or 1)
    return min(SIZES, key=lambda s: abs(s[0] / float(s[1]) - ratio))


def _multipart(fields, files):
    boundary = "----gc" + base64.b16encode(os.urandom(8)).decode()
    out = io.BytesIO()
    for k, v in fields.items():
        out.write(("--%s\r\n" % boundary).encode())
        out.write(('Content-Disposition: form-data; name="%s"\r\n\r\n' % k).encode())
        out.write(str(v).encode("utf-8"))
        out.write(b"\r\n")
    for k, (fname, data) in files.items():
        out.write(("--%s\r\n" % boundary).encode())
        out.write(('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (k, fname)).encode())
        out.write(b"Content-Type: image/png\r\n\r\n")
        out.write(data)
        out.write(b"\r\n")
    out.write(("--%s--\r\n" % boundary).encode())
    return out.getvalue(), "multipart/form-data; boundary=" + boundary


def edit(base, key, model, image_png, mask_png, prompt, size, timeout=600):
    """POST {base}/images/edits，返回 (PNG 字节, 用掉的尺寸字符串)。"""
    fields = {"model": model, "prompt": prompt, "n": "1", "size": "%dx%d" % size}
    body, ctype = _multipart(fields, {"image": ("image.png", image_png),
                                      "mask": ("mask.png", mask_png)})
    req = urllib.request.Request((base or "").rstrip("/") + "/images/edits", data=body,
                                 headers={"Authorization": "Bearer " + (key or ""),
                                          "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        try:
            detail = e.read()[:400].decode("utf-8", "replace")
        except Exception:
            detail = ""
        raise RuntimeError("接口返回 %d %s %s" % (e.code, e.reason, detail).strip())
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
        item = (data.get("data") or [{}])[0]
    except (ValueError, IndexError):
        raise RuntimeError("接口返回的不是 JSON：%r" % raw[:200])
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"]), "%dx%d" % size
    if item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=timeout) as r:
            return r.read(), "%dx%d" % size
    raise RuntimeError("接口没有返回图像：%s" % str(data)[:300])
