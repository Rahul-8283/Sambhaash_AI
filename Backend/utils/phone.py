"""
Phone number normalization

Converts the numbers we receive from CSV/JSON uploads, the API, and WhatsApp
into E.164 format (e.g. "+917989683240") so they can be dialed by Twilio and
matched against stored leads.
"""

import re

from config import get_config

E164_MIN_DIGITS = 8
E164_MAX_DIGITS = 15


def normalize_phone(raw: str, default_country_code: str | None = None) -> str:
    """
    Return the phone number in E.164 format.

    Accepts:
      "+917989683240", "917989683240", "00917989683240"  -> "+917989683240"
      "7989683240"  (10 digits, no country code)          -> default country code applied
      "07989683240" (national format with leading 0)      -> default country code applied
      "whatsapp:+917989683240"                            -> "+917989683240"

    Raises ValueError if the result cannot be a valid E.164 number.
    """
    if raw is None:
        raise ValueError("Phone is required")

    text = str(raw).strip()
    if text.lower().startswith("whatsapp:"):
        text = text[len("whatsapp:"):].strip()

    cc = (default_country_code or get_config().default_country_code).lstrip("+")
    has_plus = text.startswith("+")
    digits = re.sub(r"\D", "", text)

    if not digits:
        raise ValueError(f"Phone has no digits: {raw!r}")

    if has_plus:
        e164 = "+" + digits
    elif text.startswith("00"):
        e164 = "+" + digits[2:]
    elif len(digits) == 10:
        e164 = "+" + cc + digits
    elif len(digits) == 11 and digits.startswith("0"):
        e164 = "+" + cc + digits[1:]
    else:
        # Already has the country code without the "+", e.g. "917989683240"
        e164 = "+" + digits

    number_digits = len(e164) - 1
    if not (E164_MIN_DIGITS <= number_digits <= E164_MAX_DIGITS):
        raise ValueError(f"Phone {raw!r} is not a valid international number")

    return e164
