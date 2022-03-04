from .blacklist import BlackListManagement
from utils import DuckContext
from discord.ext.commands import NotOwner


class Owner(BlackListManagement,
            command_attrs=dict(hidden=True),
            emoji='<:blushycat:913554213555028069>',
            brief='Restricted! hah.'):
    """The Cog for All owner commands."""

    async def cog_check(self, ctx: DuckContext) -> bool:
        """Check if the user is a bot owner."""
        if await ctx.bot.is_owner(ctx.author):
            return True
        raise NotOwner


def setup(bot):
    bot.add_cog(Owner(bot))
