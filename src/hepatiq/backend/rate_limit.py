"""In-process per-client rate limiting for the HepatiQ API."""

from __future__ import annotations

import logging
import math
import os
import threading
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

DEFAULT_RATE_LIMIT_REQUESTS = 60
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60.0


@dataclass(frozen=True)
class RateLimitSettings:
    requests: int
    window_seconds: float
    trust_proxy_headers: bool = False

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> RateLimitSettings:
        env = os.environ if environ is None else environ
        return cls(
            requests=_positive_int(env, "HEPATIQ_RATE_LIMIT_REQUESTS", DEFAULT_RATE_LIMIT_REQUESTS),
            window_seconds=_positive_float(
                env, "HEPATIQ_RATE_LIMIT_WINDOW_SECONDS", DEFAULT_RATE_LIMIT_WINDOW_SECONDS
            ),
            trust_proxy_headers=_env_flag(env, "HEPATIQ_TRUST_PROXY_HEADERS", default=False),
        )


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: float = 0.0


class SlidingWindowLimiter:
    """Thread-safe sliding-window limiter keyed by client identity."""

    def __init__(
        self,
        settings: RateLimitSettings,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.settings = settings
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, identity: str) -> RateLimitDecision:
        now = self._clock()
        cutoff = now - self.settings.window_seconds
        with self._lock:
            hits = self._hits.setdefault(identity, deque())
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self.settings.requests:
                retry_after = max(0.0, hits[0] + self.settings.window_seconds - now)
                return RateLimitDecision(allowed=False, retry_after_seconds=retry_after)
            hits.append(now)
            return RateLimitDecision(allowed=True)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def client_identity(request: Request, *, trust_proxy_headers: bool) -> str:
    if trust_proxy_headers:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        forwarded_client = forwarded_for.split(",", 1)[0].strip()
        if forwarded_client:
            return forwarded_client
    if request.client is not None and request.client.host:
        return request.client.host
    return "unknown"


def enforce_rate_limit(request: Request) -> None:
    limiter: SlidingWindowLimiter | None = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        return

    identity = client_identity(request, trust_proxy_headers=limiter.settings.trust_proxy_headers)
    decision = limiter.check(identity)
    if decision.allowed:
        return

    retry_after = max(1, math.ceil(decision.retry_after_seconds))
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many requests; retry later.",
        headers={"Retry-After": str(retry_after)},
    )


def _positive_int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("Invalid %s=%r; using default %s", key, raw, default)
        return default
    if value < 1:
        logger.warning("Invalid %s=%r; using default %s", key, raw, default)
        return default
    return value


def _positive_float(env: Mapping[str, str], key: str, default: float) -> float:
    raw = env.get(key, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        logger.warning("Invalid %s=%r; using default %s", key, raw, default)
        return default
    if value <= 0:
        logger.warning("Invalid %s=%r; using default %s", key, raw, default)
        return default
    return value


def _env_flag(env: Mapping[str, str], key: str, *, default: bool) -> bool:
    raw = env.get(key, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}
