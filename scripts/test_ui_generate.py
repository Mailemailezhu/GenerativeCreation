"""画布冒烟：矩形选框、魔棒、快速选择、抓手平移、对比视图与分割线。"""
import os, sys
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP)
from PyQt5.QtCore import QEvent, QPointF, Qt, QTimer
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QApplication
import main as app_main

app = QApplication(sys.argv)
w = app_main.MainWindow()
w.show()
app.processEvents()
w._load_source(os.path.join(app_main.DATA, "test_input.png"), None)
app.processEvents()
cv = w.canvas
w.set_tool("rect")


def send(kind, x, y):
    pos = cv.mapFromScene(QPointF(x, y))
    btns = Qt.LeftButton if kind != QEvent.MouseButtonRelease else Qt.NoButton
    e = QMouseEvent(kind, QPointF(pos), Qt.LeftButton, btns, Qt.NoModifier)
    if kind == QEvent.MouseButtonPress:
        cv.mousePressEvent(e)
    elif kind == QEvent.MouseMove:
        cv.mouseMoveEvent(e)
    else:
        cv.mouseReleaseEvent(e)


send(QEvent.MouseButtonPress, 560, 180)
send(QEvent.MouseMove, 1060, 560)
send(QEvent.MouseButtonRelease, 1060, 560)
w.prompt_edit.setPlainText("一队发光的纸飞机呈对角线编队飞行，拖曳青蓝色粒子尾迹")
app.processEvents()
print("MASK", cv.mask_bounds(), flush=True)

t0 = time.time()
w.on_generate()
state = {"done": False}


def tick():
    if w._worker is None and not w._busy:
        state["done"] = True
        print("ELAPSED %.1fs has_result=%s mode=%s view_enabled=%s"
              % (time.time() - t0, cv.has_result(), cv.view_mode, w.grp_view.isEnabled()), flush=True)
        print("DRAFT", w._draft_path, flush=True)
        if cv.has_result():
            cv.set_split_axis("v")
            app.processEvents()
            w.grab().save(os.path.join(app_main.DATA, "_ui_split.png"))
            cv.set_view_mode("result")
            app.processEvents()
            w.grab().save(os.path.join(app_main.DATA, "_ui_result_only.png"))
        print("UI_OK", flush=True)
        app.quit()
        return
    if time.time() - t0 > 400:
        print("TIMEOUT busy=%s" % w._busy, flush=True)
        app.quit()
        return
    QTimer.singleShot(2000, tick)


QTimer.singleShot(3000, tick)
sys.exit(app.exec_())