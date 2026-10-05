"""
Twilio webhook signature verification

Twilio signs every webhook request with X-Twilio-Signature (HMAC of the full
URL plus the POST params, keyed by the account auth token). Requests whose
signature doesn't match are rejected, so nobody can forge call or WhatsApp events.
"""

import logging

from fastapi import HTTPException, Request, status
from twilio.request_validator import RequestValidator

from config import get_config

logger = logging.getLogger(__name__)


def _candidate_urls(request: Request) -> list[str]:
    """
    URLs Twilio may have signed. Behind ngrok or Render the app sees an internal
    URL, so the public URL is rebuilt from forwarded headers and the configured base URL.
    """
    config = get_config()
    suffix = request.url.path
    if request.url.query:
        suffix = f"{suffix}?{request.url.query}"

    urls = []
    proto = request.headers.get("x-forwarded-proto")
    host = request.headers.get("x-forwarded-host")
    if proto and host:
        urls.append(f"{proto}://{host}{suffix}")
    if config.twilio_webhook_base_url:
        urls.append(config.twilio_webhook_base_url.rstrip("/") + suffix)
    urls.append(str(request.url))

    return list(dict.fromkeys(urls))


async def verify_twilio_signature(request: Request) -> None:
    """FastAPI dependency: reject webhook requests that were not signed by Twilio."""
    config = get_config()
    if not config.twilio_validate_signatures:
        return

    if not config.twilio_auth_token or config.twilio_auth_token == "sk-test-default":
        logger.error("Twilio auth token not configured; cannot verify webhook signature")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook verification is not configured."
        )

    signature = request.headers.get("x-twilio-signature")
    if not signature:
        logger.warning(f"Rejected webhook without signature: {request.url.path}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if request.method == "POST":
        form = await request.form()
        params = dict(form)
    else:
        params = dict(request.query_params)

    validator = RequestValidator(config.twilio_auth_token)
    if any(validator.validate(url, params, signature) for url in _candidate_urls(request)):
        return

    logger.warning(f"Rejected webhook with invalid Twilio signature: {request.url.path}")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
