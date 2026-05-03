from __future__ import annotations

import logging
import re
from typing import Dict

from langdetect import DetectorFactory, detect, detect_langs


logger = logging.getLogger(__name__)
DetectorFactory.seed = 42

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
HINGLISH_HINTS = {
	"hai",
	"haan",
	"nahi",
	"kya",
	"kyun",
	"kaise",
	"please",
	"bhai",
	"sir",
	"madam",
	"mera",
	"meri",
	"mein",
	"main",
	"apna",
	"abhi",
	"thoda",
	"jaldi",
	"call",
	"program",
}


class LanguageDetector:
	"""Lightweight language detection for Hindi, English, and Hinglish."""

	@staticmethod
	def _normalize_text(text: str) -> str:
		return re.sub(r"\s+", " ", (text or "")).strip().lower()

	@classmethod
	def detect_language(cls, text: str) -> str:
		cleaned = cls._normalize_text(text)
		if not cleaned:
			return "english"

		if DEVANAGARI_RE.search(cleaned):
			return "hindi"

		tokens = set(re.findall(r"[a-zA-Z']+", cleaned))
		if tokens & HINGLISH_HINTS and len(tokens) > 1:
			return "hinglish"

		try:
			lang = detect(cleaned)
			if lang == "hi":
				return "hindi"
			if lang == "en":
				# If it looks like mixed English + Hindi romanization, prefer Hinglish.
				if tokens & HINGLISH_HINTS:
					return "hinglish"
				return "english"
			return "hinglish"
		except Exception as exc:  # pragma: no cover - fallback path
			logger.debug("Language detection failed, falling back to Hinglish heuristic: %s", exc)
			return "hinglish" if tokens & HINGLISH_HINTS else "english"

	@classmethod
	def analyze_language(cls, text: str) -> Dict[str, object]:
		cleaned = cls._normalize_text(text)
		language = cls.detect_language(cleaned)

		try:
			confidences = [{"lang": item.lang, "prob": float(item.prob)} for item in detect_langs(cleaned)] if cleaned else []
		except Exception:
			confidences = []

		return {
			"language": language,
			"confidence": confidences,
			"text": text,
		}
