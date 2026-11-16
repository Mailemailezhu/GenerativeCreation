import sys, time, numpy as np
sys.path.insert(0, 'app')
from PIL import Image, ImageFilter
from core import pipeline, image_ops as ops
P = '十架发光的纸飞机呈对角线编队飞行，拖曳青蓝色粒子尾迹'
def stats(path):
    im = Image.open(path).convert('RGB')
    mk = Image.open('data/_gc_mask.png').convert('L')
    crop = (max(0,597-180), max(0,273-180), min(im.width,3211+180), min(im.height,3554+180))
    r = im.crop(crop); m = np.asarray(mk.crop(crop)) > 8
    hf = np.asarray(r,np.float32) - np.asarray(r.filter(ImageFilter.GaussianBlur(2.0)),np.float32)
    arr = np.asarray(r,np.float32)
    print(path, 'HF in/out', round(float(hf[m].std()),3), round(float(hf[~m].std()),3),
          'L', round(float(arr[m].mean()),1), 'S', round(float(arr[m].std()),1))
t0 = time.time()
info = pipeline.run('data/_gc_preview.png', 'data/_gc_mask.png', P, 'data/_count/G_dn07.png',
                    stage='final', draft_path='data/_gc_preview.png', steps=4, cfg=1.0,
                    seed=777, denoise=0.7)
print('FINAL07', round(time.time()-t0,1), 's', info['crop'], info['size'])
stats('data/_count/G_dn07.png')
stats('data/_count/F_final.png')
Image.open('data/_count/G_dn07.png').crop((900,900,2500,2000)).save('data/_count/G_zoom1.png')
print('DONE')