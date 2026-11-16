import sys, time, numpy as np
sys.path.insert(0, 'app')
from PIL import Image, ImageFilter
from core import pipeline, image_ops as ops
P = '十架发光的纸飞机呈对角线编队飞行，拖曳青蓝色粒子尾迹'
t0 = time.time()
info = pipeline.run('data/_gc_preview.png', 'data/_gc_mask.png', P, 'data/_count/F_final.png',
                    stage='final', draft_path='data/_gc_preview.png', steps=4, cfg=1.0, seed=777)
print('FINAL', round(time.time()-t0,1), 's', info['crop'], info['size'])
im = Image.open('data/_count/F_final.png').convert('RGB')
mk = Image.open('data/_gc_mask.png').convert('L')
bb = ops.mask_bbox(np.asarray(mk))
crop = (max(0,bb[0]-180), max(0,bb[1]-180), min(im.width,bb[2]+180), min(im.height,bb[3]+180))
r = im.crop(crop); m = np.asarray(mk.crop(crop)) > 8
hf = np.asarray(r,np.float32) - np.asarray(r.filter(ImageFilter.GaussianBlur(2.0)),np.float32)
arr = np.asarray(r,np.float32)
print('HF in/out', round(float(hf[m].std()),3), round(float(hf[~m].std()),3))
print('L  in/out', round(float(arr[m].mean()),1), round(float(arr[~m].mean()),1))
print('S  in/out', round(float(arr[m].std()),1), round(float(arr[~m].std()),1))
im.crop((900,900,2500,2000)).save('data/_count/F_zoom1.png')
im.crop((1300,2400,2900,3500)).save('data/_count/F_zoom2.png')
print('DONE')