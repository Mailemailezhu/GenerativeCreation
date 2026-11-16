"""用 pipeline.run 跑 FLUX 分支：草稿 1024 → 正式 1536，和 Qwen 同一套 crop/蒙版。"""
import os, sys, time
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'app'))
from core import pipeline

OUT = os.path.join(ROOT, 'data', '_flux')
os.makedirs(OUT, exist_ok=True)
IMG = os.path.join(ROOT, 'data', 'DSC_4498.png')
MASK = os.path.join(ROOT, 'data', '_plane_mask.png')
PROMPT = ('a flock of white paper airplanes spiraling upward around a young woman, '
          'folded paper texture, soft warm backlight, fine cyan light particles trailing, '
          'photorealistic')

def step(pct, msg):
    print('  %3d%% %s' % (pct, msg), flush=True)


def main():
    side = int(sys.argv[1]) if len(sys.argv) > 1 else 1024
    stage = sys.argv[2] if len(sys.argv) > 2 else 'draft'
    t0 = time.time()
    kw = dict(stage=stage, family='flux', guidance=30.0, steps=20, seed=777,
              progress=step, timeout=2400, unet='flux1-fill-dev-Q5_0.gguf')
    if stage == 'draft':
        kw['draft_side'] = side
        kw['preview_composite'] = False
    else:
        kw['final_side'] = side
    info = pipeline.run(IMG, MASK, PROMPT, **kw)
    out = os.path.join(OUT, 'flux_%s_%d.png' % (stage, side))
    info['image'].save(out)
    print('FLUX_%s side=%d size=%s %.1fs -> %s' % (stage.upper(), side, info['size'], time.time() - t0, out), flush=True)

if __name__ == '__main__':
    main()
