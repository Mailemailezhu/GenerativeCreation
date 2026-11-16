import json, sys, os, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
from core import pipeline
wf = pipeline.build_flux_workflow('a cat', 'gc_crop.png', 'gc_mask.png', steps=20, guidance=30, seed=5)
cls = sorted({v['class_type'] for v in wf.values()})
data = json.load(urllib.request.urlopen('http://127.0.0.1:8188/object_info', timeout=30))
missing = [c for c in cls if c not in data]
print('CLASSES', cls)
print('MISSING', missing)
print('KSAMPLER', wf['11']['inputs']['steps'], wf['11']['inputs']['seed'], 'GUID', wf['10']['inputs']['guidance'])
