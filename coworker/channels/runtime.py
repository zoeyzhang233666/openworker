"""Per-session FIFO and content-free Channel delivery diagnostics (D-193)."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from time import monotonic, time
from typing import Any, Awaitable, Callable, Hashable, Optional


@dataclass
class _Queued:
    payload: Any
    future: asyncio.Future


class MessageDeduplicator:
    def __init__(self, *, ttl_seconds: float = 7 * 60 * 60, max_entries: int = 10_000):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._seen: dict[Hashable, float] = {}

    def accept(self, key: Hashable) -> bool:
        now = monotonic()
        cutoff = now - self.ttl_seconds
        if len(self._seen) >= self.max_entries:
            self._seen = {k: ts for k, ts in self._seen.items() if ts >= cutoff}
        ts = self._seen.get(key)
        if ts is not None and ts >= cutoff:
            return False
        self._seen[key] = now
        return True


class ChannelDeliveryCoordinator:
    """Serialize one engine/session while allowing unrelated sessions to run in parallel."""

    def __init__(
        self,
        runner: Callable[[str, Any], Awaitable[None]],
        *,
        max_concurrency: int = 10,
        turn_timeout: float = 300.0,
    ) -> None:
        self._runner = runner
        self._semaphore = asyncio.Semaphore(max(1, max_concurrency))
        self.turn_timeout = max(1.0, turn_timeout)
        self._queues: dict[str, asyncio.Queue[_Queued]] = {}
        self._workers: dict[str, asyncio.Task] = {}
        self._route_depths: dict[Hashable, int] = defaultdict(int)
        self.last_error: dict[Hashable, str] = {}
        self.last_received_at: dict[Hashable, float] = {}

    async def submit(
        self,
        session_id: str,
        route_key: Hashable,
        payload: Any,
        *,
        wait: bool = True,
    ) -> asyncio.Future:
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        queue = self._queues.setdefault(session_id, asyncio.Queue())
        self._route_depths[route_key] += 1
        self.last_received_at[route_key] = time()
        await queue.put(_Queued((route_key, payload), future))
        worker = self._workers.get(session_id)
        if worker is None or worker.done():
            self._workers[session_id] = asyncio.create_task(
                self._worker(session_id), name=f"channel-fifo:{session_id}"
            )
        if wait:
            await future
        else:
            # Platform callbacks must ACK promptly. Consume the eventual exception here;
            # the content-free error is already retained in ``last_error`` for status UI.
            future.add_done_callback(
                lambda done: None if done.cancelled() else done.exception()
            )
        return future

    async def _worker(self, session_id: str) -> None:
        queue = self._queues[session_id]
        try:
            while not queue.empty():
                queued = await queue.get()
                route_key, payload = queued.payload
                try:
                    async with self._semaphore:
                        await asyncio.wait_for(
                            self._runner(session_id, payload), timeout=self.turn_timeout
                        )
                except asyncio.TimeoutError:
                    self.last_error[route_key] = (
                        f"Agent 处理超过 {int(self.turn_timeout)} 秒，已继续下一条消息"
                    )
                    if not queued.future.done():
                        queued.future.set_exception(TimeoutError(self.last_error[route_key]))
                except Exception as exc:
                    # Status is visible in the settings UI.  Exception messages can contain
                    # prompts, URLs or SDK credentials, so retain only a diagnostic class.
                    self.last_error[route_key] = (
                        f"Agent 处理失败（{type(exc).__name__}）"
                    )
                    if not queued.future.done():
                        queued.future.set_exception(exc)
                else:
                    self.last_error.pop(route_key, None)
                    if not queued.future.done():
                        queued.future.set_result(None)
                finally:
                    self._route_depths[route_key] = max(
                        0, self._route_depths.get(route_key, 1) - 1
                    )
                    queue.task_done()
        finally:
            self._workers.pop(session_id, None)
            if queue.empty():
                self._queues.pop(session_id, None)

    def queue_length(self, route_key: Optional[Hashable] = None) -> int:
        if route_key is not None:
            return self._route_depths.get(route_key, 0)
        return sum(self._route_depths.values())

    def platform_status(self, platform: str) -> dict[str, Any]:
        """Aggregate content-free queue diagnostics for one platform."""
        depths = [
            depth
            for key, depth in self._route_depths.items()
            if isinstance(key, tuple) and key and key[0] == platform
        ]
        received = [
            ts
            for key, ts in self.last_received_at.items()
            if isinstance(key, tuple) and key and key[0] == platform
        ]
        errors = [
            error
            for key, error in self.last_error.items()
            if isinstance(key, tuple) and key and key[0] == platform and error
        ]
        return {
            "queue_length": sum(depths),
            "last_received_at": max(received) if received else None,
            "delivery_last_error": errors[-1] if errors else "",
        }

    async def close(self) -> None:
        workers = list(self._workers.values())
        for worker in workers:
            worker.cancel()
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)
        self._workers.clear()
        self._queues.clear()
