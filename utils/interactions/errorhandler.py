import asyncio
from types import TracebackType
from typing import Optional, Type, Tuple

import discord
from utils.bases.errors import SilentCommandError

__all__: Tuple[str, ...] = ("HandleHTTPException",)


class HandleHTTPException:
    __slots__: Tuple[str, ...] = ('webhook', 'message')

    def __init__(self, webhook: discord.Webhook, title: str = None):
        self.webhook: discord.Webhook = webhook
        self.message: str = title

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]] = None,
        exc_val: Optional[BaseException] = None,
        exc_tb: Optional[TracebackType] = None,
    ) -> bool:
        if exc_val is not None and isinstance(exc_val, discord.HTTPException) and exc_type:
            embed = discord.Embed(
                title=self.message or 'An unexpected error occurred!',
                description=f'{exc_type.__name__}: {exc_val.text}',
                colour=discord.Colour.red(),
            )

            try:
                asyncio.get_event_loop().create_task(self.webhook.send(embed=embed, ephemeral=True))
            except discord.HTTPException:
                pass
            raise SilentCommandError

        return False

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]] = None,
        exc_val: Optional[BaseException] = None,
        exc_tb: Optional[TracebackType] = None,
    ) -> bool:
        if exc_val is not None and isinstance(exc_val, discord.HTTPException) and exc_type:
            embed = discord.Embed(
                title=self.message or 'An unexpected error occurred!',
                description=f'{exc_type.__name__}: {exc_val.text}',
                colour=discord.Colour.red(),
            )

            try:
                asyncio.get_event_loop().create_task(self.webhook.send(embed=embed, ephemeral=True))
            except discord.HTTPException:
                pass
            raise SilentCommandError

        return False
