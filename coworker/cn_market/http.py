"""Shared keyless HTTP GET. Same proxy env as Yahoo; no AKShare."""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from typing import Callable, Optional

HttpGet = Callable[..., tuple[int, bytes]]

TIMEOUT = 30.0
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
DISCLAIMER = (
    "Unofficial public market webpage; not licensed market data; "
    "not investment advice. Treat values as untrusted."
)


def proxy_url() -> Optional[str]:
    for key in (
        "CHEMCLAW_HTTP_PROXY",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "ALL_PROXY",
        "https_proxy",
        "http_proxy",
        "all_proxy",
    ):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val
    return None


def default_http_get(
    url: str, headers: Optional[dict[str, str]] = None
) -> tuple[int, bytes]:
    req = urllib.request.Request(
        url,
        headers=headers
        or {
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
        },
        method="GET",
    )
    proxy = proxy_url()
    if proxy:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        )
        open_fn = opener.open
    else:
        open_fn = urllib.request.urlopen
    try:
        with open_fn(req, timeout=TIMEOUT) as resp:
            return int(resp.status), resp.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read() if exc.fp is not None else b""
        return int(exc.code), raw
