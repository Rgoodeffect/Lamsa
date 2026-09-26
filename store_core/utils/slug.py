"""URL slugs that keep Arabic letters (Arabic URLs are fine for SEO and readable for customers)."""

import re
import unicodedata

_ARABIC_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_NOT_ALLOWED = re.compile(r"[^\w؀-ۿ]+", re.UNICODE)


def slugify(text: str | None, max_length: int = 80) -> str:
	if not text:
		return ""
	value = unicodedata.normalize("NFKC", str(text)).strip().lower()
	value = _ARABIC_DIACRITICS.sub("", value)
	value = _NOT_ALLOWED.sub("-", value).replace("_", "-")
	value = re.sub(r"-{2,}", "-", value).strip("-")
	return value[:max_length].rstrip("-")
