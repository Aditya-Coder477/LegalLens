"""
tests/security/test_rate_limits.py
==================================
Tests rate-limiting and burst protection behavior.
"""

import time
import pytest


class TokenBucketRateLimiter:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def allow_request(self) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


def test_rate_limiter_burst_enforcement():
    limiter = TokenBucketRateLimiter(capacity=5, refill_rate=1.0)
    # First 5 should succeed
    allowed = [limiter.allow_request() for _ in range(5)]
    assert all(allowed)

    # 6th request immediately should fail (burst limit reached)
    assert limiter.allow_request() is False
