import io, json, sys, time
sys.path.insert(0, 'app')
from pathlib import Path
from PIL import Image
from core import pipeline
from core.comfy_client import ComfyClient, first_image

CROP = Path('data/_gc_tmp/crop.png')
MASK = Path('data/_gc_tmp/mask.png')
OUT = Path('data/_count')
OUT.mkdir(parents=True, exist_ok=True)

P0 = '十架发光的纸飞机呈对角线编队飞行，拖曳青蓝色粒子尾迹'
P1 = '十架发光的纸飞机呈对角线编队飞行，拖曳青蓝色粒子尾迹。画面中有且只有 10 架，从左下到右上等间距排成一条对角线'

def gen(tag, size, steps, cfg, lora, prompt):
    t0 = time.time()
    base = Image.open(CROP).convert('RGB')
    msk = Image.open(MASK).convert('L')
    img = base.resize(size, Image.LANCZOS) if base.size != size else base
    mask = msk.resize(size, Image.LANCZOS) if msk.size != size else msk
    img.save(OUT / (tag + '_in.png'))
    mask.save(OUT / (tag + '_mask.png'))
    c = ComfyClient()
    if not c.is_up():
        raise SystemExit('engine down')
    ni = c.upload_image(str(OUT / (tag + '_in.png')))
    nm = c.upload_image(str(OUT / (tag + '_mask.png')))
    wf = pipeline.build_workflow(size, prompt, ni, nm, steps=steps, cfg=cfg, seed=12345)
    for k, v in wf.items():
        if v['class_type'] == 'LoraLoaderModelOnly':
            v['inputs']['strength_model'] = lora
            v['inputs']['strength_clip'] = lora
    pid = c.queue_prompt(wf)
    e = c.wait_for(pid, timeout=1200)
    fn, sub, ty = first_image(e)
    g = Image.open(io.BytesIO(c.fetch_image(fn, sub, ty))).convert('RGB')
    p = OUT / (tag + '.png')
    g.save(p)
    print('RUN', tag, size, 'steps', steps, 'cfg', cfg, 'lora', lora, round(time.time() - t0, 1), 's', flush=True)

gen('A_base', (488, 600), 4, 1.0, 1.0, P0)
gen('B_prompt', (488, 600), 4, 1.0, 1.0, P1)
gen('C_big', (976, 1200), 4, 1.0, 1.0, P1)
gen('D_nolora', (976, 1200), 16, 3.0, 0.0, P1)
print('ALL_DONE', flush=True)