import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QSlider
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPalette, QColor


class StepSlider(QSlider):
    def __init__(self, *args, step=30, **kwargs):
        super().__init__(*args, **kwargs)
        self.step = step

        self.valueChanged.connect(self._snapValue)  # internal filter

    def _snapValue(self, value):
        snapped = round(value / self.step) * self.step
        if snapped != value:
            self.blockSignals(True)
            self.setValue(snapped)
            self.blockSignals(False)

class SvgRotator(QWidget):
    def __init__(self):
        super().__init__()

        # Load three layered SVG widgets
        self.svg1 = QSvgWidget("1.svg")
        self.svg2 = QSvgWidget("2.svg")
        self.svg3 = QSvgWidget("3.svg")

        self.svg1.setFixedSize(1000, 1000)  # change freely
        self.svg1.setAutoFillBackground(True)
        pal = self.svg1.palette()
        pal.setColor(QPalette.Window, QColor("white"))
        self.svg1.setPalette(pal)

        # All SVGs same size + stacked
        for svg in (self.svg2, self.svg3):
            svg.setFixedSize(1000, 1000)  # change freely
            svg.setAttribute(Qt.WA_TranslucentBackground, True)

        # Slider panel
        slider_layout = QHBoxLayout()
        self.sliders = []

        
        slider = StepSlider(Qt.Horizontal)
        slider.setRange(-180, 180)
        slider.setValue(0)  # initial angle
        slider.setSingleStep(30)
        slider.setTickInterval(30)
        slider.valueChanged.connect(self.update)
        self.sliders.append(slider)
        slider_layout.addWidget(slider)

        slider = StepSlider(Qt.Horizontal)
        slider.setRange(-30, 150)
        slider.setValue(0)  # initial angle
        slider.setSingleStep(30)
        slider.setTickInterval(30)
        slider.valueChanged.connect(self.update)
        self.sliders.append(slider)
        slider_layout.addWidget(slider)

        # Main layout
        layout = QVBoxLayout(self)
        layout.addLayout(slider_layout)
        layout.addStretch()

        self.setFixedSize(1020, 1080)
        self.setWindowTitle("Circle of Fifths")


    # def snapValue(self, value):
    #     step = 30
    #     snapped = round(value / step) * step  # Snap to 30
    #     if snapped != value:                   # Avoid endless signal loop
    #         self.sliders[0].blockSignals(True)
    #         self.sliders[0].setValue(snapped)
    #         self.sliders[0].blockSignals(False)


    def paintEvent(self, event):
        painter = QPainter(self)

        # Center of drawing area
        cx = self.width() / 2
        cy = (self.height() / 2) + 20

        # Drawing function for each rotated svg
        def draw_svg(svg_widget, angle):
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(angle)
            painter.translate(-svg_widget.width() / 2, -svg_widget.height() / 2)
            svg_widget.renderer().render(painter, QRectF(0, 0, svg_widget.width(), svg_widget.height()))
            painter.restore()

        # Draw all three images on top of each other
        draw_svg(self.svg1, self.sliders[0].value())
        draw_svg(self.svg2, self.sliders[1].value())
        draw_svg(self.svg3, 0)#self.sliders[2].value())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet("""
    QWidget {
        background-color: white;
    }
""")

    window = SvgRotator()
    window.show()
    sys.exit(app.exec())
