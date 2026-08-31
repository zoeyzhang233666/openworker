"""The small public Channel adapter interface (D-193)."""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

from .models import ChannelCapabilities, ChannelStatus, OutboundEnvelope


@runtime_checkable
class ChannelAdapter(Protocol):
    platform: str
    account_id: str
    capabilities: ChannelCapabilities

    async def start(self) -> bool: ...

    async def stop(self) -> None: ...

    def status(self) -> ChannelStatus: ...

    async def send(
        self,
        envelope: OutboundEnvelope | str,
        text: Optional[str] = None,
        *,
        thread_id: Optional[str] = None,
    ) -> Any: ...
