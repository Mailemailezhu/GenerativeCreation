"""自己画一个图标：深色底 + 蓝色笔刷弧 + 高光点，输出多尺寸 ico。"""
import math
import os
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 1024
SS = 2048  # 先放大画再缩小，边缘才不毛


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def quad(p0, p1, p2, t):
    u = 1 - t
    return (u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
            u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1])


def bg():
    im = Image.new("RGB", (S, S), (0, 0, 0))
    d = ImageDraw.Draw(im)
    top, bot = (38, 50, 68), (13, 16, 23)
    for y in range(S):
        d.line([(0, y), (S, y)], fill=lerp(top, bot, y / float(S)))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=255)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    return out


def swipe():
    """二次贝塞尔 + 逐点变半径，密采样 200 步，笔触才有起笔收笔的粗细变化。"""
    layer = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    p0 = (0.16 * SS, 0.76 * SS)
    p1 = (0.44 * SS, 0.74 * SS)
    p2 = (0.79 * SS, 0.30 * SS)
    steps = 200
    for i in range(steps + 1):
        t = i / float(steps)
        x, y = quad(p0, p1, p2, t)
        r = (0.028 + 0.062 * math.sin(math.pi * min(1.0, t * 1.06)) ** 0.7) * SS
        col = lerp((42, 132, 232), (118, 232, 255), t)
        d.ellipse([x - r, y - r, x + r, y + r], fill=col + (255,))
    layer = layer.resize((S, S), Image.LANCZOS)
    glow = layer.filter(ImageFilter.GaussianBlur(S * 0.035))
    big = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    big.alpha_composite(glow)
    big.alpha_composite(layer)
    return big


def spark():
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = int(S * 0.79), int(S * 0.30)
    for dx, dy, ln in ((1, 0, 0.13), (-1, 0, 0.10), (0, 1, 0.10), (0, -1, 0.13)):
        ex, ey = cx + dx * S * ln, cy + dy * S * ln
        d.line([(cx, cy), (ex, ey)], fill=(200, 246, 255, 200), width=int(S * 0.010))
    d.ellipse([cx - S * 0.042, cy - S * 0.042, cx + S * 0.042, cy + S * 0.042], fill=(240, 253, 255, 255))
    return layer.filter(ImageFilter.GaussianBlur(S * 0.005))


def compose():
    im = bg()
    im.alpha_composite(swipe())
    im.alpha_composite(spark())
    edge = Image.new("L", (S, S), 0)
    ImageDraw.Draw(edge).rounded_rectangle([1, 1, S - 2, S - 2], radius=int(S * 0.22),
                                           outline=110, width=int(S * 0.006))
    im.paste(Image.new("RGBA", (S, S), (96, 156, 224, 255)), (0, 0), edge)
    return im


def main():
    out_dir = os.path.join(ROOT, "app", "assets")
    os.makedirs(out_dir, exist_ok=True)
    big = compose()
    sizes = [256, 128, 64, 48, 32, 24, 16]
    ico = os.path.join(out_dir, "gc.ico")
    big.resize((256, 256), Image.LANCZOS).save(ico, sizes=[(s, s) for s in sizes])
    png = os.path.join(out_dir, "gc.png")
    big.resize((512, 512), Image.LANCZOS).save(png)
    print("ICON_OK", os.path.getsize(ico), "bytes")


if __name__ == "__main__":
    main()
