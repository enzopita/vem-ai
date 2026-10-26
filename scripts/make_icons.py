"""Gera icon-192.png e icon-512.png a partir do desenho de icon.svg. Uso: uv run --with pillow scripts/make_icons.py"""
from pathlib import Path

from PIL import Image, ImageDraw

STATIC = Path(__file__).resolve().parent.parent / "frontend" / "static"
INK, WHITE, GREEN = (11, 13, 18), (255, 255, 255), (60, 207, 122)


def draw(size: int) -> Image.Image:
    # Desenha a 4x e reduz, para as curvas saírem suaves.
    big = size * 4
    k = big / 512
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def rect(x, y, w, h, r, fill=None, outline=None, width=0):
        d.rounded_rectangle([x * k, y * k, (x + w) * k, (y + h) * k], radius=r * k, fill=fill, outline=outline, width=round(width * k))

    def circle(cx, cy, r, fill):
        d.ellipse([(cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k], fill=fill)

    # O V de "Vem" descendo até o ponto verde: o ônibus chegando onde a pessoa está.
    rect(0, 0, 512, 512, 112, fill=INK)
    d.line([(120 * k, 128 * k), (256 * k, 360 * k), (392 * k, 128 * k)], fill=WHITE, width=round(56 * k), joint="curve")
    for x, y in ((120, 128), (256, 360), (392, 128)):
        circle(x, y, 28, WHITE)
    circle(256, 392, 72, INK)
    circle(256, 392, 52, GREEN)
    return img.resize((size, size), Image.LANCZOS)


for size in (192, 512):
    draw(size).save(STATIC / f"icon-{size}.png")
