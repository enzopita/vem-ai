"""Gera icon-192.png e icon-512.png a partir do desenho de icon.svg. Uso: uv run --with pillow scripts/make_icons.py"""
from pathlib import Path

from PIL import Image, ImageDraw

STATIC = Path(__file__).resolve().parent.parent / "web" / "static"
BLUE, WHITE = (91, 63, 224), (255, 255, 255)
FROM, TO = (79, 70, 229), (192, 38, 211)


def draw(size: int) -> Image.Image:
    k = size / 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def rect(x, y, w, h, r, fill):
        d.rounded_rectangle([x * k, y * k, (x + w) * k, (y + h) * k], radius=r * k, fill=fill)

    def circle(cx, cy, r, fill):
        d.ellipse([(cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k], fill=fill)

    gradient = Image.new("L", (size, size))
    gradient.putdata([round((x + y) * 255 / (2 * size - 2)) for y in range(size) for x in range(size)])
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size, size], radius=96 * k, fill=255)
    img.paste(Image.composite(Image.new("RGB", (size, size), TO), Image.new("RGB", (size, size), FROM), gradient), mask=mask)
    rect(96, 120, 320, 240, 40, WHITE)
    rect(128, 152, 256, 96, 16, BLUE)
    circle(176, 392, 36, WHITE)
    circle(336, 392, 36, WHITE)
    rect(136, 280, 48, 24, 8, BLUE)
    rect(328, 280, 48, 24, 8, BLUE)
    return img


for size in (192, 512):
    draw(size).save(STATIC / f"icon-{size}.png")
