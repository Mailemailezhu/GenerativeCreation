import sys
import numpy as np
from PIL import Image
a = np.asarray(Image.open("data/test_input.png").convert("RGB")).astype(np.int16)
b = np.asarray(Image.open("data/out_draft.png").convert("RGB")).astype(np.int16)
print("shapes", a.shape, b.shape)
d = np.abs(a - b).max(axis=2)
print("changed px (>2)", int((d > 2).sum()), "max dev", int(d.max()))
ys, xs = np.nonzero(d > 2)
if len(xs):
    print("bbox", xs.min(), ys.min(), xs.max(), ys.max())
m = np.asarray(Image.open("data/test_mask.png").convert("L"))
print("mask bbox", np.nonzero(m)[1].min(), np.nonzero(m)[0].min(), np.nonzero(m)[1].max(), np.nonzero(m)[0].max())
inside = m[np.nonzero(d > 2)]
print("changed px that are inside mask(>8):", int((inside > 8).sum()), "/", len(inside))
