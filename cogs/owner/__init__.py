from utils import DuckContext, HandleHTTPException, cb
from discord.ext.commands import NotOwner, command, Paginator, ExtensionFailed
from traceback import format_exception

from .blacklist import BlackListManagement
from .test_shit import TestingShit
from .badges import BadgeManagement
from .eval import Eval
from .sql import SQLCommands
from .translations import TranslationManager

class Owner(BlackListManagement, TestingShit,
            BadgeManagement, Eval, TranslationManager,
            SQLCommands,
            command_attrs=dict(hidden=True),
            emoji='<:blushycat:913554213555028069>',
            brief='Restricted! hah.'):
    """The Cog for All owner commands."""

    async def cog_check(self, ctx: DuckContext) -> bool:
        """Check if the user is a bot owner."""
        if await ctx.bot.is_owner(ctx.author):
            return True
        raise NotOwner

    @command()
    async def sync(self, ctx: DuckContext):
        """ Syncs commands. """
        msg = await ctx.send('Syncing...')
        ctx.bot.tree.copy_global_to(guild=ctx.guild)
        cmds = await ctx.bot.tree.sync(guild=ctx.guild)
        async with HandleHTTPException(ctx):
            await msg.edit(content=f'✅ Synced {len(cmds)} commands.')

    @command()
    async def rall(self, ctx):
        paginator = Paginator(prefix='', suffix='')
        for extension in list(self.bot.extensions.keys()):
            try:
                await self.bot.reload_extension(extension)
                paginator.add_line(f"\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS} `{extension}`")

            except Exception as e:
                if isinstance(e, ExtensionFailed):
                    e = e.original
                paginator.add_line(f'\N{WARNING SIGN} Failed to load extension: `{extension}`', empty=True)
                error = ''.join(format_exception(type(e), e, e.__traceback__))
                paginator.add_line(cb(error))

        for page in paginator.pages:
            await ctx.send(page)

async def setup(bot):
    await bot.add_cog(Owner(bot))
