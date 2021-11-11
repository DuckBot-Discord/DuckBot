from __future__ import annotations

import random
import asyncio
from collections import deque
from copy import copy
from typing import (AsyncIterator, Generic, Iterable, Iterator, List, Optional, Type, TypeVar, Union,)

from pomice import Track

__all__ = (
    "Queue",
    "QueueEmpty",
    "QueueException",
    "QueueFull",
    "WaitQueue",
)


class QueueException(Exception):
    """Base WaveLink Queue exception."""
    pass


class QueueFull(QueueException):
    """Exception raised when attempting to add to a full Queue."""
    pass


class QueueEmpty(QueueException):
    """Exception raised when attempting to retrieve from an empty Queue."""
    pass


class Queue(Iterable[Track]):
    __slots__ = ("max_size", "_queue", "_overflow")

    def __init__(
        self,
        max_size: Optional[int] = None,
        *,
        overflow: bool = True,
        queue_cls=deque,
    ):
        self.max_size: Optional[int] = max_size
        self._queue = queue_cls()  # type: ignore
        self._overflow: bool = overflow

    def __str__(self) -> str:
        """String showing all pomice.Track objects appearing as a list."""
        return str(list(f"'{t}'" for t in self))

    def __repr__(self) -> str:
        """Official representation with max_size and member count."""
        return (
            f"<{self.__class__.__name__} max_size={self.max_size} members={self.count}>"
        )

    def __bool__(self) -> bool:
        """Treats the queue as a bool, with it evaluating True when it contains members."""
        return bool(self.count)

    def __call__(self, item: Track) -> None:
        """Allows the queue instance to be called directly in order to add a member."""
        self.put(item)

    def __len__(self) -> int:
        """Return the number of members in the queue."""
        return self.count

    def __getitem__(self, index: int) -> Track:
        """Returns a member at the given position.
        Does not remove item from queue.
        """
        if not isinstance(index, int):
            raise ValueError("'int' type required.'")

        return self._queue[index]

    def __setitem__(self, index: int, item: Track):
        """Inserts an item at given position."""
        if not isinstance(index, int):
            raise ValueError("'int' type required.'")

        self.put_at_index(index, item)

    def __delitem__(self, index: int) -> None:
        """Delete item at given position."""
        self._queue.__delitem__(index)

    def __iter__(self) -> Iterator[Track]:
        """Iterate over members in the queue.
        Does not remove items when iterating.
        """
        return self._queue.__iter__()

    def __reversed__(self) -> Iterator[Track]:
        """Iterate over members in reverse order."""
        return self._queue.__reversed__()

    def __contains__(self, item: Track) -> bool:
        """Check if an item is a member of the queue."""
        return item in self._queue

    def __add__(self, other: Iterable[Track]) -> Queue:
        """Return a new queue containing all members.
        The new queue will have the same max_size as the original.
        """
        if not isinstance(other, Iterable):
            raise TypeError(f"Adding with the '{type(other)}' type is not supported.")

        new_queue = self.copy()
        new_queue.extend(other)
        return new_queue

    def __iadd__(self, other: Union[Iterable[Track], Track]) -> Queue:
        """Add items to queue."""
        if isinstance(other, Track):
            self.put(other)
            return self

        if isinstance(other, Iterable):
            self.extend(other)
            return self

        raise TypeError(f"Adding '{type(other)}' type to the queue is not supported.")

    def _get(self) -> Track:
        return self._queue.popleft()

    def _drop(self) -> Track:
        return self._queue.pop()

    def _index(self, item: Track) -> int:
        return self._queue.index(item)

    def _put(self, item: Track) -> None:
        self._queue.append(item)

    def _insert(self, index: int, item: Track) -> None:
        self._queue.insert(index, item)

    @staticmethod
    def _check_track(item: Track) -> Track:
        if not isinstance(item, Track):
            raise TypeError("Only pomice.Track objects are supported.")

        return item

    @classmethod
    def _check_track_container(cls, iterable: Iterable) -> List[Track]:
        iterable = list(iterable)
        for item in iterable:
            cls._check_track(item)

        return iterable

    @property
    def count(self) -> int:
        """Returns queue member count."""
        return len(self._queue)

    @property
    def is_empty(self) -> bool:
        """Returns True if queue has no members."""
        return not bool(self.count)

    @property
    def is_full(self) -> bool:
        """Returns True if queue item count has reached max_size."""
        return False if self.max_size is None else self.count >= self.max_size

    def get(self) -> Track:
        """Return next immediately available item in queue if any.
        Raises QueueEmpty if no items in queue.
        """
        if self.is_empty:
            raise QueueEmpty("No items in the queue.")

        return self._get()

    def pop(self) -> Track:
        """Return item from the right end side of the queue.
        Raises QueueEmpty if no items in queue.
        """
        if self.is_empty:
            raise QueueEmpty("No items in the queue.")

        return self._queue.pop()

    def find_position(self, item: Track) -> int:
        """Find the position a given item within the queue.
        Raises ValueError if item is not in queue.
        """
        return self._index(self._check_track(item))

    def put(self, item: Track) -> None:
        """Put the given item into the back of the queue."""
        if self.is_full:
            if not self._overflow:
                raise QueueFull(f"Queue max_size of {self.max_size} has been reached.")

            self._drop()

        return self._put(self._check_track(item))

    def put_at_index(self, index: int, item: Track) -> None:
        """Put the given item into the queue at the specified index."""
        if self.is_full:
            if not self._overflow:
                raise QueueFull(f"Queue max_size of {self.max_size} has been reached.")

            self._drop()

        return self._insert(index, self._check_track(item))

    def put_at_front(self, item: Track) -> None:
        """Put the given item into the front of the queue."""
        return self.put_at_index(0, item)

    def extend(self, iterable: Iterable[Track], *, atomic: bool = True) -> None:
        """
        Add the members of the given iterable to the end of the queue.
        If atomic is set to True, no tracks will be added upon any exceptions.
        If atomic is set to False, as many tracks will be added as possible.
        When overflow is enabled for the queue, `atomic=True` won't prevent dropped items.
        """
        if atomic:
            iterable = self._check_track_container(iterable)

            if not self._overflow and self.max_size is not None:
                new_len = len(iterable)

                if (new_len + self.count) > self.max_size:
                    raise QueueFull(
                        f"Queue has {self.count}/{self.max_size} items, "
                        f"cannot add {new_len} more."
                    )

        for item in iterable:
            self.put(item)

    def copy(self) -> Queue:
        """Create a copy of the current queue including it's members."""
        new_queue = self.__class__(max_size=self.max_size)
        new_queue._queue = copy(self._queue)

        return new_queue

    def clear(self) -> None:
        """Remove all items from the queue."""
        self._queue.clear()


class WaitQueue(Queue):
    """Queue for pomice.Track objects designed for Players that allow waiting for new items with `get_wait`.
    .. note::
        WaitQueue is the default Player queue.
    Attributes
    ----------
    history: :class:`~Queue`
        A history Queue of previously played tracks.
    """

    __slots__ = ("history", "_waiters", "_finished")

    def __init__(
        self,
        max_size: Optional[int] = None,
        history_max_size: Optional[int] = None,
        history_cls=Queue,
    ):
        super().__init__(max_size, overflow=False)  # type: ignore
        self.history = history_cls(history_max_size)

        self._waiters = deque()
        self._finished = asyncio.Event()
        self._finished.set()

    async def __aiter__(self) -> AsyncIterator[Track]:
        """Pops members as it iterates the queue, waiting for new members when exhausted.
        Removes items when iterating.
        """
        while True:
            yield await self.get_wait()

    def _get(self) -> Track:
        item = super()._get()
        self.history.put(item)

        return item

    def _put(self, item: Track) -> None:
        super()._put(item)
        self._wakeup_next()

    def _insert(self, index: int, item: Track) -> None:
        super()._queue.insert(index, item)
        self._wakeup_next()

    def _wakeup_next(self) -> None:
        while self._waiters:
            waiter = self._waiters.popleft()
            if not waiter.done():
                waiter.set_result(None)
                break

    async def get_wait(self) -> Track:
        """|coro|
        Return the next item in queue once available.
        .. note::
            This will wait until an item is available to be retrieved.
        """
        while self.is_empty:
            loop = asyncio.get_event_loop()
            waiter = loop.create_future()

            self._waiters.append(waiter)

            try:
                await waiter
            except:  # noqa
                waiter.cancel()

                try:
                    self._waiters.remove(waiter)
                except ValueError:  # pragma: no branch
                    pass

                if not self.is_empty and not waiter.cancelled():  # pragma: no cover
                    # something went wrong with this waiter, move on to next
                    self._wakeup_next()
                raise

        return self.get()

    async def put_wait(self, item: Track) -> None:
        """|coro|
        Put an item into the queue using await.
        """
        self._put(item)
        await asyncio.sleep(0)

    def shuffle(self) -> None:
        """
        Randomizes the current order of tracks in the queue
        """
        random.shuffle(super()._queue)

    def reset(self) -> None:
        """Clears the state of all queues."""
        self.clear()
        self.history.clear()

        for waiter in self._waiters:
            waiter.cancel()

        self._waiters.clear()