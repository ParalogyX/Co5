
import sys
import pathlib
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QSlider, QFileDialog, QPushButton, QGraphicsDropShadowEffect
)
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QPainter, QImage, QPdfWriter, QIcon, QPixmap, QColor
)

cur_path = pathlib.Path(__file__).parent.resolve()


###############################################################
# Slider with snapping steps
###############################################################
class StepSlider(QSlider):
    def __init__(self, *args, step=30, **kwargs):
        super().__init__(*args, **kwargs)
        self.step = step
        self.valueChanged.connect(self.snap_value)

    def snap_value(self, v: int):
        new = round(v / self.step) * self.step
        if new != v:
            self.blockSignals(True)
            self.setValue(new)
            self.blockSignals(False)


###############################################################
# Main widget: rotating SVG layers + export
###############################################################
class SvgRotator(QWidget):
    def __init__(self):
        super().__init__()

        # UI scale factor for on-screen drawing
        self.scale_UI = 0.90

        # SVG layers (these files must exist)
        self.svg1 = QSvgWidget(str(cur_path / "11.svg"))
        self.svg2 = QSvgWidget(str(cur_path / "22.svg"))
        self.svg3 = QSvgWidget(str(cur_path / "33.svg"))

        for s in (self.svg1, self.svg2, self.svg3):
            s.setAttribute(Qt.WA_TranslucentBackground, True)

        # ───────────────── UI LAYOUT ─────────────────
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        layout.addLayout(top)

        # Rotation sliders
        self.sliders = []

        s = StepSlider(Qt.Horizontal, step=10)
        s.setRange(-180, 180)
        s.setValue(0)
        s.setSingleStep(30)
        s.setTickInterval(30)
        s.valueChanged.connect(self.update)
        self.sliders.append(s)
        top.addWidget(s)

        s = StepSlider(Qt.Horizontal)
        s.setRange(-30, 150)
        s.setValue(0)
        s.setSingleStep(30)
        s.setTickInterval(30)
        s.valueChanged.connect(self.update)
        self.sliders.append(s)
        top.addWidget(s)


        # ================= SAVE BUTTON — SVG + REAL SHADOW + HOVER =================
        btn = QPushButton()
        btn.setFixedSize(72, 72)

        # Material Save icon
        btn.setIcon(QIcon(str(cur_path / "save.svg")))
        btn.setIconSize(btn.size() * 0.72)

        # subtle styling — no invalid properties now
        btn.setStyleSheet("""
            QPushButton {
                background:white;
                border:1px solid #d0d0d0;
                border-radius:10px;
            }
            QPushButton:hover {
                background:#e7f3ff;
                border:1px solid #5ba4ff;
            }
            QPushButton:pressed {
                background:#d4e7ff;
                border:1px solid #2b7cff;
            }
        """)

        # REAL drop-shadow (dynamic, bright when hovered)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(90, 150, 255, 160))  # soft blue glow
        btn.setGraphicsEffect(shadow)

        # click handler
        btn.clicked.connect(self.export_wheel)
        top.addWidget(btn)


        layout.addStretch()

        # Window behaviour
        self.resize(800, 800)
        self.setMinimumSize(600, 600)
        self.setWindowTitle("Circle of Fifths")

    ###############################################################
    # Export current wheel state to PNG or PDF
    ###############################################################
    def export_wheel(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Wheel",
            "circle",
            "PDF Document (*.pdf);;PNG Image (*.png)"  # PDF first
        )
        if not path:
            return

        # ---------- PNG: fixed 2048x2048, wheel = 90% ----------
        if path.lower().endswith(".png"):
            size = 2048
            img = QImage(size, size, QImage.Format_ARGB32)
            img.fill(Qt.white)

            painter = QPainter(img)
            cx = size * 0.5
            cy = size * 0.5
            diameter = size * 0.90  # 90% of image
            self.draw_layers(painter, cx, cy, diameter)
            painter.end()

            img.save(path)
            return

        # ---------- PDF: A4, wheel = 90% of page width ----------
        if path.lower().endswith(".pdf"):

            from PySide6.QtGui import QPageSize  # <-- REQUIRED FIX

            pdf = QPdfWriter(path)
            pdf.setPageSize(QPageSize(QPageSize.A4))  # <-- FIXED

            page_w = pdf.width()
            page_h = pdf.height()
            circle = int(page_w * 0.90)

            img = QImage(circle, circle, QImage.Format_ARGB32)
            img.fill(Qt.white)

            p_img = QPainter(img)
            cx = circle * 0.5
            cy = circle * 0.5
            diameter = circle * 0.90
            self.draw_layers(p_img, cx, cy, diameter)
            p_img.end()

            p_pdf = QPainter(pdf)
            x = (page_w - circle) // 2
            y = (page_h - circle) // 2
            p_pdf.drawImage(x, y, img)
            p_pdf.end()
            return

    ###############################################################
    # On-screen paint
    ###############################################################
    def paintEvent(self, event):
        painter = QPainter(self)
        size = min(self.width(), self.height() - 60) * self.scale_UI
        cx = self.width() * 0.5
        cy = self.height() * 0.52  # slight shift down, like before
        self.draw_layers(painter, cx, cy, size)

    ###############################################################
    # Core drawing routine (used for screen + export)
    ###############################################################
    def draw_layers(self, painter: QPainter, cx: float, cy: float, size: float):
        def draw(svg: QSvgWidget, angle: float):
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(angle)
            r = QRectF(-size / 2, -size / 2, size, size)
            svg.renderer().render(painter, r)
            painter.restore()

        draw(self.svg1, self.sliders[0].value())
        draw(self.svg2, self.sliders[1].value())
        draw(self.svg3, 0)


###############################################################
# Entry point
###############################################################
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget { background-color: white; }
    """)

    window = SvgRotator()   # IMPORTANT: keep a reference!
    window.show()
    sys.exit(app.exec())
