import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app"))
from PIL import Image
from core import exporter, lrc
img = Image.open("data/test_input.png").convert("RGB")
for fmt, opts in (("JPEG", {"quality": 12, "progressive": False}),
                  ("JPEG", {"quality": 5}),
                  ("PNG", {"compress_level": 9}),
                  ("PNG", {"compress_level": 0}),
                  ("TIFF", {"compression": "LZW"}),
                  ("TIFF", {"compression": "ZIP"})):
    p = "data/_t" + exporter.EXT[fmt]
    n = exporter.save(img, p, fmt, opts)
    back = Image.open(p)
    print("SAVE", fmt, opts, exporter.human(n), back.size, back.mode)
d = tempfile.mkdtemp()
open(os.path.join(d, "a.jpg"), "wb").write(b"x")
print("JPG_ONLY", lrc.resolve(os.path.join(d, "a.NEF")))
open(os.path.join(d, "a.png"), "wb").write(b"x")
print("BOTH", lrc.resolve(os.path.join(d, "a.NEF")))
print("DIRECT", lrc.resolve(os.path.join(d, "a.png")))
print("MISS", lrc.resolve(os.path.join(d, "b.NEF"))[0])
