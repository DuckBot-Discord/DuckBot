import discord
from discord.ext import commands
from bot import DuckBot
from utils import (
    DuckCog,
    DuckContext,
    cache,
    Strategy
)

from typing import (
    Optional,
    Union,
)

class CommandConfig(DuckCog):
    """
    handles configuration of commands and channels.
    """
    def __init__(self, bot: DuckBot):
        super().__init__(bot)

    async def bot_check_once(self, ctx: DuckContext) -> bool:
        if await ctx.bot.is_owner(ctx.author):
            return True
        if isinstance(ctx.author, discord.Member):
            if ctx.author.guild_permissions.manage_guild:
                return True
        return True

    @cache(strategy=Strategy.lru, maxsize=1000, ignore_kwargs=True)
    async def is_context_valid(self, ctx: DuckContext):
        ...  # TODO: implement

    @commands.group(name='config')
    @commands.has_permissions(manage_guild=True)
    async def config(self, ctx: DuckContext):
        """|coro|

        Base command to configure the bot.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
            # TODO: Show all this server's enabled configs.

    @config.command(name='ignore')
    async def config_ignore(
            self,
            ctx: DuckContext,
            *ignorable: Union[discord.abc.GuildChannel, discord.Member, discord.Role]
    ):
        """|coro|

        Ignores a member, channel or role.
        """
        async with ctx.bot.safe_connection() as conn:
            pass
