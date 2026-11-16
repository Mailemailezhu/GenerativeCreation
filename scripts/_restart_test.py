import os, sys, time
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'app'))
import bootstrap
bootstrap.apply()
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QCoreApplication
app = QApplication(sys.argv)
import main as M
from core import comfy_client, pipeline
w = M.MainWindow()
pid0 = w._engine_pid()
print('PID0', pid0, 'up', comfy_client.ComfyClient().is_up())
w._engine_ok = True
w.restart_engine()
t0 = time.time()
ok = False
while time.time() - t0 < 200:
    QCoreApplication.processEvents()
    if comfy_client.ComfyClient().is_up():
        ok = True
        break
    time.sleep(1.0)
pid1 = w._engine_pid()
print('PID1', pid1, 'up', ok, 'elapsed %.1f' % (time.time() - t0))
print('SAME_PID', pid0 == pid1)
