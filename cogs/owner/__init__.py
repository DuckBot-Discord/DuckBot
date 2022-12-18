from utils import DuckContext, HandleHTTPException
from discord.ext.commands import NotOwner
from utils import command

from .blacklist import BlackListManagement
from .test_shit import TestingShit
from .badges import BadgeManagement
from .eval import Eval
from .sql import SQLCommands
from .update import ExtensionsManager
from .api import Api


class Owner(
    BlackListManagement,
    TestingShit,
    BadgeManagement,
    Eval,
    Api,
    SQLCommands,
    ExtensionsManager,
    command_attrs=dict(hidden=True),
    emoji="<:blushycat:913554213555028069>",
    brief="Restricted! hah.",
):
    """The Cog for All owner commands."""

    async def cog_check(self, ctx: DuckContext) -> bool:
        """Check if the user is a bot owner."""
        if await ctx.bot.is_owner(ctx.author):
            return True
        raise NotOwner

    @command()
    async def sync(self, ctx: DuckContext):
        """Syncs commands."""
        msg = await ctx.send("Syncing...")
        ctx.bot.tree.copy_global_to(guild=ctx.guild)
        async with HandleHTTPException(ctx):
            cmds = await ctx.bot.tree.sync(guild=ctx.guild)
            await msg.edit(content=f"✅ Synced {len(cmds)} commands.")


async def setup(bot):
    await bot.add_cog(Owner(bot))
