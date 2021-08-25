import asyncio
from inspect import Parameter
import discord
import json
import re
import typing
import unicodedata

from typing import Optional
from discord.ext import commands, menus
from discord.ext.commands.core import command

import errors

class EmbedPageSource(menus.ListPageSource):

    async def format_page(self, menu, item):
        embed = discord.Embed(description="\n".join(item), title="ℹ Character information")
        return embed


class General(commands.Cog):
    """💬 Text commands. """

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='charinfo')
    @commands.max_concurrency(1, per=commands.BucketType.user, wait=False)
    async def character_info(self, ctx, *, characters: str):
        """Shows you information about a number of characters."""

        def to_string(c):
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, 'Name not found.')
            return f'`\\U{digit:>08}`: {name} - **{c}** \N{EM DASH} ' \
                   f'<http://www.fileformat.info/info/unicode/char/{digit}>'

        msg = '\n'.join(map(to_string, characters))

        menu = menus.MenuPages(EmbedPageSource(msg.split("\n"), per_page=20), delete_message_after=True)
        await menu.start(ctx)

    # .s <text>
    # resends the message as the bot

    @commands.command(aliases=['s', 'send'],
                      help="Speak as if you were me. # URLs/Invites not allowed!")
    @commands.check_any(commands.bot_has_permissions(send_messages=True, manage_messages=True), commands.is_owner())
    async def say(self, ctx: commands.context, *, msg: str) -> Optional[discord.Message]:

        results = re.findall(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
                             msg)  # HTTP/HTTPS URL regex
        results2 = re.findall(r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?",
                              msg)  # Discord invite regex
        if results or results2:
            await ctx.send(
                f"`Urls or invites aren't allowed!",
                delete_after=5)
            await ctx.message.delete(delay=5)

        await ctx.message.delete(delay=0)

        return await ctx.send(msg, allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True), reference=ctx.message.reference)

    # .a <TextChannel> <text>
    # sends the message in a channel

    @commands.command(
        aliases=['a', 'an', 'announce'],
        usage="<message or reply>")
    @commands.check_any(commands.has_permissions(manage_messages=True), commands.is_owner())
    @commands.check_any(commands.bot_has_permissions(send_messages=True, manage_messages=True), commands.is_owner())
    async def echo(self, ctx: commands.Context, channel: discord.TextChannel, *, message_or_reply: str = None) -> discord.Message:
        """"Echoes a message to another channel"""
        if not ctx.message.reference and not message_or_reply:
            raise commands.MissingRequiredArgument(
                Parameter(name='message or reply', kind=Parameter.POSITIONAL_ONLY))
        elif ctx.message.reference:
            msg = ctx.message.reference.resolved
        return await channel.send(msg, allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True))

    @commands.command(
        aliases=['e'],
        usage="[reply] [new message] [--d|--s]")
    @commands.check_any(commands.has_permissions(manage_messages=True), commands.is_owner())
    @commands.check_any(commands.bot_has_permissions(send_messages=True, manage_messages=True), commands.is_owner())
    async def edit(self, ctx, *, new: typing.Optional[str] = '--d'):
        """Quote a bot message to edit it. # Append --s at the end to supress embeds and --d to delete the message"""
        if ctx.message.reference:
            msg = ctx.message.reference.resolved
            if new.endswith("--s"):
                await msg.edit(content=f"{new[:-3]}", suppress=True)
            elif new.endswith('--d'):
                await msg.delete()
            else:
                await msg.edit(content=new, suppress=False)
            await ctx.message.delete(delay=0.1)
        else:
            raise errors.NoQuotedMessage

    # .jumbo <Emoji>
    # makes emoji go big

    @commands.group(help="Makes an emoji bigger and shows it's formatting",
                    invoke_without_command=True,
                    aliases=['em'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def emoji(self, ctx, custom_emojis: commands.Greedy[discord.PartialEmoji]):
        if len(custom_emojis) > 5:
            raise commands.TooManyArguments()

        for emoji in custom_emojis:
            if emoji.animated:
                emoticon = f"*`<`*`a:{emoji.name}:{emoji.id}>`"
            else:
                emoticon = f"*`<`*`:{emoji.name}:{emoji.id}>`"
            embed = discord.Embed(description=f"{emoticon}", color=ctx.me.color)
            embed.set_image(url=emoji.url)
            await ctx.send(embed=embed)

    @emoji.command(name="lock")
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    async def emoji_lock(self, ctx):
        await ctx.send("not yet implemented sorry")

    @emoji.command(name="steal",
                   hidden=True,
                   aliases=['s'])
    @commands.is_owner()
    async def emoji_steal(self, ctx, index: int = 1):
        if not ctx.message.reference:
            raise errors.NoQuotedMessage

        custom_emoji = re.compile(r"<a?:[a-zA-Z0-9_]+:[0-9]+>")
        emojis = custom_emoji.findall(ctx.message.reference.resolved.content)
        if not emojis:
            raise errors.NoEmojisFound

        emoji = await commands.PartialEmojiConverter().convert(ctx, emojis[index - 1])
        file = await emoji.read()
        guild = self.bot.get_guild(831313673351593994)
        emoji = await guild.create_custom_emoji(name=emoji.name, image=file, reason="stolen emoji KEK")
        try:
            await ctx.message.add_reaction(emoji)
        except discord.NotFound:
            pass

    # .uuid <minecraft_username>
    # gets user's UUID (minecraft)

    @commands.command(help="Fetches the UUID of a minecraft user",
                      usage="<Minecraft username>")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def uuid(self, ctx: commands.Context, *, argument: typing.Optional[str] = None) -> Optional[discord.Message]:
        async with self.bot.session.get(f"https://api.mojang.com/users/profiles/minecraft/{argument}") as cs:
            embed = discord.Embed(color=ctx.me.color)
            if cs.status == 204:
                embed.add_field(name='⚠ ERROR ⚠', value=f"`{argument}` is not a minecraft username!")

            elif cs.status == 400:
                embed.add_field(name="⛔ ERROR ⛔", value="ERROR 400! Bad request.")
            else:
                res = await cs.json()
                user = res["name"]
                uuid = res["id"]
                embed.add_field(name=f'Minecraft username: `{user}`', value=f"**UUID:** `{uuid}`")
            await ctx.send(embed=embed)

    @commands.command(help="Makes the bot send an embed to a channel.", usage="")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, manage_messages=True)
    @commands.max_concurrency(1, per=commands.BucketType.user, wait=False)
    async def embed(self, ctx, channel: typing.Optional[discord.TextChannel], *, data=None):
        channel = channel or ctx.channel
        if data:
            try:
                dictionary = json.loads(data)
            except json.JSONDecodeError:
                return await ctx.send("Invalid dictionary! Please try again <3")

            embed = discord.Embed().from_dict(dictionary)
            await channel.send(embed=embed)

        embed = discord.Embed(color=0x47B781, description="0️⃣ **STEP ZERO: Text**")
        embed.add_field(
            name="What do you want your embed text to be?",
            value="send `ping everyone` to ping @everyone\nsend `ping here` to ping @here\nsend `skip` to skip. you "
                  "can use __**`markdown`**__ here")
        embed.set_footer(text="all prompts expire in 5 minutes! Send \"cancel\" to cancel")
        message = await ctx.send(ctx.author.mention, embed=embed)

        announcement_embed = discord.Embed(title="Announcement visualization")
        announcement = await ctx.send(embed=announcement_embed)

        # Message check
        def check(m: discord.Message):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

        try:
            msg = await self.bot.wait_for(event='message', check=check, timeout=600.0)
        except asyncio.TimeoutError:
            err = discord.Embed(color=0xD7342A, description=f"**Sorry, you didn't respond in time**")
            await message.edit(content=ctx.author.mention, embed=err)
            return
        else:
            if msg.content.lower() == "skip":
                try:
                    await msg.delete()
                except:
                    pass
                announcement_content = ""
            elif msg.content.lower() == "ping everyone":
                try:
                    await msg.delete()
                except:
                    pass
                announcement_content = "@everyone"
                await announcement.edit(content=announcement_content, embed=announcement_embed)
            elif msg.content.lower() == "ping here":
                try:
                    await msg.delete()
                except:
                    pass
                announcement_content = "@here"
                await announcement.edit(content=announcement_content, embed=announcement_embed)
            elif msg.content.lower() == "cancel":
                await message.edit(embed=discord.Embed(color=0xD7342A, title="Cancelled"))
                return
            else:
                try:
                    await msg.delete()
                except:
                    pass
                announcement_content = msg.content
                await announcement.edit(content=announcement_content, embed=announcement_embed)

        embed.clear_fields()
        embed.description = "1️⃣ **STEP ONE: Title**"
        embed.add_field(name="What do you want your embed title to be?", value="send `skip` to skip.")
        await message.edit(content=ctx.author.mention, embed=embed)

        try:
            msg = await self.bot.wait_for(event='message', check=check, timeout=600.0)
        except asyncio.TimeoutError:
            err = discord.Embed(color=0xD7342A, description=f"**Sorry, you didn't respond in time**")
            await message.edit(content=ctx.author.mention, embed=err)
            return
        else:
            if msg.content.lower() == "skip":
                try:
                    await msg.delete()
                except:
                    pass
                announcement_embed.title = None
            elif msg.content.lower() == "cancel":
                await message.edit(embed=discord.Embed(color=0xD7342A, title="Cancelled"))
                return
            else:
                try:
                    await msg.delete()
                except:
                    pass
                announcement_embed.title = msg.content
                await announcement.edit(embed=announcement_embed)

        embed.clear_fields()
        embed.description = "2️⃣ **STEP TWO: description**"
        embed.add_field(name="What do you want your embed description to be?",
                        value="send `skip` to skip. you can use __**`markdown`**__ here")
        await message.edit(content=ctx.author.mention, embed=embed)

        iteration_amount = 0
        while iteration_amount == 0:
            try:
                msg = await self.bot.wait_for(event='message', check=check, timeout=600.0)
            except asyncio.TimeoutError:
                err = discord.Embed(color=0xD7342A, description=f"**Sorry, you didn't respond in time**")
                await message.edit(content=ctx.author.mention, embed=err)
                return
            else:
                if msg.content.lower() == "skip":
                    if not announcement_embed.title:
                        try:
                            await msg.delete()
                        except:
                            pass
                        await ctx.send("Title already skipped. you can't skip the description.", delete_after=5)
                    else:
                        try:
                            await msg.delete()
                        except:
                            pass
                        announcement_embed.description = None
                        iteration_amount = 1

                elif msg.content.lower() == "cancel":
                    await message.edit(embed=discord.Embed(color=0xD7342A, title="Cancelled"))
                    return
                else:
                    try:
                        await msg.delete()
                    except:
                        pass
                    announcement_embed.description = msg.content
                    await announcement.edit(embed=announcement_embed)
                    iteration_amount = 1

        embed.clear_fields()
        embed.description = "3️⃣ **STEP THREE: Color**"
        embed.add_field(
            name="What color of embed you want?",
            value="send `skip` to leave it as default. [COLOR PICKER]("
                  "https://www.google.com/search?q=Color+picker)\nsend `invisible` to make the color invisible (same "
                  "as the embed BG)")
        await message.edit(content=ctx.author.mention, embed=embed)

        iteration_amount = 0
        while iteration_amount == 0:
            try:
                msg = await self.bot.wait_for(event='message', check=check, timeout=600.0)
            except asyncio.TimeoutError:
                err = discord.Embed(color=0xD7342A, description=f"**Sorry, you didn't respond in time**")
                await message.edit(content=ctx.author.mention, embed=err)
                return
            else:
                if msg.content.lower() == "skip":
                    try:
                        await msg.delete()
                    except:
                        pass
                    iteration_amount = 1
                elif msg.content.lower() == "invisible":
                    try:
                        await msg.delete()
                    except:
                        pass
                    announcement_embed.colour = 0x2F3136
                    await announcement.edit(embed=announcement_embed)
                    iteration_amount = 1
                elif msg.content.lower() == "cancel":
                    await message.edit(embed=discord.Embed(color=0xD7342A, title="Cancelled"))
                    return
                elif re.match(r"^#?(?:[0-9a-fA-F]{3}){1,2}$", msg.content):
                    try:
                        await msg.delete()
                    except (discord.Forbidden, discord.HTTPException, discord.NotFound):
                        pass
                    color = msg.content.replace("#", "")
                    color = int(color, 16)
                    announcement_embed.colour = color
                    await announcement.edit(embed=announcement_embed)
                    iteration_amount = 1
                else:
                    try:
                        await msg.delete()
                    except:
                        pass
                    await ctx.send("that's not a valid hex code!", delete_after=5)

        embed.clear_fields()
        embed.description = "4️⃣ **STEP FOUR: fields**"
        embed.add_field(name="What do you want your fields to be?",
                        value="Send `skip` to skip."
                              "\nSend `done` to finish adding fields. "
                              "\n\nFormat: `NAME ~ VALUE ~ in-line(yes/no)`"
                              "\nNAME: max characters = 256 "
                              "\nVALUE: max characters = 1024",
                        inline=False)
        embed.add_field(name="_ _", value="_ _", inline=False)
        embed.add_field(name="NAME - this is an in-line field",
                        value="VALUE - this is an example value for an in-line field", inline=True)
        embed.add_field(name="NAME - this is an in-line field",
                        value="VALUE - this is an example value for an in-line field", inline=True)
        embed.add_field(name="NAME - this is a not in-line field",
                        value="VALUE - this is an example value for a field in-line that "
                              "is not in-line, as you can see they are made in a new line.",
                        inline=False)
        embed.add_field(name="_ _", value="_ _", inline=False)
        await message.edit(content=ctx.author.mention, embed=embed)

        iteration_amount = 0
        while iteration_amount == 0:
            try:
                msg = await self.bot.wait_for(event='message', check=check, timeout=600.0)
            except asyncio.TimeoutError:
                err = discord.Embed(color=0xD7342A, description=f"**Sorry, you didn't respond in time**")
                await message.edit(content=ctx.author.mention, embed=err)
                return
            else:
                if msg.content.lower() == "skip" or msg.content == "done":
                    try:
                        await msg.delete()
                    except:
                        pass
                    iteration_amount = 1

                elif msg.content.lower() == "cancel":
                    await message.edit(embed=discord.Embed(color=0xD7342A, title="Cancelled"))
                    return

                elif re.match(r"^(((?s).{1,256})~((?s).{1,1024})~(yes|no| yes| no))$", msg.content.replace("\n", " ")):
                    try:
                        await msg.delete()
                    except:
                        pass
                    if msg.content.split("~")[2].replace(" ", "") == "yes":
                        inl = True
                    else:
                        inl = False
                    announcement_embed.add_field(name=msg.content.split("~")[0], value=msg.content.split("~")[1],
                                                 inline=inl)
                    await announcement.edit(embed=announcement_embed)
                    if len(announcement_embed.fields) >= 25:
                        await ctx.send("max amount of fields reached!", delete_after=5)
                        iteration_amount = 1
                else:
                    try:
                        await msg.delete(delay=20)
                    except:
                        pass
                    embed.description = "4️⃣ **STEP FOUR: fields** " \
                                        "\n\nsomething went wrong! remember to add " \
                                        "the `~` to separate the values. " \
                                        "\nformat: `NAME ~ VALUE ~ in-line(yes/no)`" \
                                        "\nYou must format your field like: ```" \
                                        "\nName (max: 1024 characters) ~ " \
                                        "Value (max: 1024 characters) ~ inline(yes/no)```" \
                                        "\n**example:**```\nI'm a name ~ I'm  a value ~ yes```"
                    embed.clear_fields()
                    await message.edit(content=ctx.author.mention, embed=embed)

        embed.clear_fields()
        embed.description = "5️⃣ **STEP FIVE: footer**"
        embed.add_field(name="What do you want the footer to be?",
                        value=f"send `skip` to skip.\nSend `default` to set the default footer"
                              f"\n _Default is `message sent by {ctx.author}`_")
        await message.edit(content=ctx.author.mention, embed=embed)

        try:
            msg = await self.bot.wait_for(event='message', check=check, timeout=600.0)
        except asyncio.TimeoutError:
            err = discord.Embed(color=0xD7342A, description=f"**Sorry, you didn't respond in time**")
            await message.edit(content=ctx.author.mention, embed=err)
            return
        else:
            if msg.content.lower() == "skip":
                try:
                    await msg.delete()
                except:
                    pass
            elif msg.content.lower() == "cancel":
                await message.edit(embed=discord.Embed(color=0xD7342A, title="Cancelled"))
                return
            elif msg.content.lower() == "default":
                try:
                    await msg.delete()
                except:
                    pass
                announcement_embed.set_footer(text=f"Sent by {ctx.author}", icon_url=ctx.author.avatar.url)
                await announcement.edit(embed=announcement_embed)
            else:
                try:
                    await msg.delete()
                except:
                    pass
                announcement_embed.set_footer(text=msg.content)
                await announcement.edit(embed=announcement_embed)

        embed.clear_fields()
        embed.description = "6️⃣ **STEP SIX: channel**"
        embed.add_field(name="Where do you want to send the embed to?",
                        value=f"send `cancel` to cancel. you can't skip this step "
                              f"\n only `#channel` mentions work. IDs don't work.")
        await message.edit(content=ctx.author.mention, embed=embed)

        iteration_amount = 0
        while iteration_amount == 0:
            try:
                msg = await self.bot.wait_for(event='message', check=check, timeout=600.0)
            except asyncio.TimeoutError:
                err = discord.Embed(color=0xD7342A, description=f"**Sorry, you didn't respond in time**")
                await message.edit(content=ctx.author.mention, embed=err)
                return
            else:
                if msg.content.lower() == "cancel":
                    await message.edit(embed=discord.Embed(color=0xD7342A, title="Cancelled"))
                    return
                elif msg.channel_mentions:
                    try:
                        await msg.delete()
                    except:
                        pass
                    channel = msg.channel_mentions[0]

                    if channel.type == discord.ChannelType.text:
                        if channel.permissions_for(ctx.author).send_messages:
                            if channel.permissions_for(ctx.me).send_messages and channel.permissions_for(
                                    ctx.me).embed_links:
                                await channel.send(announcement_content, embed=announcement_embed)
                                await announcement.delete()
                                if channel == ctx.channel:
                                    await message.delete()
                                else:
                                    embed = discord.Embed(color=0x47B781, description="💌 Sent!")
                                    await message.edit(content=ctx.author.mention, embed=embed)
                                iteration_amount = 1
                            else:
                                try:
                                    await msg.delete()
                                except:
                                    pass
                                await ctx.send("I can't send messages to that channel. mention another channel",
                                               delete_after=5)
                        else:
                            try:
                                await msg.delete()
                            except:
                                pass
                            await ctx.send("You can't send messages to that channel. mention another channel",
                                           delete_after=5)
                    else:
                        try:
                            await msg.delete()
                        except:
                            pass
                        await ctx.send("Invalid channel", delete_after=5)
                else:
                    try:
                        await msg.delete()
                    except:
                        pass
                    await ctx.send("Invalid channel", delete_after=5)


def setup(bot):
    bot.add_cog(General(bot))
