import sys
sys.path.insert(0, r"D:/LayerForge/app")
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, Qt, QPointF
from PyQt5.QtGui import (QImage, QPainter, QLinearGradient, QColor, QFont,
                         QPainterPath, QPainterPathStroker)
from main import MainWindow

app = QApplication(sys.argv)
w = MainWindow()
w.resize(1440, 900)
w.show()

def step1():
    img = QImage(1600, 1067, QImage.Format_ARGB32)
    g = QLinearGradient(0, 0, 0, img.height())
    g.setColorAt(0.0, QColor("#4a6a8a"))
    g.setColorAt(1.0, QColor("#16202b"))
    p = QPainter(img)
    p.fillRect(img.rect(), g)
    p.setPen(QColor("#e8e8e8"))
    p.setFont(QFont("Microsoft YaHei", 46))
    p.drawText(img.rect(), Qt.AlignCenter, "LayerForge 画布")
    p.end()
    tmp = r"D:/GenerativeCreation/data/_test_canvas.png"
    img.save(tmp)
    w.canvas.load_image(tmp)
    w.canvas.push_undo()
    path = QPainterPath(QPointF(180, 700))
    path.cubicTo(QPointF(600, 380), QPointF(1050, 950), QPointF(1420, 560))
    st = QPainterPathStroker()
    st.setWidth(120)
    outline = st.createStroke(path)
    pp = QPainter(w.canvas.mask)
    pp.setRenderHint(QPainter.Antialiasing)
    pp.fillPath(outline, QColor(255, 64, 64))
    pp.end()
    w.canvas._refresh_mask_item()
    w.canvas.maskChanged.emit()
    w.prompt_edit.setPlainText("一队纸飞机呈对角线编队飞行，拖曳青蓝色发光粒子尾迹…")
    app.processEvents()
    QTimer.singleShot(500, step2)

def step2():
    w.grab().save(r"D:/GenerativeCreation/data/_ui_shot.png")
    app.quit()

QTimer.singleShot(800, step1)
app.exec_()
print("SHOT_OK")
