import os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'app'))
import bootstrap; bootstrap.apply()
from PyQt5.QtWidgets import QApplication
from PIL import Image
app = QApplication(sys.argv)
import main as M
w = M.MainWindow()
w.canvas.load_image(Image.new('RGB', (3434, 5151), (20, 40, 90)))
print('QWEN side', w._draft_side())
w.on_model_selected('flux-fill-q5')
print('FLUX side', w._draft_side(), 'ratio', w.preview_ratio)
