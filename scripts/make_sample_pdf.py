"""data/sample_cv.txt dosyasından örnek bir CV PDF'i üretir (PDF girdisini denemek için).

Kullanım: python scripts/make_sample_pdf.py
Türkçe karakterler için bir TTF font gerekir; Windows'ta Arial, Linux'ta DejaVu Sans aranır.
"""
import textwrap
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial.ttf",
]


def main() -> None:
    font_path = next((p for p in FONT_CANDIDATES if Path(p).is_file()), None)
    if font_path is None:
        raise SystemExit("Uygun bir TTF font bulunamadı; FONT_CANDIDATES listesine ekleyin.")
    pdfmetrics.registerFont(TTFont("CV", font_path))

    out = ROOT / "data" / "sample_cv.pdf"
    c = canvas.Canvas(str(out), pagesize=A4)
    width, height = A4
    y, margin, leading = height - 50, 50, 14
    c.setFont("CV", 10)
    lines = []
    for raw in (ROOT / "data" / "sample_cv.txt").read_text(encoding="utf-8").splitlines():
        # uzun satırlar kesilmez, alt satıra sarılır (madde işareti hizası korunur)
        lines += textwrap.wrap(raw, 105, subsequent_indent="  ") or [""]
    for line in lines:
        if y < margin:
            c.showPage()
            c.setFont("CV", 10)
            y = height - 50
        c.drawString(margin, y, line)
        y -= leading
    c.save()
    print(f"Yazıldı: {out}")


if __name__ == "__main__":
    main()
