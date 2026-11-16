"""核对图层名（unicode_escape，避免控制台编码干扰）与生成层的透明度。"""
import sys

import numpy as np
from psd_tools import PSDImage

psd = PSDImage.open(sys.argv[1])
for i, layer in enumerate(psd):
    a = np.array(layer.topil().convert("RGBA"))[:, :, 3]
    print("LAYER", i, layer.name.encode("unicode_escape").decode(),
          "alpha_min", int(a.min()), "alpha_max", int(a.max()),
          "opaque_ratio", round(float((a > 128).mean()), 3))
