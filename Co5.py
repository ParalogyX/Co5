import sys
import pathlib
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QSlider, QFileDialog, QPushButton, QGraphicsDropShadowEffect,
    QCheckBox, QLabel
)
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QPainter, QImage, QPdfWriter, QIcon, QColor,
    QPageSize, QFont
)

cur_path = pathlib.Path(__file__).parent.resolve()


#################################################################
# QSlider with snap-to-step behavior
#################################################################
class StepSlider(QSlider):
    def __init__(self, *args, step=30, **kwargs):
        super().__init__(*args, **kwargs)
        self.step = step
        self.valueChanged.connect(self._snap_value)

    def _snap_value(self, v: int):
        snapped = round(v / self.step) * self.step
        if snapped != v:
            self.blockSignals(True)
            self.setValue(snapped)
            self.blockSignals(False)


#################################################################
# Canvas for rendering only (no UI logic inside)
#################################################################
class WheelCanvas(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        # Center label
        self.tonality_label = QLabel("", self)
        self.tonality_label.setAlignment(Qt.AlignCenter)
        self.tonality_label.setStyleSheet("""
            QLabel {
                color: #701e22;
                background: transparent;
            }
        """)

    def resizeEvent(self, event):
        # Position label on screen
        self.tonality_label.resize(self.width(), self.height() + 16)
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        size = min(self.width(), self.height()) * self.parent.scale_UI
        cx = self.width() * 0.5
        cy = self.height() * 0.52
        self.parent.draw_layers(painter, cx, cy, size)


#################################################################
# Main UI widget
#################################################################
class SvgRotator(QWidget):
    def __init__(self):
        super().__init__()

        self.prev_tonality = ""
        self.scale_UI = 0.90
        self.offset = 0

        # SVG layers
        self.svg1 = QSvgWidget(str(cur_path / "11.svg"))
        self.svg2 = QSvgWidget(str(cur_path / "22.svg"))
        self.svg3 = QSvgWidget(str(cur_path / "33.svg"))

        for s in (self.svg1, self.svg2, self.svg3):
            s.setAttribute(Qt.WA_TranslucentBackground, True)

        # Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # ---- Top Controls ----
        top = QHBoxLayout()
        main_layout.addLayout(top)

        self.sliders = []

        # Slider A
        s = StepSlider(Qt.Horizontal, step=30)
        s.setRange(-180, 180)
        s.setValue(0)
        s.valueChanged.connect(self.update_canvas)
        self.sliders.append(s)
        top.addWidget(s)

        # Slider B
        s = StepSlider(Qt.Horizontal)
        s.setRange(-30, 150)
        s.setValue(0)
        s.valueChanged.connect(self.update_canvas)
        self.sliders.append(s)
        top.addWidget(s)

        # Export button
        btn = QPushButton()
        btn.setFixedSize(72, 72)
        btn.setIcon(QIcon(str(cur_path / "save.svg")))
        btn.setIconSize(btn.size() * 0.72)
        btn.setStyleSheet("""
            QPushButton {
                background: white;
                border: 1px solid #d0d0d0;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: #e7f3ff;
                border: 1px solid #5ba4ff;
            }
            QPushButton:pressed {
                background: #d4e7ff;
                border: 1px solid #2b7cff;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(90, 150, 255, 160))
        btn.setGraphicsEffect(shadow)
        btn.clicked.connect(self.export_wheel)
        top.addWidget(btn)

        # ---- Canvas ----
        self.canvas = WheelCanvas(self)
        main_layout.addWidget(self.canvas, 1)

        # ---- Bottom ----
        bottom = QHBoxLayout()
        main_layout.addLayout(bottom)

        self.linkBox = QCheckBox("Link sliders")
        self.linkBox.setStyleSheet("""
            QCheckBox { color: black; font-size: 16px; }
            QCheckBox::indicator { width: 20px; height: 20px; }
            QCheckBox::indicator:checked { background-color: #4da3ff; border: 1px solid #1b6bd8; }
            QCheckBox::indicator:unchecked { background-color: white; border: 1px solid #444; }
        """)
        self.linkBox.stateChanged.connect(self.sync_sliders)
        bottom.addWidget(self.linkBox)
        bottom.addStretch()

        # Window
        self.resize(800, 800)
        self.setMinimumSize(600, 600)
        self.setWindowTitle("Circle of Fifths")

    #################################################################
    # Linked slider mechanics
    #################################################################
    def mirrorAtoB(self, v: int):
        if not self.linkBox.isChecked():
            return
        slave = self.sliders[1]
        minv, maxv = slave.minimum(), slave.maximum()
        span = maxv - minv
        target = v + self.offset
        if span > 0:
            while target < minv: target += span
            while target > maxv: target -= span
        step = getattr(slave, "step", 1)
        target = round(target / step) * step
        slave.blockSignals(True)
        slave.setValue(int(target))
        slave.blockSignals(False)
        self.update_canvas()

    def mirrorBtoA(self, v: int):
        if not self.linkBox.isChecked():
            return
        slave = self.sliders[0]
        minv, maxv = slave.minimum(), slave.maximum()
        span = maxv - minv
        target = v - self.offset
        if span > 0:
            while target < minv: target += span
            while target > maxv: target -= span
        step = getattr(slave, "step", 1)
        target = round(target / step) * step
        slave.blockSignals(True)
        slave.setValue(int(target))
        slave.blockSignals(False)
        self.update_canvas()

    def sync_sliders(self):
        if self.linkBox.isChecked():
            self.offset = self.sliders[1].value() - self.sliders[0].value()
            self.sliders[0].valueChanged.connect(self.mirrorAtoB)
            self.sliders[1].valueChanged.connect(self.mirrorBtoA)
            self.sliders[0].setRange(-180, 180)
            self.sliders[1].setRange(-180, 180)
        else:
            self.sliders[0].setRange(-180, 180)
            self.sliders[1].setRange(-30, 150)
            try: self.sliders[0].valueChanged.disconnect(self.mirrorAtoB)
            except: pass
            try: self.sliders[1].valueChanged.disconnect(self.mirrorBtoA)
            except: pass

    def update_canvas(self):
        self.canvas.update()

    #################################################################
    # Draw SVG layers and update the on-screen label
    #################################################################
    def draw_layers(self, painter: QPainter, cx: float, cy: float, size: float):

        # --- Helper: draw SVG layer ---
        def draw(svg, angle):
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(angle)
            rect = QRectF(-size/2, -size/2, size, size)
            svg.renderer().render(painter, rect)
            painter.restore()

        # --- Helper: compute tonality ---
        def get_tonality(a, b):
            def mode(a):
                a = a % 360
                idx = (a // 30) % 12
                modes = ["Major", "Mixolydian", "Dorian", "Minor", "Phrygian",
                         "Locrian", "", "", "", "", "", "Lydian"]
                return modes[int(idx)]

            def rotate(lst, n):
                return lst[n:] + lst[:n]

            a = a % 360
            idx = (a // 30) % 12

            keys = ["G", "D", "A", "E", "B", "F#", "C#",
                    "Ab", "Eb", "Bb", "F", "C"][::-1]

            md = mode(b)

            shifts = {
                "Lydian": 1, "Mixolydian": -1, "Dorian": -2,
                "Minor": -3, "Phrygian": -4, "Locrian": -5,
                "Major": 0
            }
            if md not in shifts:
                return ""

            keys = rotate(keys, shifts[md])
            return keys[int(idx)] + " " + md

        # Draw layers
        draw(self.svg1, self.sliders[0].value())
        draw(self.svg2, self.sliders[1].value())
        draw(self.svg3, 0)

        # Update label
        tonality = get_tonality(self.sliders[0].value(), self.sliders[1].value())

        if tonality != self.prev_tonality:
            font = self.canvas.tonality_label.font()

            if any(w in tonality for w in ["Mixolydian", "Phrygian", "Locrian"]):
                font.setPointSize(20)
            else:
                font.setPointSize(26)

            self.canvas.tonality_label.setFont(font)
            self.canvas.tonality_label.setText(tonality)

        self.prev_tonality = tonality


    #################################################################
    # Export PNG / PDF
    #################################################################
    def export_wheel(self):

        filename = self.prev_tonality if self.prev_tonality else "circle"

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Wheel", filename,
            "PDF Document (*.pdf);;PNG Image (*.png)"
        )
        if not path:
            return

        tonality = self.prev_tonality

        #################################################################
        # PNG EXPORT
        #################################################################
        if path.lower().endswith(".png"):

            size = 2048
            img = QImage(size, size, QImage.Format_ARGB32)
            img.fill(Qt.white)

            p = QPainter(img)
            cx = size * 0.5
            cy = size * 0.5
            diameter = size * 0.90

            # Draw SVG layers
            self.draw_layers(p, cx, cy + 20, diameter)

            # Draw label (scaled proportional to wheel)
            export_font = QFont(self.canvas.tonality_label.font())

            # Scale font relative to image resolution
            export_font.setPointSize(int(size * 0.035))   # ~3.5% of image height
            p.setFont(export_font)

            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(tonality)
            th = fm.height()

            # Vertical offset based on wheel diameter (natural-looking)
            y = cy + th * 0.35

            p.setPen(QColor("#701e22"))
            p.drawText(int(cx - tw/2), int(y), tonality)

            p.end()
            img.save(path)
            return

        #################################################################
        # PDF EXPORT
        #################################################################
        if path.lower().endswith(".pdf"):

            pdf = QPdfWriter(path)
            pdf.setPageSize(QPageSize(QPageSize.A4))

            page_w = pdf.width()
            page_h = pdf.height()
            circle = int(page_w * 0.90)

            img = QImage(circle, circle, QImage.Format_ARGB32)
            img.fill(Qt.white)

            p_img = QPainter(img)
            cx = circle * 0.5
            cy = circle * 0.5
            diameter = circle * 0.90

            # Draw SVG layers
            self.draw_layers(p_img, cx, cy+70, diameter)

            # Draw label (scaled proportional to PDF circle size)
            export_font = QFont(self.canvas.tonality_label.font())

            # PDF scaling: circle is in *PDF units*, we scale relative to circle diameter
            export_font.setPointSize(int(circle * 0.035))  # ~3.5% of diameter
            p_img.setFont(export_font)

            fm = p_img.fontMetrics()
            tw = fm.horizontalAdvance(tonality)
            th = fm.height()

            y = cy + th * 0.35   # same proportional vertical shift

            p_img.setPen(QColor("#701e22"))
            p_img.drawText(int(cx - tw/2), int(y), tonality)

            p_img.end()

            # Draw the image onto the PDF
            p_pdf = QPainter(pdf)
            x = (page_w - circle) // 2
            y = (page_h - circle) // 2
            p_pdf.drawImage(x, y, img)
            p_pdf.end()
            return


#################################################################
# Entry point
#################################################################
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet("QWidget { background-color: white; }")

    window = SvgRotator()
    window.show()
    sys.exit(app.exec())
