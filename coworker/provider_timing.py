"""Content-free, call-local timing. Never passed through model settings or HTTP bodies.

The engine installs the scope inside its producer thread. Late output after Stop is
ignored once frozen. HTTP hooks deliberately never inspect URLs, headers or bodies.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from threading import Lock
from time import perf_counter


_active: ContextVar[CallTiming | None] = ContextVar("provider_timing", default=None)
_MARKS = frozenset({
    "provider_start_ms", "upstream_first_content_ms", "upstream_first_reasoning_ms",
    "provider_first_text_ms", "engine_first_text_ms",
})


class CallTiming:
    def __init__(self, *, offset_ms: float = 0, clock=perf_counter):
        self._clock = clock
        self._start = clock()
        self._lock = Lock()
        self._closed = False
        self._data = {"offset_ms": offset_ms, "status": "running", "http_requests": [],
                      "http_request_count": 0}

    def _elapsed(self):
        return round(max(0, (self._clock() - self._start) * 1000), 3)

    def mark(self, name: str):
        if name not in _MARKS:
            return
        with self._lock:
            if not self._closed and name not in self._data:
                self._data[name] = self._elapsed()

    def http_request(self):
        with self._lock:
            if not self._closed:
                self._data["http_request_count"] += 1
                if self._data["http_request_count"] <= 32:
                    self._data["http_requests"].append({"request_ms": self._elapsed()})

    def http_headers(self):
        with self._lock:
            if (not self._closed and self._data["http_requests"]
                    and self._data["http_request_count"] <= 32):
                self._data["http_requests"][-1].setdefault("headers_ms", self._elapsed())

    def finish(self, status: str):
        with self._lock:
            if not self._closed:
                self._data["elapsed_ms"] = self._elapsed()
                self._data["status"] = status if status in {"completed", "failed", "interrupted"} else "failed"
                self._closed = True
            return {**self._data, "http_requests": [dict(r) for r in self._data["http_requests"]]}


@contextmanager
def timing_scope(timing: CallTiming):
    token = _active.set(timing)
    try:
        yield
    finally:
        _active.reset(token)


def mark_provider_time(name: str):
    timing = _active.get()
    if timing is not None:
        timing.mark(name)


def on_http_request(_request):
    timing = _active.get()
    if timing is not None:
        timing.http_request()


def on_http_response(_response):
    timing = _active.get()
    if timing is not None:
        timing.http_headers()
