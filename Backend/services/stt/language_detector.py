from __future__ import annotations

import logging
import re
from typing import Dict

from langdetect import DetectorFactory, detect, detect_langs


logger = logging.getLogger(__name__)
DetectorFactory.seed = 42

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

# Indic scripts are identified by Unicode range; the statistical detector is
# unreliable on these, so script comes first.
INDIC_SCRIPT_RANGES = {
	"bn": re.compile(r"[\u0980-\u09FF]"),  # Bengali
	"pa": re.compile(r"[\u0A00-\u0A7F]"),  # Gurmukhi (Punjabi)
	"gu": re.compile(r"[\u0A80-\u0AFF]"),  # Gujarati
	"or": re.compile(r"[\u0B00-\u0B7F]"),  # Odia
	"ta": re.compile(r"[\u0B80-\u0BFF]"),  # Tamil
	"te": re.compile(r"[\u0C00-\u0C7F]"),  # Telugu
	"kn": re.compile(r"[\u0C80-\u0CFF]"),  # Kannada
	"ml": re.compile(r"[\u0D00-\u0D7F]"),  # Malayalam
}

# Language codes the rest of the pipeline (TTS, templates) can use
SUPPORTED_CODES = {"en", "hi", "mr", "bn", "pa", "gu", "or", "ta", "te", "kn", "ml"}

HINGLISH_HINTS = {
	"hai",
	"haan",
	"nahi",
	"kya",
	"kyun",
	"kaise",
	"bhai",
	"mera",
	"meri",
	"mein",
	"main",
	"apna",
	"abhi",
	"thoda",
	"jaldi",
}


class LanguageDetector:
	"""
	Detects the language of a transcript.

	Returns a language code ("en", "hi", "ta", "te", ...) for native-script speech,
	"hinglish" for romanized Hindi mixed with English, and "en" otherwise.
	"""

	@staticmethod
	def _normalize_text(text: str) -> str:
		return re.sub(r"\s+", " ", (text or "")).strip().lower()

	@staticmethod
	def _devanagari_language(cleaned: str) -> str:
		"""Devanagari is shared by Hindi and Marathi; the statistical detector tells them apart."""
		try:
			return "mr" if detect(cleaned) == "mr" else "hi"
		except Exception:
			return "hi"

	@classmethod
	def detect_language(cls, text: str) -> str:
		cleaned = cls._normalize_text(text)
		if not cleaned:
			return "en"

		# 1. Native script wins: count letters in each script, take the dominant one
		script_counts = {code: len(pattern.findall(cleaned)) for code, pattern in INDIC_SCRIPT_RANGES.items()}
		devanagari_count = len(DEVANAGARI_RE.findall(cleaned))
		if devanagari_count or any(script_counts.values()):
			if devanagari_count >= max(script_counts.values()):
				return cls._devanagari_language(cleaned)
			return max(script_counts, key=script_counts.get)

		# 2. Romanized Latin script
		tokens = set(re.findall(r"[a-zA-Z']+", cleaned))
		if tokens & HINGLISH_HINTS and len(tokens) > 1:
			return "hinglish"

		try:
			lang = detect(cleaned)
		except Exception as exc:  # pragma: no cover - fallback path
			logger.debug("Language detection failed, using heuristics: %s", exc)
			return "hinglish" if tokens & HINGLISH_HINTS else "en"

		if lang == "hi":
			return "hi"
		if lang == "en":
			return "hinglish" if tokens & HINGLISH_HINTS else "en"
		# Any other Latin-script language is not one we speak; treat it as English
		logger.info("Detected unsupported language %r for Latin-script text; using English", lang)
		return "en"

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
