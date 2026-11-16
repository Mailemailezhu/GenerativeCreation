"""最小 PSD 写入器：8 位 RGB + 逐通道 RLE，支持带透明度的多图层，不依赖第三方库。

Pillow 只能写平铺的 PSD（而且还要额外插件）、psd-tools 只读、pytoshop 没有 Python 3.12
的轮子，所以这里按 Adobe 文件格式规范自己拼：头部 → 颜色模式 → 图像资源 → 图层信息 →
合成图。Photoshop 和 Affinity 都按这条路径读，图层名优先读 luni（Unicode）块。
"""
import struct


def _packbits(row):
    """PackBits（TIFF 老式 RLE）：控制字节 n>=0 表示后面 n+1 个字面字节，
    257-(n) 表示把下一个字节重复 257-n 次（即 -n，n 在 1..128）。"""
    out = bytearray()
    i, n = 0, len(row)
    while i < n:
        run = 1
        while i + run < n and row[i + run] == row[i] and run < 128:
            run += 1
        if run >= 3:
            out.append(257 - run)
            out.append(row[i])
            i += run
            continue
        start = i
        i += run
        while i < n and i - start < 128:
            run = 1
            while i + run < n and row[i + run] == row[i] and run < 128:
                run += 1
            if run >= 3:
                break
            i += run
        out.append(i - start - 1)
        out.extend(row[start:i])
    return bytes(out)


def _channel_rle(plane):
    """plane 是单通道的 bytes（w*h）；返回 (每行字节数表, 打包数据)。"""
    w, h = plane.size
    raw = plane.tobytes()
    counts, chunks = [], []
    for y in range(h):
        row = _packbits(raw[y * w:(y + 1) * w])
        counts.append(len(row))
        chunks.append(row)
    return counts, b"".join(chunks)


def _channel_block(plane):
    counts, data = _channel_rle(plane)
    head = struct.pack(">H", 1) + struct.pack(">%dh" % len(counts), *counts)
    return head + data


def _pascal(name):
    raw = name.encode("latin-1", "replace")[:255]
    out = bytes([len(raw)]) + raw
    pad = (-len(out)) % 4
    return out + b"\x00" * pad


def _luni(name):
    """Photoshop 的图层名以这个 Unicode 块为准，否则中文会变成乱码。"""
    raw = name.encode("utf-16-be")
    body = struct.pack(">I", len(name)) + raw
    return b"8BIM" + b"luni" + struct.pack(">I", len(body)) + body


def _layer_record(name, width, height, lengths):
    rect = struct.pack(">4i", 0, 0, height, width)
    chans = struct.pack(">h", len(lengths))
    for cid, ln in lengths:
        chans += struct.pack(">hI", cid, ln)
    blend = b"8BIM" + b"norm" + bytes([255, 0, 0, 0])
    extra = struct.pack(">I", 0) + struct.pack(">I", 0)
    extra += _pascal(name) + _luni(name)
    return rect + chans + blend + struct.pack(">I", len(extra)) + extra


def write(path, layers, composite, flat_name="合成"):
    """layers 自下而上，每项 (名称, RGBA 图)；composite 是不看图层也能正确显示的 RGB 图。"""
    if not layers:
        raise ValueError("PSD 至少需要一个图层")
    width, height = composite.size
    records, channel_data = b"", b""
    for name, img in layers:
        rgba = img.convert("RGBA")
        if rgba.size != (width, height):
            rgba = rgba.resize((width, height))
        planes = [rgba.getchannel(c) for c in ("R", "G", "B", "A")]
        ids = (0, 1, 2, -1)
        blocks = [_channel_block(p) for p in planes]
        lengths = [(ids[i], len(blocks[i])) for i in range(4)]
        records += _layer_record(name, width, height, lengths)
        channel_data += b"".join(blocks)

    info = struct.pack(">h", len(layers)) + records + channel_data
    if len(info) % 2:
        info += b"\x00"
    layer_mask = struct.pack(">I", len(info)) + info + struct.pack(">I", 0)

    rgb = composite.convert("RGB")
    planes = [rgb.getchannel(c) for c in ("R", "G", "B")]
    blocks = [_channel_rle(p) for p in planes]
    head = struct.pack(">H", 1)
    for counts, _data in blocks:
        head += struct.pack(">%dh" % len(counts), *counts)
    image_data = head + b"".join(d for _c, d in blocks)

    out = bytearray()
    out += b"8BPS" + struct.pack(">H", 1) + b"\x00" * 6
    out += struct.pack(">HIIHH", 3, height, width, 8, 3)
    out += struct.pack(">I", 0)
    out += struct.pack(">I", 0)
    out += struct.pack(">I", len(layer_mask)) + layer_mask
    out += image_data
    with open(path, "wb") as f:
        f.write(out)
    return len(out)
