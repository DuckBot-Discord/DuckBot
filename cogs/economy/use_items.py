import asyncio
import contextlib
import os
import random
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from ._base import EconomyBase
from .helper_classes import OwnedItem
from .helper_functions import require_setup

if TYPE_CHECKING:
    from helpers.context import CustomContext
else:
    from discord.ext.commands import Context as CustomContext


# noinspection SqlResolve
class UseItems(EconomyBase):
    async def play_in_voice(self, ctx, file: str):
        user = ctx.author
        voice_channel = user.voice.channel if user.voice else None
        if voice_channel is None:
            return False
        if not voice_channel.permissions_for(user.guild.me).connect:
            return False
        file_name = f"./secrets/audio/{file}"
        if not os.path.exists(file_name):
            return False
        try:
            vc = await voice_channel.connect()
        except discord.errors.ClientException:
            return False
        else:
            try:
                with contextlib.suppress(discord.HTTPException):
                    await ctx.message.add_reaction('🎶')
                file = await self.bot.loop.run_in_executor(None, discord.FFmpegPCMAudio, file_name)
                vc.play(file)
                while vc.is_playing():
                    await asyncio.sleep(1)
                await asyncio.sleep(0.5)
                vc.stop()
            finally:
                await vc.disconnect()
                return True

    @require_setup()
    @commands.command()
    async def use(self, ctx: CustomContext, *, item: OwnedItem):
        """Uses an item in your inventory."""
        async with ctx.wallet:
            used = False
            if item.noises:
                used = await self.play_in_voice(ctx, random.choice(item.noises))
                if used:
                    await item.use(ctx)
                    return await ctx.send(f'🎵 {item.name} 🎵')
            if item.messages:
                await item.use(ctx)
                await ctx.send(random.choice(item.messages))
            if used:
                return
            else:
                raise commands.BadArgument('❗ That item has no use yet.')
