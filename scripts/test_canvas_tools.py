"""画布冒烟：矩形选框、魔棒、快速选择、抓手平移、对比视图与分割线。"""
import os, sys
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
sys.path.insert(0, APP)
from PyQt5.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QApplication
import main as app_main


def send(widget, kind, pos, btn=Qt.LeftButton, mods=Qt.NoModifier, buttons=None):
    btns = buttons if buttons is not None else (btn if kind != QEvent.MouseButtonRelease else Qt.NoButton)
    e = QMouseEvent(kind, QPointF(pos), btn, btns, mods)
    if kind == QEvent.MouseButtonPress:
        widget.mousePressEvent(e)
    elif kind == QEvent.MouseMove:
        widget.mouseMoveEvent(e)
    else:
        widget.mouseReleaseEvent(e)


def to_view(cv, x, y):
    return cv.mapFromScene(QPointF(x, y))


app = QApplication(sys.argv)
w = app_main.MainWindow()
w.show()
app.processEvents()
scr = app.primaryScreen()
print("SCALE dpr=%.2f dpi=%d win=%dx%d" % (scr.devicePixelRatio(), scr.logicalDotsPerInch(), w.width(), w.height()))
print("GRAB", w.grab().width(), w.grab().height())
print("TOOLS", [a.text() for a in w.tool_group.actions() if a.text()])

w._load_source(os.path.join(app_main.DATA, "test_input.png"), None)
app.processEvents()
cv = w.canvas

# 1 矩形选框
w.set_tool("rect")
print("VIS rect brush=%s tol=%s sel=%s" % (w.grp_brush.isVisible(), w.grp_tol.isVisible(), w.grp_sel.isVisible()))
p0, p1 = to_view(cv, 200, 100), to_view(cv, 500, 300)
send(cv, QEvent.MouseButtonPress, p0)
send(cv, QEvent.MouseMove, p1, buttons=Qt.LeftButton)
send(cv, QEvent.MouseButtonRelease, p1)
app.processEvents()
b = cv.mask_bounds()
print("RECT bounds=(%.0f,%.0f %.0fx%.0f) undo=%d" % (b.x(), b.y(), b.width(), b.height(), len(cv._undo)))

# 2 魔棒：点天空
cv.clear_mask()
w.set_tool("wand")
print("VIS wand brush=%s tol=%s" % (w.grp_brush.isVisible(), w.grp_tol.isVisible()))
send(cv, QEvent.MouseButtonPress, to_view(cv, 100, 40))
send(cv, QEvent.MouseButtonRelease, to_view(cv, 100, 40))
app.processEvents()
b = cv.mask_bounds()
print("WAND bounds=(%.0f,%.0f %.0fx%.0f)" % (b.x(), b.y(), b.width(), b.height()))
cv.mask.copy().save(os.path.join(app_main.DATA, "_mask_wand.png"))

# 3 快速选择：在人物上拖一笔，只吸相近颜色
cv.clear_mask()
w.set_tool("quick")
a, c = to_view(cv, 660, 260), to_view(cv, 700, 320)
send(cv, QEvent.MouseButtonPress, a)
send(cv, QEvent.MouseMove, c, buttons=Qt.LeftButton)
send(cv, QEvent.MouseButtonRelease, c)
app.processEvents()
b = cv.mask_bounds()
print("QUICK bounds=(%.0f,%.0f %.0fx%.0f)" % (b.x(), b.y(), b.width(), b.height()))

# 4 抓手平移：先放大，再拖动，看滚动条有没有动
cv.zoom_to(2.0)
app.processEvents()
w.set_tool("hand")
app.processEvents()
print("VIS hand brush=%s tol=%s sel=%s" % (w.grp_brush.isVisible(), w.grp_tol.isVisible(), w.grp_sel.isVisible()))
h0 = cv.horizontalScrollBar().value()
send(cv, QEvent.MouseButtonPress, QPoint(500, 300))
send(cv, QEvent.MouseMove, QPoint(380, 240), buttons=Qt.LeftButton)
send(cv, QEvent.MouseButtonRelease, QPoint(380, 240))
app.processEvents()
print("PAN hscroll %d -> %d range=%d" % (h0, cv.horizontalScrollBar().value(),
                                        cv.horizontalScrollBar().maximum()))

# 5 对比视图
out = os.path.join(app_main.DATA, "out_draft.png")
ok = cv.set_result(out) if os.path.exists(out) else False
app.processEvents()
print("RESULT ok=%s mode=%s view_enabled=%s" % (ok, cv.view_mode, w.grp_view.isEnabled()))
if ok:
    cv.set_split_axis("v")
    ratio0 = cv.split_ratio
    line_x = cv.mapFromScene(QPointF(cv.image.width() * cv.split_ratio, 0)).x()
    send(cv, QEvent.MouseButtonPress, QPoint(int(line_x), 300))
    send(cv, QEvent.MouseMove, QPoint(int(line_x) - 160, 300), buttons=Qt.LeftButton)
    send(cv, QEvent.MouseButtonRelease, QPoint(int(line_x) - 160, 300))
    app.processEvents()
    print("SPLIT ratio %.2f -> %.2f line_visible=%s" % (ratio0, cv.split_ratio,
                                                       cv._split_line.isVisible()))
    cv.fit_view()
    app.processEvents()
    w.grab().save(os.path.join(app_main.DATA, "_ui_compare.png"))
    cv.set_split_axis("h")
    app.processEvents()
    w.grab().save(os.path.join(app_main.DATA, "_ui_compare_h.png"))
    cv.set_view_mode("result")
    app.processEvents()
    print("VIEW result base_visible=%s res_visible=%s" % (cv._pix_item.isVisible(),
                                                          cv._result_item.isVisible()))
    cv.set_view_mode("original")
    print("VIEW original base_visible=%s res_visible=%s" % (cv._pix_item.isVisible(),
                                                            cv._result_item.isVisible()))

print("SHOT_OK")