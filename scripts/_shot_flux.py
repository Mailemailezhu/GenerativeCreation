"""真实平台截图：切到 FLUX，检查步数/引导强度/禁用项。"""
import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'app'))
import bootstrap  # noqa: E402
bootstrap.apply()
from PyQt5.QtCore import Qt, QTimer  # noqa: E402
from PyQt5.QtGui import QColor, QPainter  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402
import main as app_main  # noqa: E402

app = QApplication(sys.argv)
w = app_main.MainWindow()
w.resize(1444, 900)
w.show()
w._load_source(os.path.join(ROOT, 'data', 'test_input.tif'))
p = QPainter(w.canvas.mask)
p.setPen(Qt.NoPen)
p.setBrush(QColor(255, 0, 0, 255))
p.drawEllipse(700, 300, 320, 240)
p.end()
w.canvas._refresh_mask_item()
w.canvas.maskChanged.emit()
w.on_mask_changed()
w.model_head.setChecked(True)
w.on_model_toggle(True)
w.on_model_selected('flux-fill-q5')
w.adv_head.setChecked(True)
w.adv_box.setVisible(True)
print('STATE', w.model_id, w.steps_spin.value(), w.guidance_spin.value(),
      w.cfg_spin.isEnabled(), w.guidance_spin.isEnabled(), w.asset_strip.isEnabled(), flush=True)

def shot():
    w.panel_scroll.verticalScrollBar().setValue(10 ** 6)
    w.grab().save(os.path.join(ROOT, 'data', '_ui_flux.png'))
    print('SHOT_OK', flush=True)
    app.quit()

QTimer.singleShot(1600, shot)
sys.exit(app.exec_())
