"""带进度回调和断点续传的下载器。"""
import os
import time
import urllib.error
import urllib.request

CHUNK = 1024 * 1024


def _total(url, headers):
    try:
        req = urllib.request.Request(url, headers=dict(headers, Range="bytes=0-0"))
        with urllib.request.urlopen(req, timeout=30) as r:
            cr = r.headers.get("Content-Range")
            if cr and "/" in cr:
                return int(cr.split("/")[-1])
    except Exception:
        pass
    return 0


def download(url, dest, on_progress=None, cancel=None):
    """下载到 dest。on_progress(已下载字节, 总字节, 速度MB/s)，cancel() 返回 True 就中断。"""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    part = dest + ".part"
    have = os.path.getsize(part) if os.path.isfile(part) else 0
    headers = {"User-Agent": "GC/1.0"}
    total = _total(url, headers)
    if total and have >= total:
        os.replace(part, dest)
        return dest
    if have:
        headers["Range"] = "bytes=%d-" % have
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=60)
    except urllib.error.HTTPError as e:
        if e.code in (416, 501):
            # 服务器不认续传：丢掉残片从头来
            if os.path.isfile(part):
                os.remove(part)
            have = 0
            req = urllib.request.Request(url, headers={"User-Agent": "GC/1.0"})
            resp = urllib.request.urlopen(req, timeout=60)
        else:
            raise
    if total <= 0:
        cl = resp.headers.get("Content-Length")
        total = (int(cl) + have) if cl else 0
    t0 = time.time()
    done = have
    with open(part, "ab" if have else "wb") as fh:
        while True:
            if cancel and cancel():
                raise RuntimeError("已取消")
            buf = resp.read(CHUNK)
            if not buf:
                break
            fh.write(buf)
            done += len(buf)
            if on_progress:
                speed = done / max(1e-6, time.time() - t0) / 1024 / 1024
                on_progress(done, total, speed)
    resp.close()
    if total and done < total:
        raise RuntimeError("下载不完整：%d/%d 字节，重试会接着下" % (done, total))
    os.replace(part, dest)
    return dest
