"""
Fixed-window rate limiting per client IP, with counters kept in Redis so every
API process shares them.

If Redis is unavailable the request is allowed and a warning is logged. A broken
limiter should not block the public lead form.
"""

import logging

import redis.asyncio as aioredis
from fastapi import HTTPException, Request, status

from config import get_config

logger = logging.getLogger(__name__)

_redis_client = None


def _redis():
	global _redis_client
	if _redis_client is None:
		_redis_client = aioredis.from_url(get_config().redis_url, decode_responses=True)
	return _redis_client


def client_ip(request: Request) -> str:
	"""
	Client address. Behind a proxy (Render, ngrok) the proxy appends the real client
	to X-Forwarded-For, so the last entry is the one to trust.
	"""
	forwarded = request.headers.get("x-forwarded-for")
	if forwarded:
		return forwarded.split(",")[-1].strip()
	return request.client.host if request.client else "unknown"


def rate_limit(scope: str, limit: int, window_seconds: int):
	"""FastAPI dependency: allow at most `limit` requests per `window_seconds` per IP."""

	async def dependency(request: Request) -> None:
		key = f"ratelimit:{scope}:{client_ip(request)}"
		try:
			redis = _redis()
			# nx=True sets the expiry only when the key is created, so a crash between
			# the two commands cannot leave a counter that never expires
			await redis.set(key, 0, ex=window_seconds, nx=True)
			count = await redis.incr(key)
		except Exception as exc:
			logger.warning(f"[RATELIMIT] Redis unavailable, allowing request: {exc}")
			return

		if count > limit:
			logger.warning(f"[RATELIMIT] {scope} limit hit for {client_ip(request)}")
			raise HTTPException(
				status_code=status.HTTP_429_TOO_MANY_REQUESTS,
				detail="Too many requests. Please try again later.",
				headers={"Retry-After": str(window_seconds)},
			)

	return dependency
