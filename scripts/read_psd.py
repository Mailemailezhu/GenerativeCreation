"""用 psd-tools 读回手写 PSD，核对图层名/尺寸/合成图是否一致。"""
import sys

from psd_tools import PSDImage

p = sys.argv[1]
psd = PSDImage.open(p)
print("SIZE", psd.width, psd.height, "CHANNELS", psd.channels, "DEPTH", psd.depth)
for i, layer in enumerate(psd):
    print("LAYER", i, repr(layer.name), layer.size, layer.bbox, "visible", layer.visible)
comp = psd.composite()
print("COMPOSITE", comp.size, comp.mode)
print("PIX_HASH", tuple(comp.convert("RGB").resize((8, 8)).getdata())[:4])
