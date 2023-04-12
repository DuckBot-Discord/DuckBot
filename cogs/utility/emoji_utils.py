import asyncio
import re
import typing
from io import BytesIO
from inspect import Parameter

import discord
from discord.ext import commands

import errors
from bot import CustomContext
from helpers import paginator, constants
from ._base import UtilityBase

async def render_with_rsvg(blob):
    rsvg = 'rsvg-convert --width=1024'
    proc = await asyncio.create_subprocess_shell(rsvg,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate(blob)
    return BytesIO(stdout), stderr

    converted, stderr = await renderWithRsvg()

SVG_URL = 'https://raw.githubusercontent.com/twitter/twemoji/master/assets/svg/{chars}.svg'


class EmojiUtils(UtilityBase):
    @commands.group(invoke_without_command=True, aliases=['em'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def emoji(
        self, ctx: CustomContext, custom_emojis: commands.Greedy[typing.Union[discord.Emoji, discord.PartialEmoji]]
    ):
        """
        Shows information about one or more emoji.
        _Note, this is a group, and has also more sub-commands_
        """
        if not custom_emojis:
            raise commands.MissingRequiredArgument(Parameter(name='custom_emojis', kind=Parameter.POSITIONAL_ONLY))

        source = paginator.EmojiListPageSource(data=custom_emojis, ctx=ctx)
        menu = paginator.ViewPaginator(source=source, ctx=ctx, check_embeds=True)
        await menu.start()

    @emoji.command(name="lock")
    @commands.guild_only()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji_lock(
        self, ctx: CustomContext, server_emoji: discord.Emoji, roles: commands.Greedy[discord.Role]
    ) -> discord.Message:
        """
        Locks an emoji to one or multiple roles. Input as many roles as you want in the "[roles]..." parameter.
        Note: admin/owner DOES NOT bypass this lock, so be sure to have the role if you wish to unlock the emoji.
        # If the role is removed and re-assigned, the locked emoji will not be visible until you restart your client.
        # To unlock an emoji you can't access, use the `db.emoji unlock <emoji_name>` command
        """
        if not roles:
            raise commands.MissingRequiredArgument(Parameter('role', Parameter.POSITIONAL_ONLY))
        if server_emoji.guild_id != ctx.guild.id:
            return await ctx.send("That emoji is from another server!")
        embed = discord.Embed(
            description=f"**Restricted access of {server_emoji} to:**"
            f"\n{', '.join([r.mention for r in roles])}"
            f"\nTo unlock the emoji do `{ctx.clean_prefix} emoji unlock {server_emoji}`"
            f"_Note that to do this you will need one of the roles the emoji has been "
            f"restricted to. \nNo, admin permissions don't bypass this lock._"
        )
        await ctx.send(embed=embed)
        await server_emoji.edit(roles=roles)

    @emoji.group(name="unlock", invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji_unlock(self, ctx: CustomContext, server_emoji: discord.Emoji) -> discord.Message:
        """
        Unlocks a locked emoji.
        **Note:** If you don't have access to the emoji you can also do:

        **__GOOD:__** `%PRE%emoji unlock RooDuck`
        **__BAD:__** `%PRE%emoji unlock :RooDuck:`
        """
        if server_emoji.guild_id != ctx.guild.id:
            return await ctx.send("That emoji is from another server!")
        await server_emoji.edit(roles=[])
        embed = discord.Embed(title="Successfully unlocked emoji!", description=f"**Allowed {server_emoji} to @everyone**")
        return await ctx.send(embed=embed)

    @emoji_unlock.command(name="all")
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji_unlock_all(self, ctx: CustomContext):
        """
        Unlocks all locked emojis in the current server.
        """
        async with ctx.typing():
            unlocked = []
            for emoji in ctx.guild.emojis:
                if emoji.roles:
                    await emoji.edit(roles=[], reason=f"Unlock all emoji requested by {ctx.author} ({ctx.author.id})")
                    unlocked.append(emoji)
                    await asyncio.sleep(1)
            await ctx.send(f"Done! Unlocked {len(unlocked)} emoji(s)" f"\n {' '.join([str(em) for em in unlocked])}")

    @emoji.command(name="steal", hidden=True, aliases=['s'])
    @commands.is_owner()
    async def emoji_steal(self, ctx, index: int = 1):
        if not ctx.message.reference:
            raise errors.NoQuotedMessage

        custom_emoji = re.compile(r"<a?:[a-zA-Z0-9_]+:[0-9]+>")
        emojis = custom_emoji.findall(ctx.message.reference.resolved.content)
        if not emojis:
            raise errors.NoEmojisFound

        try:
            emoji = await commands.PartialEmojiConverter().convert(ctx, emojis[index - 1])
        except IndexError:
            return await ctx.send(
                f"Emoji out of index {index}/{len(emojis)}!" f"\nIndex must be lower or equal to {len(emojis)}"
            )
        file = await emoji.read()
        guild = self.bot.get_guild(831313673351593994)
        emoji = await guild.create_custom_emoji(name=emoji.name, image=file, reason="stolen emoji KEK")
        try:
            await ctx.message.add_reaction(emoji)
        except discord.NotFound:
            pass

    @emoji.command(name="clone", aliases=['create'])
    @commands.guild_only()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji_clone(
        self,
        ctx: CustomContext,
        server_emoji: typing.Optional[discord.PartialEmoji],
        index: typing.Optional[int] = 1,
        *,
        name: typing.Optional[str] = '#',
    ):
        """
        Clones an emoji into the current server.
        You can pass either an emoji or an index, not both.

        What is index? Index is for stealing emotes from other people. To do so, reply to their message, and pass a number (index) to select which emoji to steal. For example, to steal the first emoji of the quoted message, pass a number `1`
        If you don't pass an emoji nor a number, and you quoted a message, it will select the first emoji in the message, if applicable.

        Note: You can only pass an emoji _or_ an index, not both.
        """
        if ctx.message.reference:
            custom_emoji = re.compile(r"<a?:[a-zA-Z0-9_]+:[0-9]+>")
            emojis = custom_emoji.findall(ctx.message.reference.resolved.content)
            if not emojis:
                raise errors.NoEmojisFound
            try:
                server_emoji = await commands.PartialEmojiConverter().convert(ctx, emojis[index - 1])
            except IndexError:
                return await ctx.send(
                    f"Emoji out of index {index}/{len(emojis)}!" f"\nIndex must be lower or equal to {len(emojis)}"
                )

        if not server_emoji:
            raise commands.MissingRequiredArgument(Parameter(name='server_emoji', kind=Parameter.POSITIONAL_ONLY))

        file = await server_emoji.read()
        guild = ctx.guild

        valid_name = re.compile('^[a-zA-Z0-9_]+$')

        server_emoji = await guild.create_custom_emoji(
            name=name if valid_name.match(name) else server_emoji.name,
            image=file,
            reason=f"Cloned emoji, requested by {ctx.author}",
        )
        await ctx.send(f"**Done!** cloned {server_emoji} **|** `{server_emoji}`")

    @emoji.command(usage="", name='list')
    @commands.guild_only()
    async def emoji_list(
        self, ctx: CustomContext, guild: typing.Optional[typing.Union[discord.Guild, typing.Literal['bot']]]
    ):
        """Lists this server's emoji"""
        target_guild = (
            guild
            if isinstance(guild, discord.Guild) and (await self.bot.is_owner(ctx.author))
            else 'bot'
            if isinstance(guild, str) and (await self.bot.is_owner(ctx.author))
            else ctx.guild
        )
        emojis = target_guild.emojis if isinstance(target_guild, discord.Guild) else self.bot.emojis

        emotes = [f"{str(e)} **|** `{e.id}` **|** [{e.name}]({e.url})" for e in emojis]
        menu = paginator.ViewPaginator(
            paginator.ServerEmotesEmbedPage(
                data=emotes, guild=(target_guild if isinstance(target_guild, discord.Guild) else ctx.bot)
            ),
            ctx=ctx,
        )
        await menu.start()

    @emoji.command(name='delete')
    @commands.guild_only()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji_delete(self, ctx: CustomContext, server_emoji: discord.Emoji):
        """
        Deletes an emoji from this server.
        """
        if server_emoji.guild != ctx.guild:
            raise commands.MissingRequiredArgument(Parameter(name='server_emoji', kind=Parameter.POSITIONAL_ONLY))
        confirm = await ctx.confirm(f'❓ | Are you sure you want to delete {server_emoji}?', return_message=True)

        if confirm[0]:
            await server_emoji.delete(reason=f'Deletion requested by {ctx.author} ({ctx.author.id})')
            await confirm[1].edit(content=f'🚮 | Successfully deleted `{server_emoji}`', view=None)
        else:
            await confirm[1].edit(content='❌ | Cancelled!', view=None)

    @emoji.command(name='rename')
    @commands.guild_only()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji_rename(self, ctx, server_emoji: discord.Emoji, new_name: commands.clean_content):
        """
        Renames an emoji from this server.
        """
        new_name: str
        if server_emoji.guild != ctx.guild:
            raise commands.MissingRequiredArgument(Parameter(name='server_emoji', kind=Parameter.POSITIONAL_ONLY))
        if len(new_name) > 32:
            raise commands.BadArgument('⚠ | **new_name** must be less than **32 characters** in long.')
        if server_emoji.name == new_name:
            raise commands.BadArgument(f"⚠ | {server_emoji} is already named {new_name}")

        valid_name = re.compile('^[a-zA-Z0-9_]+$')
        if not valid_name.match(new_name):
            raise commands.BadArgument('⚠ | **new_name** can only contain **alphanumeric characters** and **underscores**')
        new_emoji = await server_emoji.edit(name=new_name, reason='Deletion requested by {ctx.author} ({ctx.author.id})')
        await ctx.send(
            f"{constants.EDIT_NICKNAME} | Successfully renamed {new_emoji} from `{server_emoji.name}` to `{new_emoji.name}`!"
        )

    @commands.command()
    async def svg(self, ctx, ipt):
        """Enlargens a default emoji by rendeding it's SVG asset from the twemoji github repository"""
        chars = '-'.join(f'{ord(c):x}' for c in ipt)

        resp = await self.bot.session.get(SVG_URL.format(chars=chars))
        if resp.status != 200:
            return await ctx.send("not a valid unicode emoji.")
        blob = await resp.read()

        converted, stderr= await render_with_rsvg(blob)

        file = discord.File(converted, filename="rendered.png")
        await ctx.send(file=file)