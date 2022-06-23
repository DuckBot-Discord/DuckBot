import inspect
from logging import getLogger
import logging
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    List,
    Literal,
    NamedTuple,
    Optional,
    Tuple,
    TypeVar,
)

from aiohttp import web

if TYPE_CHECKING:
    from bot import DuckBot
else:
    from discord.ext.commands import Bot as DuckBot

__all__: Tuple[str, ...] = ("IPCBase", "route")

FuncT = TypeVar("FuncT", bound="Callable[..., Any]")


class Route(NamedTuple):
    name: str
    method: str
    func: Callable[..., Any]


def route(name: str, *, method: Literal["get", "post", "put", "patch", "delete"]) -> Callable[[FuncT], FuncT]:
    def decorator(func: FuncT) -> FuncT:
        actual = func
        if isinstance(actual, staticmethod):
            actual = actual.__func__
        if not inspect.iscoroutinefunction(actual):
            raise TypeError("Route function must be a coroutine.")

        actual.__ipc_route_name__ = name  # type: ignore
        actual.__ipc_method__ = method  # type: ignore
        return func

    return decorator


class IPCBase:
    @property
    def logger(self):
        return logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def __init__(self, bot: DuckBot):
        self.bot: DuckBot = bot
        self.routes: List[Route] = []

        self.app: web.Application = web.Application()
        self._runner = web.AppRunner(self.app)
        self._webserver: Optional[web.TCPSite] = None

        for attr in map(lambda x: getattr(self, x, None), dir(self)):
            if attr is None:
                continue
            if (name := getattr(attr, "__ipc_route_name__", None)) is not None:
                route: str = attr.__ipc_method__
                self.routes.append(Route(func=attr, name=name, method=route))

        self.app.add_routes([web.route(x.method, x.name, x.func) for x in self.routes])

    async def start(self, *, port: int):
        self.logger.debug('Starting IPC runner.')
        await self._runner.setup()
        self.logger.debug('Starting IPC webserver.')
        self._webserver = web.TCPSite(self._runner, "localhost", port=port)
        await self._webserver.start()

    async def close(self):
        self.logger.debug('Cleaning up after IPCBase.')
        await self._runner.cleanup()
        if self._webserver:
            self.logger.debug('Closing IPC webserver.')
            await self._webserver.stop()
