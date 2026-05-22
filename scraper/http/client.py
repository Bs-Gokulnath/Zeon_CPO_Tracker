"""
Resilient async HTTP client.

Wraps httpx.AsyncClient with:
  - Per-endpoint timeout control (markers API needs 90s read timeout)
  - Tenacity exponential-backoff retry on transient failures
  - Structured log entry/exit per request
  - Optional proxy support from settings

Usage:
    async with AsyncHTTPClient(read_timeout=90) as client:
        data = await client.post_json(url, payload)
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from scraper.config import settings
from scraper.utils.logger import get_scrape_logger

log = get_scrape_logger("http.client")

# HTTP status codes that warrant a retry (server-side transient errors)
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

# Default browser-like headers sent with every request
_DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


class NonRetryableHTTPError(Exception):
    """
    Raised for HTTP 4xx responses (except 429).
    These indicate a client-side problem that retrying will not fix.
    """

    def __init__(self, status_code: int, url: str) -> None:
        super().__init__(f"HTTP {status_code} for {url} — not retrying")
        self.status_code = status_code
        self.url = url


class AsyncHTTPClient:
    """
    Async HTTP client with retry logic. Intended as an async context manager.

    Parameters
    ----------
    read_timeout:
        Seconds to wait for a response body. The markers API returns ~2.5 MB
        and takes 56–63 s — set this to at least 90 for that endpoint.
    max_retries:
        Maximum retry attempts (uses exponential backoff: 5s → 10s → 20s...).
    extra_headers:
        Additional headers merged on top of _DEFAULT_HEADERS.
    """

    def __init__(
        self,
        *,
        read_timeout: int | None = None,
        max_retries: int | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self._read_timeout = read_timeout or settings.scraper_request_timeout
        self._max_retries = max_retries or settings.scraper_max_retries
        self._headers = {**_DEFAULT_HEADERS, **(extra_headers or {})}
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AsyncHTTPClient":
        timeout = httpx.Timeout(
            connect=10.0,
            read=float(self._read_timeout),
            write=10.0,
            pool=5.0,
        )
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers=self._headers,
            proxy=settings.proxy_config,
            http2=True,
            follow_redirects=True,
        )
        log.debug(
            "HTTP client opened (read_timeout={t}s, max_retries={r})",
            t=self._read_timeout,
            r=self._max_retries,
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()
            log.debug("HTTP client closed")

    # ── Public interface ──────────────────────────────────────────────────────

    async def post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        POST *payload* as JSON to *url*, returning the parsed JSON body.
        Retries on transient failures with exponential backoff.
        """
        assert self._client is not None, "Client must be used inside an async context manager"
        return await self._with_retry("POST", url, payload)

    async def get(
        self,
        url: str,
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """
        GET *url*, returning the raw httpx.Response.
        Retries on transient failures.
        """
        assert self._client is not None, "Client must be used inside an async context manager"
        return await self._with_retry("GET", url, None, extra_headers)

    # ── Internal retry plumbing ───────────────────────────────────────────────

    async def _with_retry(
        self,
        method: str,
        url: str,
        payload: dict | None,
        extra_headers: dict | None = None,
    ) -> Any:
        """Run the request through tenacity retry logic."""
        attempt_number = 0

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._max_retries),
                wait=wait_exponential(multiplier=2, min=5, max=60),
                retry=retry_if_exception_type(
                    (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)
                ),
                reraise=True,
            ):
                with attempt:
                    attempt_number = attempt.retry_state.attempt_number
                    if attempt_number > 1:
                        log.warning(
                            "Retry attempt {n}/{max} for {method} {url}",
                            n=attempt_number,
                            max=self._max_retries,
                            method=method,
                            url=url,
                        )
                    return await self._dispatch(method, url, payload, extra_headers)

        except RetryError as exc:
            log.error(
                "All {n} retry attempts exhausted for {method} {url}",
                n=self._max_retries,
                method=method,
                url=url,
            )
            raise

    async def _dispatch(
        self,
        method: str,
        url: str,
        payload: dict | None,
        extra_headers: dict | None,
    ) -> Any:
        """Single (non-retried) HTTP dispatch."""
        assert self._client is not None
        headers = extra_headers or {}

        if method == "POST":
            log.debug("POST {url} payload_keys={keys}", url=url, keys=list((payload or {}).keys()))
            response = await self._client.post(url, json=payload, headers=headers)
        else:
            log.debug("GET {url}", url=url)
            response = await self._client.get(url, headers=headers)

        self._raise_for_status(response)
        log.debug(
            "{method} {url} → HTTP {code} ({size} bytes)",
            method=method,
            url=url,
            code=response.status_code,
            size=len(response.content),
        )

        if method == "POST":
            return response.json()
        return response

    def _raise_for_status(self, response: httpx.Response) -> None:
        """
        Classify HTTP errors:
          - 5xx + 429 → retryable (raise HTTPStatusError)
          - 4xx (except 429) → non-retryable (raise NonRetryableHTTPError)
        """
        if response.status_code in _RETRYABLE_STATUS:
            raise httpx.HTTPStatusError(
                f"Retryable status {response.status_code}",
                request=response.request,
                response=response,
            )
        if response.status_code >= 400:
            raise NonRetryableHTTPError(response.status_code, str(response.url))
