"""Async data structures."""
import asyncio


class HybridDoubleBuffer:
    """Double nuffering for bytes datagrams.

    This is intended for coupling sync input and async output
    and allows repeatedly retrieving the last input value.
    """
    datagram_size: int

    def __init__(self) -> None:
        """Init AsyncReceiveBuffer."""
        self.data_ready: asyncio.Future[None] = asyncio.Future()
        self.recv_buffer = bytearray()
        self.recv_buffer_lock = asyncio.Lock()

    async def get(self) -> bytes:
        """Get the latest datagram from the double buffer as soon as available."""
        async with self.recv_buffer_lock:
            if not self.data_ready.done():
                await self.data_ready
            return self.recv_buffer[-self.datagram_size:]

    def put_nowait(self, data: bytes) -> None:
        """Put datagram into the double buffer.

        When buffer is locked (task waiting for data), data is appended
        at the end and buffer size is trimmed when the next datagram arrives.
        """
        self.datagram_size = len(data)
        if self.recv_buffer_lock.locked():
            self.recv_buffer.extend(data)
        else:
            self.recv_buffer[:] = data
        if not self.data_ready.done():
            self.data_ready.set_result(None)


class HybridFifoQueue:
    """FIFO storage queue for bytes datagrams.

    This is intended for coupling sync input and async output.
    Values can only be retrieved once as they are removed when read.

    Overflow of this queue when using sync input is prevented by
    discarding the oldest entry and retrying again.
    """

    def __init__(self, maxsize: int = 10) -> None:
        """Init AsyncReceiveQueue."""
        self._recv_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize)

    async def get(self) -> bytes:
        """Get the latest datagram from the queue as soon as available."""
        return await self._recv_queue.get()

    def put_nowait(self, data: bytes) -> None:
        """Callback called when a UDP datagram arrives."""
        try:
            self._recv_queue.put_nowait(data)
        # If queue is full, we first discard the oldest entry and try again.
        except asyncio.QueueFull:
            try:
                self._recv_queue.get_nowait()
                self._recv_queue.put_nowait(data)
            # Queue could have been drained by reading in between.
            except asyncio.QueueEmpty:
                try:
                    self._recv_queue.put_nowait(data)
                # If above fails again (new data arrived in between emptying the
                # queue and putting in the newest value), discard more data.
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass
            # Same if more data arrived after dropping the first value.
            except asyncio.QueueFull:
                pass
