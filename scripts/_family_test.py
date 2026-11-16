import os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'app'))
import bootstrap
bootstrap.apply()
from PyQt5.QtWidgets import QApplication
app = QApplication(sys.argv)
import main as M
w = M.MainWindow()
w.refresh_models()
w.model_id = 'qwen2511-q5'
w.refresh_models()
print('QWEN steps', w.steps_spin.value(), 'guid', w.guidance_spin.value(), 'cfg_en', w.cfg_spin.isEnabled(), 'guid_en', w.guidance_spin.isEnabled(), 'assets_en', w.asset_strip.isEnabled(), 'lock_en', w.lock_spin.isEnabled())
w.on_model_selected('flux-fill-q5')
print('FLUX id', w.model_id, 'steps', w.steps_spin.value(), 'guid', w.guidance_spin.value(), 'cfg_en', w.cfg_spin.isEnabled(), 'guid_en', w.guidance_spin.isEnabled(), 'assets_en', w.asset_strip.isEnabled(), 'lock_en', w.lock_spin.isEnabled())
print('EFAM', w._family(), 'UNET', w._unet(), 'FINAL', (M.catalog.by_id(w.model_id) or {}).get('final_side'))
from PIL import Image as PILImage
w.canvas.load_image(PILImage.new('RGB', (1200, 800), (30, 60, 120)))
kw = w._gen_kw('test', 'draft')
print('KW', {k: kw[k] for k in ('family', 'guidance', 'final_side', 'unet', 'steps', 'draft_side') if k in kw})
print('EST', w.estimate_label.text())
w.on_model_selected('qwen2511-q5')
print('BACK steps', w.steps_spin.value(), 'cfg_en', w.cfg_spin.isEnabled(), 'guid_en', w.guidance_spin.isEnabled(), 'assets_en', w.asset_strip.isEnabled())
