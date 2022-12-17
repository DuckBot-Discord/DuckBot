import re
import typing
import discord
from discord.ext import commands

from ._base import FunBase
from helpers.context import CustomContext


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
    async def convert(cls, ctx: CustomContext, argument: str):
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


class EmbedMaker(FunBase):
    @commands.command(brief='Sends an embed using flags')
    async def embed(self, ctx: commands.Context, *, flags: EmbedFlags):
        """
        A test command for trying out the new flags feature in discord.py v2.0
        Flag usage: `--flag [flag string]`
        Note that `--text... [text]` (with ellipsis) can accept a repeated amount of them:
        Like for example, in this case, with the flag `text`:
        `--text hello --text hi how r u --text a third text and so on`
        `--text...(25)` would mean it can have up to 25 different inputs.
        `--text [text*]` would mean that its **necessary but not mandatory**. AKA if there's multiple of them, you can pass only one, and it will work. But you need **__at least one of the flags marked with `*`__**

        Flags that have an `=` sign mean that they have a default value.
        for example: `--color [Color=#ffffff]` means the color will be `#ffffff` if it can't find a color in the given input.
        Flags can also be mandatory, for example: `--text <text>`. the `<>` brackets mean it is not optional

        **Available flags:**
        `--title [text*]` Sets the embed title.
        `--description [text*]` Sets the embed body/description.
        `--color [color]` Sets the embed's color.
        `--image [http/https URL*]` Sets the embed's image.
        `--thumbnail [http/https URL*]` Sets the embed's thumbnail.
        `--author [AuthorFlags*]` Sets the embed's author.
        `--field...(25) [FieldFlags*]` Sets one of the embed's fields using field flags.
        `--footer [FooterFlags*]` Sets the embed's footer using footer flags.

        **AuthorFlags:**
        > `--name [text*]` Sets the author's name.
        > `--url [http/https URL*]` Sets the author's url.
        > `--icon [http/https URL*]` Sets the author's icon.

        **FieldFlags:**
        > `--name <text>` Sets that field's name
        > `--value <text>` Sets that field's value / body
        > `--inline [yes/no]` If the field should be in-line (displayed alongside other in-line fields if any)
        **For example:** `--field --name hi hello --value more text --inline no`
        _Note: You can have multiple `--field`(s) using `--name` and `--value` (up to 25)_

        **FooterFlags:**
        > `--text [text]` Sets the footer's text
        > `--icon [http/https URL]` Sets the footer's icon

        **Here is an example of the command:**
        ```
        %PRE%embed --title This is the title
        --description This is the description
        --field --name One --value One
        --field --name Two --value Two
        --field --name Three --value Three (but this one isn't in-line) --inline No
        --footer --text This is the footer text
        ```
        """
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

        if embed:
            if len(embed) > 6000:
                raise commands.BadArgument('The embed is too big! (too much text!)')
            try:
                await ctx.channel.send(embed=embed)
            except discord.HTTPException as e:
                raise commands.BadArgument(f'Failed to send the embed! {type(e).__name__}: {e.text}`')
            except Exception as e:
                raise commands.BadArgument(f'An unexpected error occurred: {type(e).__name__}: {e}')
        else:
            raise commands.BadArgument('You must pass at least one of the necessary (`*`) flags!')
