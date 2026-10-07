"""Make The Chat Place's icon (#64): a speech bubble with "CP".

Run once (it needs Pillow, a development tool only) and commit the output:
    python tools/make_icon.py
Writes thechatplace/assets/app.ico (16 to 256 pixels, each size drawn for
itself so the small ones stay crisp) and app.png (512 pixels, for the Mac
icon and anywhere else).
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "thechatplace" / "assets"
BLUE = (31, 78, 121, 255)
WHITE = (255, 255, 255, 255)
SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]


def _font(size: int):
    for name in ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw(size: int) -> Image.Image:
    """The icon at ``size`` pixels, drawn 4x larger and scaled down."""
    big = size * 4
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    pen = ImageDraw.Draw(image)
    margin = big * 0.06
    body_bottom = big * 0.78
    pen.rounded_rectangle((margin, margin, big - margin, body_bottom),
                          radius=big * 0.2, fill=BLUE)
    # The bubble's tail, low on the left.
    pen.polygon([(big * 0.22, body_bottom - big * 0.02), (big * 0.44, body_bottom - big * 0.02),
                 (big * 0.18, big - margin)], fill=BLUE)
    if size >= 20:
        font = _font(int(big * (0.36 if size >= 32 else 0.42)))
        middle = ((margin + big - margin) / 2, (margin + body_bottom) / 2)
        pen.text(middle, "CP", font=font, fill=WHITE, anchor="mm")
    else:
        # Too small for letters: three dots, a chat bubble's own sign.
        radius = big * 0.07
        y = (margin + body_bottom) / 2
        for x in (big * 0.3, big * 0.5, big * 0.7):
            pen.ellipse((x - radius, y - radius, x + radius, y + radius), fill=WHITE)
    return image.resize((size, size), Image.LANCZOS)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    frames = [draw(size) for size in SIZES]
    frames[-1].save(ASSETS / "app.ico", sizes=[(s, s) for s in SIZES],
                    append_images=frames[:-1])
    draw(512).save(ASSETS / "app.png")
    print(f"Wrote {ASSETS / 'app.ico'} and app.png")


if __name__ == "__main__":
    main()
