"""Branded placeholder images for products that have no photo yet.

Each product gets a card in the brand colour (#7A3E65) with its Arabic name and the word "لمسة",
written to data/product-images/<sku>/main.png. Replacing it later is deliberately trivial: drop a
real main.jpg (then 2.jpg, 3.jpg, …) into the same folder and re-run the importer — `find_images`
prefers whatever real files are there and only falls back to the placeholder.

Pillow draws the placeholder when it is available. It usually is on a bench (ERPNext depends on it),
but if it is missing this writes a valid SVG instead, so seeding never fails for lack of an image
library.
"""

import os

BRAND_COLOR = "#7A3E65"
BRAND_RGB = (0x7A, 0x3E, 0x65)
CANVAS = 900
REAL_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".avif")
#: Real photos are named main.*, 2.*, 3.* … ; the generated card is placeholder.*
PLACEHOLDER_STEM = "placeholder"
MAIN_STEM = "main"


def find_images(folder: str) -> list[str]:
	"""Real product photos in display order: main first, then 2, 3, …; placeholder only if alone."""
	if not os.path.isdir(folder):
		return []
	files = os.listdir(folder)

	def by_stem(stem: str) -> list[str]:
		out = []
		for ext in REAL_EXTS:
			name = f"{stem}{ext}"
			if name in files:
				out.append(os.path.join(folder, name))
		return out

	ordered: list[str] = []
	ordered += by_stem(MAIN_STEM)
	for n in range(2, 11):
		ordered += by_stem(str(n))

	if ordered:
		return ordered
	# no real photos: use the placeholder if one was generated
	return by_stem(PLACEHOLDER_STEM)


def ensure_placeholder(folder: str, title_ar: str) -> str | None:
	"""Create (once) and return the branded placeholder for a product, or None if it cannot draw one."""
	os.makedirs(folder, exist_ok=True)
	png = os.path.join(folder, f"{PLACEHOLDER_STEM}.png")
	if os.path.exists(png):
		return png
	if _draw_png(png, title_ar):
		return png
	svg = os.path.join(folder, f"{PLACEHOLDER_STEM}.svg")
	_write_svg(svg, title_ar)
	return svg if os.path.exists(svg) else None


def _draw_png(path: str, title_ar: str) -> bool:
	try:
		from PIL import Image, ImageDraw
	except Exception:
		return False
	try:
		display = _shape_arabic(title_ar)
		img = Image.new("RGB", (CANVAS, CANVAS), BRAND_RGB)
		draw = ImageDraw.Draw(img)
		font_title = _load_font(48)
		font_brand = _load_font(72)

		lines = _wrap(display, 22)
		total_h = len(lines) * 60
		y = CANVAS // 2 - total_h // 2 - 40
		for line in lines:
			_centered(draw, line, y, font_title, CANVAS)
			y += 60
		_centered(draw, _shape_arabic("لمسة"), CANVAS // 2 + 90, font_brand, CANVAS)

		img.save(path, "PNG")
		return True
	except Exception:
		return False


def _write_svg(path: str, title_ar: str):
	from xml.sax.saxutils import escape

	title = escape(title_ar)
	svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS}" height="{CANVAS}" viewBox="0 0 {CANVAS} {CANVAS}">
  <rect width="{CANVAS}" height="{CANVAS}" fill="{BRAND_COLOR}"/>
  <text x="50%" y="45%" fill="#ffffff" font-family="sans-serif" font-size="46"
        text-anchor="middle" direction="rtl">{title}</text>
  <text x="50%" y="60%" fill="#ffffff" font-family="sans-serif" font-size="72"
        text-anchor="middle" direction="rtl" font-weight="bold">لمسة</text>
</svg>
"""
	with open(path, "w", encoding="utf-8") as f:
		f.write(svg)


def _shape_arabic(text: str) -> str:
	"""Join and reorder Arabic so a plain bitmap font renders it correctly; a no-op if the shaping
	libraries are absent (the SVG path renders Arabic natively and does not need this)."""
	try:
		import arabic_reshaper
		from bidi.algorithm import get_display

		return get_display(arabic_reshaper.reshape(text))
	except Exception:
		return text


def _load_font(size: int):
	from PIL import ImageFont

	for path in (
		"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
		"/usr/share/fonts/truetype/freefont/FreeSans.ttf",
		"/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
	):
		if os.path.exists(path):
			try:
				return ImageFont.truetype(path, size)
			except Exception:
				continue
	return ImageFont.load_default()


def _wrap(text: str, width: int) -> list[str]:
	words = text.split()
	lines, current = [], ""
	for word in words:
		if len(current) + len(word) + 1 > width and current:
			lines.append(current)
			current = word
		else:
			current = f"{current} {word}".strip()
	if current:
		lines.append(current)
	return lines[:4] or [text[:width]]


def _centered(draw, text: str, y: int, font, width: int):
	try:
		box = draw.textbbox((0, 0), text, font=font)
		w = box[2] - box[0]
	except Exception:
		w = len(text) * 20
	draw.text(((width - w) / 2, y), text, fill="#ffffff", font=font)
