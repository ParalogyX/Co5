from flask import Flask, request, send_file, render_template
from io import BytesIO
import tempfile
import os

from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import (
    QImage,
    QPainter,
    QPdfWriter,
    QGuiApplication,
    QPageSize,
    QFont,
    QColor,
)
from PySide6.QtCore import Qt, QRectF

# Qt must exist to render fonts & SVG correctly
qt_app = QGuiApplication([])

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


def render_svg_layer(svg: str, angle: int, size: int) -> QImage:
    """Render a single SVG layer using Qt, scaled and rotated."""
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)

    renderer = QSvgRenderer(svg.encode("utf-8"))
    p = QPainter(img)
    renderer.render(p, QRectF(0, 0, size, size))  # scale SVG to image
    p.end()

    if angle == 0:
        return img

    rotated = QImage(size, size, QImage.Format_ARGB32)
    rotated.fill(Qt.transparent)

    p2 = QPainter(rotated)
    p2.translate(size / 2, size / 2)
    p2.rotate(angle)  # clockwise, matches PySide app
    p2.translate(-size / 2, -size / 2)
    p2.drawImage(0, 0, img)
    p2.end()

    return rotated


@app.post("/export")
def export():
    fmt = request.form["format"].lower()
    a1, a2 = map(int, request.form["angles"].split(","))

    svg1 = request.form["svg1"]
    svg2 = request.form["svg2"]
    svg3 = request.form["svg3"]

    # Tonality computed in JS and passed here
    tonality = (request.form.get("tonality") or "").strip()

    size = 2048

    # Composite final wheel image (SVG layers)
    final = QImage(size, size, QImage.Format_ARGB32)
    final.fill(Qt.white)

    p = QPainter(final)
    p.drawImage(0, 0, render_svg_layer(svg1, a1, size))
    p.drawImage(0, 0, render_svg_layer(svg2, a2, size))
    p.drawImage(0, 0, render_svg_layer(svg3, 0, size))
    p.end()

    # -----------------------------------------------------------
    # Draw tonality label into the final image (for PNG and PDF)
    # -----------------------------------------------------------
    if tonality:
        p = QPainter(final)
        cx = size / 2
        cy = size / 2

        # Same logic as in JS/PySide: long mode words → slightly smaller font
        long_words = ("Mixolydian", "Phrygian", "Locrian")
        factor = 0.035 if any(w in tonality for w in long_words) else 0.04

        font = QFont()
        font.setPointSize(int(size * factor))  # ~3–3.5% of image size
        p.setFont(font)

        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(tonality)
        th = fm.height()

        y = cy + th * 0.35

        p.setPen(QColor("#701e22"))
        p.drawText(int(cx - tw / 2), int(y-20), tonality)
        p.end()

    # Safe filename base
    base_name = tonality if tonality else "circle"
    base_name = base_name.replace(" ", "_")

    # ---------- PNG ----------
    if fmt == "png":
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            name = tmp.name

        final.save(name, "PNG", quality=100)
        data = open(name, "rb").read()
        os.remove(name)

        return send_file(
            BytesIO(data),
            as_attachment=True,
            download_name=f"{base_name}.png",
            mimetype="image/png",
        )

    # ---------- PDF ----------
    if fmt == "pdf":
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            name = tmp.name

        pdf = QPdfWriter(name)
        pdf.setPageSize(QPageSize(QPageSize.A4))
        pdf.setResolution(600)

        p = QPainter(pdf)

        pw, ph = pdf.width(), pdf.height()
        target_w = pw * 0.9
        scale = target_w / size
        target_h = size * scale

        x = (pw - target_w) / 2
        y = (ph - target_h) / 2

        # final already contains label
        p.drawImage(
            x,
            y,
            final.scaled(
                int(target_w),
                int(target_h),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            ),
        )
        p.end()

        data = open(name, "rb").read()
        os.remove(name)

        return send_file(
            BytesIO(data),
            as_attachment=True,
            download_name=f"{base_name}.pdf",
            mimetype="application/pdf",
        )

    return "Unsupported format", 400


if __name__ == "__main__":
    app.run(debug=True)
