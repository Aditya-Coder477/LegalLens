"""
pipeline/core/http_client.py
============================
Shared async HTTP client for the LegalLens pipeline.

Features:
  - Descriptive User-Agent (transparent bot identification)
  - Per-domain token-bucket rate limiting with configurable jitter
  - Tri-state robots.txt compliance checker (ALLOW, DISALLOW, UNKNOWN)
  - Configurable robots unknown policy ("permissive" vs "conservative")
  - Robots audit trail logged to legal-data/logs/robots_audit.jsonl
  - Secret / API key URL redaction
  - Config-driven retry with exponential backoff & jitter
  - Resumable downloads via Range header + .part temp files
  - HTTP metadata capture (status, Content-Type, Last-Modified, ETag)
"""

from __future__ import annotations

import asyncio
import json
import random
import re
import time
import urllib.parse
import urllib.robotparser
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx

from pipeline.core.config import PipelineConfig, get_config
from pipeline.core.logger import get_logger

log = get_logger("http_client")


# ──────────────────────────────────────────────
# Secret Redaction Helper
# ──────────────────────────────────────────────

def redact_secrets_from_url(url: str) -> str:
    """
    Redact API keys or sensitive query parameters from URLs.
    Example: ...?api-key=SECRET123 -> ...?api-key=[REDACTED]
    """
    try:
        parsed = urlparse(url)
        if not parsed.query:
            return url
        params = parse_qs(parsed.query, keep_blank_values=True)
        sensitive_keys = {
            "api-key", "apikey", "api_key", "key", "token",
            "access_token", "secret", "auth", "password"
        }
        modified = False
        for k in list(params.keys()):
            if k.lower() in sensitive_keys:
                params[k] = ["REDACTED"]
                modified = True
        if modified:
            new_query = urlencode(sorted(params.items()), doseq=True)
            return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
        return url
    except Exception:
        return url


# ──────────────────────────────────────────────
# Custom exceptions
# ──────────────────────────────────────────────

class RobotsDecision(str, Enum):
    ALLOW = "ALLOW"
    DISALLOW = "DISALLOW"
    UNKNOWN = "UNKNOWN"


class RobotsBlockedError(Exception):
    """Raised when a URL is disallowed by the source's robots.txt."""
    def __init__(self, url: str, robots_url: str, decision: RobotsDecision = RobotsDecision.DISALLOW):
        self.url = redact_secrets_from_url(url)
        self.robots_url = robots_url
        self.decision = decision
        super().__init__(f"robots.txt ({decision.value}) at {robots_url} disallows: {self.url}")


class DownloadError(Exception):
    """Raised when a download fails after all retries."""
    def __init__(self, url: str, reason: str, http_status: Optional[int] = None):
        self.url = redact_secrets_from_url(url)
        self.reason = reason
        self.http_status = http_status
        super().__init__(f"Download failed for {self.url}: {reason} (HTTP {http_status})")


# ──────────────────────────────────────────────
# robots.txt tri-state cache
# ──────────────────────────────────────────────

class RobotsCache:
    """
    Thread-safe in-memory cache of parsed robots.txt per domain.
    Distinguishes: ALLOW, DISALLOW, and UNKNOWN.
    Logs audit records to legal-data/logs/robots_audit.jsonl.
    """

    def __init__(
        self,
        audit_log_path: str = "legal-data/logs/robots_audit.jsonl",
        unknown_policy: str = "permissive",
    ) -> None:
        self._cache: dict[str, tuple[RobotsDecision, Optional[urllib.robotparser.RobotFileParser]]] = {}
        self._lock = asyncio.Lock()
        self._audit_log_path = Path(audit_log_path)
        self._unknown_policy = unknown_policy.lower()

    def _record_audit(
        self,
        domain: str,
        robots_url: str,
        status: Optional[int],
        decision: RobotsDecision,
        user_agent: str,
        error: Optional[str] = None,
    ) -> None:
        """Append an audit record to robots_audit.jsonl."""
        try:
            self._audit_log_path.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "domain": domain,
                "robots_url": robots_url,
                "fetched_at": datetime.utcnow().isoformat() + "Z",
                "http_status": status,
                "policy_decision": decision.value,
                "user_agent": user_agent,
                "error": error,
            }
            with self._audit_log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as exc:
            log.warning("Could not write robots audit log", error=str(exc))

    async def check_url(self, url: str, user_agent: str = "*") -> RobotsDecision:
        """
        Check robots.txt for a URL and return RobotsDecision (ALLOW, DISALLOW, UNKNOWN).
        Uses httpx with SSL verification tolerance for government domains.
        """
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = f"{domain}/robots.txt"

        async with self._lock:
            if domain in self._cache:
                decision, rp = self._cache[domain]
                if decision == RobotsDecision.UNKNOWN:
                    return RobotsDecision.UNKNOWN
                if rp is not None:
                    allowed = rp.can_fetch(user_agent, url)
                    return RobotsDecision.ALLOW if allowed else RobotsDecision.DISALLOW
                return decision

            # Fetch robots.txt via httpx
            rp = urllib.robotparser.RobotFileParser()
            try:
                async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                    resp = await client.get(robots_url, headers={"User-Agent": user_agent})
                    if resp.status_code in (200, 203):
                        lines = resp.text.splitlines()
                        rp.parse(lines)
                        allowed = rp.can_fetch(user_agent, url)
                        dec = RobotsDecision.ALLOW if allowed else RobotsDecision.DISALLOW
                        self._cache[domain] = (dec, rp)
                        self._record_audit(domain, robots_url, resp.status_code, dec, user_agent)
                        return dec
                    elif resp.status_code in (404, 410):
                        # No robots.txt found -> all allowed
                        self._cache[domain] = (RobotsDecision.ALLOW, None)
                        self._record_audit(domain, robots_url, resp.status_code, RobotsDecision.ALLOW, user_agent)
                        return RobotsDecision.ALLOW
                    elif resp.status_code in (401, 403):
                        # Authentication/Forbidden on robots.txt -> conservative
                        self._cache[domain] = (RobotsDecision.DISALLOW, None)
                        self._record_audit(domain, robots_url, resp.status_code, RobotsDecision.DISALLOW, user_agent)
                        return RobotsDecision.DISALLOW
                    else:
                        # Server error
                        self._cache[domain] = (RobotsDecision.UNKNOWN, None)
                        self._record_audit(domain, robots_url, resp.status_code, RobotsDecision.UNKNOWN, user_agent, error=f"HTTP {resp.status_code}")
                        return RobotsDecision.UNKNOWN
            except Exception as exc:
                log.warning("Could not fetch robots.txt", robots_url=robots_url, error=str(exc))
                self._cache[domain] = (RobotsDecision.UNKNOWN, None)
                self._record_audit(domain, robots_url, None, RobotsDecision.UNKNOWN, user_agent, error=str(exc))
                return RobotsDecision.UNKNOWN

    async def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """
        Evaluate if URL can be fetched under the configured unknown policy.
        """
        dec = await self.check_url(url, user_agent)
        if dec == RobotsDecision.ALLOW:
            return True
        elif dec == RobotsDecision.DISALLOW:
            return False
        else:
            # UNKNOWN
            return (self._unknown_policy == "permissive")


# ──────────────────────────────────────────────
# Per-domain rate limiter (token bucket)
# ──────────────────────────────────────────────

class DomainRateLimiter:
    """
    Enforces minimum delay between requests per domain.
    Adds random jitter to avoid thundering-herd patterns.
    """

    def __init__(
        self,
        delay_seconds: float = 2.5,
        jitter_seconds: float = 1.0,
    ) -> None:
        self._delay = delay_seconds
        self._jitter = jitter_seconds
        self._last_request: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def wait(self, domain: str) -> None:
        """Block until it is safe to make the next request to this domain."""
        async with self._lock:
            now = time.monotonic()
            last = self._last_request.get(domain, 0.0)
            jitter = random.uniform(0, self._jitter)
            wait_time = self._delay + jitter - (now - last)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._last_request[domain] = time.monotonic()


# ──────────────────────────────────────────────
# HTTP Metadata capture
# ──────────────────────────────────────────────

class HttpMetadata:
    """Captured HTTP response metadata for provenance recording."""

    def __init__(self, response: httpx.Response) -> None:
        self.status_code: int = response.status_code
        self.content_type: str = response.headers.get("content-type", "")
        self.content_length: Optional[int] = (
            int(response.headers["content-length"])
            if "content-length" in response.headers else None
        )
        self.etag: Optional[str] = response.headers.get("etag")
        self.last_modified: Optional[str] = response.headers.get("last-modified")
        self.server: Optional[str] = response.headers.get("server")


# ──────────────────────────────────────────────
# Main client
# ──────────────────────────────────────────────

class LegalLensClient:
    """
    Async HTTP client for all pipeline downloads.

    Context manager usage:
        async with LegalLensClient(config) as client:
            resp = await client.get(url)
    """

    def __init__(self, config: Optional[PipelineConfig] = None) -> None:
        self._cfg = config or get_config()
        self._robots = RobotsCache(
            audit_log_path=str(Path(self._cfg.storage.logs_dir) / "robots_audit.jsonl"),
            unknown_policy=self._cfg.collection.robots_unknown_policy,
        )
        self._rate_limiter = DomainRateLimiter(
            delay_seconds=self._cfg.collection.request_delay_seconds,
            jitter_seconds=self._cfg.collection.request_jitter_seconds,
        )
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "LegalLensClient":
        self._client = httpx.AsyncClient(
            headers={"User-Agent": self._cfg.collection.user_agent},
            timeout=httpx.Timeout(self._cfg.collection.timeout_seconds),
            verify=False,  # government SSL certificates in India often miss local CA roots
            follow_redirects=True,
            http2=True,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    def _domain(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc

    async def _check_robots(self, url: str) -> None:
        """Raise RobotsBlockedError if robots.txt disallows this URL."""
        decision = await self._robots.check_url(url, self._cfg.collection.user_agent)
        if decision == RobotsDecision.DISALLOW:
            robots_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}/robots.txt"
            raise RobotsBlockedError(url=url, robots_url=robots_url, decision=decision)
        if decision == RobotsDecision.UNKNOWN and self._cfg.collection.robots_unknown_policy == "conservative":
            robots_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}/robots.txt"
            raise RobotsBlockedError(url=url, robots_url=robots_url, decision=decision)

    async def get(
        self,
        url: str,
        check_robots: bool = True,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Perform a GET request with rate limiting, robots.txt checking, and retry.
        """
        if not self._client:
            raise RuntimeError("Client not started — use `async with LegalLensClient() as client:`")

        if check_robots:
            await self._check_robots(url)

        await self._rate_limiter.wait(self._domain(url))

        return await self._get_with_retry(url, **kwargs)

    async def _get_with_retry(self, url: str, **kwargs: Any) -> httpx.Response:
        """Execute request with configured exponential backoff and jitter."""
        assert self._client is not None
        max_attempts = self._cfg.collection.max_retries
        backoff_factor = self._cfg.collection.backoff_factor

        for attempt in range(1, max_attempts + 1):
            try:
                resp = await self._client.get(url, **kwargs)
                if resp.status_code in (429, 503):
                    retry_after = int(resp.headers.get("retry-after", backoff_factor ** attempt))
                    log.warning("Rate limited / 503", url=redact_secrets_from_url(url), retry_after=retry_after, attempt=attempt)
                    if attempt < max_attempts:
                        await asyncio.sleep(retry_after)
                        continue
                if resp.status_code in (400, 401, 403, 404):
                    # Deterministic failure: DO NOT retry
                    raise DownloadError(url, f"Deterministic client error (HTTP {resp.status_code})", resp.status_code)

                if resp.status_code in (502, 504):
                    if attempt < max_attempts:
                        delay = (backoff_factor ** attempt) + random.uniform(0, 1.0)
                        await asyncio.sleep(delay)
                        continue
                    raise DownloadError(url, f"Server error (HTTP {resp.status_code})", resp.status_code)

                resp.raise_for_status()
                return resp
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt < max_attempts:
                    delay = (backoff_factor ** attempt) + random.uniform(0, 1.0)
                    log.warning("Transient error, retrying", url=redact_secrets_from_url(url), attempt=attempt, error=str(exc))
                    await asyncio.sleep(delay)
                    continue
                raise DownloadError(url, str(exc)) from exc
            except httpx.HTTPStatusError as exc:
                raise DownloadError(url, str(exc), exc.response.status_code) from exc

        raise DownloadError(url, "Max retries exhausted")

    async def download_file(
        self,
        url: str,
        dest: Path,
        check_robots: bool = True,
        resume: bool = True,
    ) -> HttpMetadata:
        """
        Download a file to dest, supporting resumable downloads via Range header.
        Writes to dest.parent / (dest.name + '.part') atomically.
        """
        if not self._client:
            raise RuntimeError("Client not started")

        if check_robots:
            await self._check_robots(url)

        dest.parent.mkdir(parents=True, exist_ok=True)
        part_path = dest.parent / (dest.name + ".part")

        headers: dict[str, str] = {}
        resume_pos = 0
        if resume and part_path.exists():
            resume_pos = part_path.stat().st_size
            if resume_pos > 0:
                headers["Range"] = f"bytes={resume_pos}-"
                log.debug("Resuming download", url=redact_secrets_from_url(url), from_byte=resume_pos)

        max_attempts = self._cfg.collection.max_retries + 1
        backoff_factor = self._cfg.collection.backoff_factor

        for attempt in range(1, max_attempts + 1):
            await self._rate_limiter.wait(self._domain(url))
            try:
                async with self._client.stream("GET", url, headers=headers) as resp:
                    if resp.status_code == 416:
                        # Range not satisfiable = file already complete
                        part_path.replace(dest)
                        return HttpMetadata(resp)

                    if resp.status_code == 429:
                        if attempt < max_attempts:
                            retry_after = float(resp.headers.get("retry-after", 2.0))
                            log.warning("Rate limit hit during download, backing off", url=redact_secrets_from_url(url), retry_after=retry_after)
                            await asyncio.sleep(retry_after)
                            continue
                        raise DownloadError(url, "Rate limit exceeded (HTTP 429)", 429)

                    if resp.status_code in (400, 401, 403, 404):
                        raise DownloadError(url, f"Client error (HTTP {resp.status_code})", resp.status_code)

                    if resp.status_code in (502, 503, 504):
                        if attempt < max_attempts:
                            delay = (backoff_factor ** attempt) + random.uniform(0, 1.0)
                            log.warning("Server error during download, retrying", url=redact_secrets_from_url(url), attempt=attempt, status=resp.status_code)
                            await asyncio.sleep(delay)
                            continue
                        raise DownloadError(url, f"Server error (HTTP {resp.status_code})", resp.status_code)

                    if resp.status_code == 200 and resume_pos > 0:
                        # Server doesn't support Range — restart
                        resume_pos = 0

                    resp.raise_for_status()
                    meta = HttpMetadata(resp)
                    mode = "ab" if resume_pos > 0 else "wb"
                    with part_path.open(mode) as f:
                        async for chunk in resp.aiter_bytes(chunk_size=1024 * 64):
                            f.write(chunk)

                part_path.replace(dest)
                return meta
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt < max_attempts:
                    delay = (backoff_factor ** attempt) + random.uniform(0, 1.0)
                    log.warning("Network error during download, retrying", url=redact_secrets_from_url(url), attempt=attempt, error=str(exc))
                    await asyncio.sleep(delay)
                    continue
                raise DownloadError(url, str(exc)) from exc
            except httpx.HTTPStatusError as exc:
                raise DownloadError(url, str(exc), exc.response.status_code) from exc

        raise DownloadError(url, "Max download retries exhausted")
