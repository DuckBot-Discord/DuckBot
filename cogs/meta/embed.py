import re
import typing
import discord
from discord.ext import commands

from utils import DuckContext, DuckCog, command
from cogs.tags import TagName

try:
    from utils.ignored import HORRIBLE_HELP_EMBED
except ImportError:
    HORRIBLE_HELP_EMBED = discord.Embed(title='No information available...')

__all__ = ('EmbedMaker', 'EmbedFlags')


def strip_codeblock(content):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
        return content.strip('```')

    # remove `foo`
    return content.strip('` \n')


def verify_link(argument: str) -> str:
    link = re.fullmatch('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|%[0-9a-fA-F][0-9a-fA-F])+', argument)
    if not link:
        raise commands.BadArgument('Invalid URL provided.')
    return link.string


class FieldFlags(commands.FlagConverter, prefix='--', delimiter='', case_insensitive=True):
    name: str
    value: str
    inline: bool = True


class FooterFlags(commands.FlagConverter, prefix='--', delimiter='', case_insensitive=True):
    text: str
    icon: verify_link = None


class AuthorFlags(commands.FlagConverter, prefix='--', delimiter='', case_insensitive=True):
    name: str
    icon: verify_link = None
    url: verify_link = None


class EmbedFlags(commands.FlagConverter, prefix='--', delimiter='', case_insensitive=True):
    @classmethod
    async def convert(cls, ctx: DuckContext, argument: str):
        argument = strip_codeblock(argument).replace(' —', ' --')
        # Here we strip the code block if any and replace the iOS dash with
        # a regular double-dash for ease of use.
        return await super().convert(ctx, argument)

    title: str = None
    description: str = None
    color: discord.Color = None
    field: typing.List[FieldFlags] = None
    footer: FooterFlags = None
    image: verify_link = None
    author: AuthorFlags = None
    thumbnail: verify_link = None
    save: TagName = None


class EmbedMaker(DuckCog):
    @command(brief='Sends an embed using flags')
    async def embed(self, ctx: DuckContext, *, flags: EmbedFlags):
        """|coro|

        Sends an embed using flags.
        Please see ``embed --help`` for
        usage information.

        Parameters
        ----------
        flags: EmbedFlags
            The flags to use.
        """

        if isinstance(flags, str) and flags.lower() == '--help':
            return await ctx.send(embed=HORRIBLE_HELP_EMBED)

        embed = discord.Embed(title=flags.title, description=flags.description, colour=flags.color)

        if flags.field and len(flags.field) > 25:
            raise commands.BadArgument('You can only have up to 25 fields!')

        for f in flags.field or []:
            embed.add_field(name=f.name, value=f.value, inline=f.inline)

        if flags.thumbnail:
            embed.set_thumbnail(url=flags.thumbnail)

        if flags.image:
            embed.set_image(url=flags.image)

        if flags.author:
            embed.set_author(name=flags.author.name, url=flags.author.url, icon_url=flags.author.icon)

        if flags.footer:
            embed.set_footer(text=flags.footer.text, icon_url=flags.footer.icon or None)

        if not embed:
            raise commands.BadArgument('You must pass at least one of the necessary (marked with `*`) flags!')
        if len(embed) > 6000:
            raise commands.BadArgument('The embed is too big! (too much text!) Max length is 6000 characters.')
        if not flags.save:
            try:
                await ctx.channel.send(embed=embed)
            except discord.HTTPException as e:
                raise commands.BadArgument(f'Failed to send the embed! {type(e).__name__}: {e.text}`')
            except Exception as e:
                raise commands.BadArgument(f'An unexpected error occurred: {type(e).__name__}: {e}')
        else:
            query = """
                SELECT EXISTS (
                    SELECT * FROM tags
                    WHERE name = $1
                    AND guild_id = $2
                    AND owner_id = $3
                )
            """
            confirm = await ctx.bot.pool.fetchval(query, flags.save, ctx.guild.id, ctx.author.id)
            if confirm is True:
                confirm = await ctx.confirm(
                    f"{ctx.author.mention} do you want to add this embed to "
                    f"tag {flags.save!r}\n_This prompt will time out in 3 minutes, "
                    f"so take your time_",
                    embed=embed,
                    timeout=180,
                )
                if confirm is True:
                    query = """
                        with upsert as (
                            UPDATE tags
                            SET embed = $1
                            WHERE name = $2
                            AND guild_id = $3
                            AND owner_id = $4
                            RETURNING *
                        )
                         SELECT EXISTS ( SELECT * FROM upsert )   
                    """
                    added = await ctx.bot.pool.fetchval(query, embed.to_dict(), flags.save, ctx.guild.id, ctx.author.id)
                    if added is True:
                        await ctx.send(f'Added embed to tag {flags.save!r}!')
                    else:
                        await ctx.send(f'Could not edit tag. Are you sure it exists and you own it?')
                elif confirm is False:
                    await ctx.send(f'Cancelled!')
            else:
                await ctx.send(f'Could not find tag {flags.save!r}. Are you sure it exists and you own it?')
