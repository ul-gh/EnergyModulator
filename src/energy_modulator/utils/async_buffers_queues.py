"""Async data structures."""
import asyncio
from typing import Any


class HybridFifoQueue(asyncio.Queue[Any]):
    """FIFO storage queue for bytes datagrams.

    This is intended for coupling sync input and async output.
    Values can only be retrieved once as they are removed when read.

    Overflow of this queue when using sync input is prevented by
    discarding the oldest entry and retrying again.
    """

    def __init__(self, maxsize: int = 10) -> None:
        """Init AsyncReceiveQueue."""
        super().__init__(maxsize)

    def put_nowait(self, item: bytes) -> None:
        """Callback called when a UDP datagram arrives."""
        try:
            super().put_nowait(item)
        # If queue is full, we first discard the oldest entry and try again.
        except asyncio.QueueFull:
            try:
                super().get_nowait()
                super().put_nowait(item)
            # Queue could have been drained by reading in between.
            except asyncio.QueueEmpty:
                try:
                    super().put_nowait(item)
                # If above fails again (new data arrived in between emptying the
                # queue and putting in the newest value), discard more data.
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass
            # Same if more data arrived after dropping the first value.
            except asyncio.QueueFull:
                pass
