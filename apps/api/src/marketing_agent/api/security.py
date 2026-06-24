"""API-boundary authentication and rate limiting controls."""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from typing import Annotated

from fastapi import Depends, Header, Request
from starlette import status

from marketing_agent.api.errors import ProblemException, request_id
from marketing_agent.config import Settings, get_settings

ACCESS_KEY_HEADER = "X-App-Access-Key"
RATE_LIMIT_TYPE = "https://example.local/errors/rate-limit"
AUTH_TYPE = "https://example.local/errors/authentication"

logger = logging.getLogger(__name__)
SettingsDep = Annotated[Settings, Depends(get_settings)]


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    reset_seconds: int
    retry_after_seconds: int


@dataclass
class _Bucket:
    count: int
    reset_at: float


class InMemoryRateLimiter:
    """Fixed-window limiter for single-process MVP deployments."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}
        self._lock = Lock()

    def check(self, *, key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        now = self._clock()
        with self._lock:
            self._prune_expired(now)
            bucket = self._buckets.get(key)
            if bucket is None or now >= bucket.reset_at:
                bucket = _Bucket(count=0, reset_at=now + window_seconds)
                self._buckets[key] = bucket

            reset_seconds = max(1, int(bucket.reset_at - now))
            if bucket.count >= limit:
                return RateLimitDecision(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_seconds=reset_seconds,
                    retry_after_seconds=reset_seconds,
                )

            bucket.count += 1
            remaining = max(0, limit - bucket.count)
            return RateLimitDecision(
                allowed=True,
                limit=limit,
                remaining=remaining,
                reset_seconds=reset_seconds,
                retry_after_seconds=0,
            )

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()

    def _prune_expired(self, now: float) -> None:
        expired = [key for key, bucket in self._buckets.items() if now >= bucket.reset_at]
        for key in expired:
            del self._buckets[key]


_perception_rate_limiter = InMemoryRateLimiter()


def get_perception_rate_limiter() -> InMemoryRateLimiter:
    return _perception_rate_limiter


AccessKeyHeaderDep = Annotated[str | None, Header(alias=ACCESS_KEY_HEADER)]


def require_access_key(
    request: Request,
    settings: SettingsDep,
    access_key: AccessKeyHeaderDep = None,
) -> None:
    expected = settings.app_access_key
    if not expected:
        if settings.is_production:
            logger.error(
                "access_key_not_configured",
                extra={"request_id": request_id(request)},
            )
            raise ProblemException(
                title="Authentication is not configured",
                detail="APP_ACCESS_KEY must be configured before production API access is enabled.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                type_=AUTH_TYPE,
            )
        return

    if access_key and hmac.compare_digest(access_key, expected):
        return

    logger.warning(
        "access_key_rejected",
        extra={"request_id": request_id(request)},
    )
    raise ProblemException(
        title="Authentication required",
        detail=f"Provide a valid {ACCESS_KEY_HEADER} header.",
        status_code=status.HTTP_401_UNAUTHORIZED,
        type_=AUTH_TYPE,
        headers={"WWW-Authenticate": "ApiKey"},
    )


def enforce_perception_rate_limit(
    request: Request,
    settings: SettingsDep,
    access_key: AccessKeyHeaderDep = None,
) -> None:
    if settings.rate_limit_requests == 0:
        return

    key = _rate_limit_key(request, access_key)
    decision = get_perception_rate_limiter().check(
        key=key,
        limit=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
    request.state.rate_limit_remaining = decision.remaining

    if decision.allowed:
        return

    logger.warning(
        "rate_limit_exceeded",
        extra={"request_id": request_id(request)},
    )
    raise ProblemException(
        title="Rate limit exceeded",
        detail=(
            f"Too many analysis requests. Try again in {decision.retry_after_seconds} seconds."
        ),
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        type_=RATE_LIMIT_TYPE,
        headers={
            "Retry-After": str(decision.retry_after_seconds),
            "X-RateLimit-Limit": str(decision.limit),
            "X-RateLimit-Remaining": str(decision.remaining),
            "X-RateLimit-Reset": str(decision.reset_seconds),
        },
    )


AccessKeyDep = Annotated[None, Depends(require_access_key)]
PerceptionRateLimitDep = Annotated[None, Depends(enforce_perception_rate_limit)]


def _rate_limit_key(request: Request, access_key: str | None) -> str:
    if access_key:
        digest = hashlib.sha256(access_key.encode("utf-8")).hexdigest()
        return f"access-key:{digest}:{request.url.path}"
    client = _client_ip(request)
    return f"ip:{client}:{request.url.path}"


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    if request.client is None:
        return "unknown"
    return request.client.host
