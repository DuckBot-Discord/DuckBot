import contextlib
import io
import json
import logging
import os
import re
import urllib
import zlib
from inspect import Parameter

import math

import asyncpg
import discord
import typing
import yarl
from discord.ext import commands

import DuckBot.__main__
from DuckBot import errors
from DuckBot.__main__ import DuckBot
from jishaku.paginators import WrappedPaginator
from DuckBot.cogs.management import get_webhook
from DuckBot.helpers.context import CustomContext


url_regex = re.compile(r"^http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|)+$")
DUCK_HIDEOUT = 774561547930304536
QUEUE_CHANNEL = 927645247226408961
BOTS_ROLE = 870746847071842374
GENERAL_CHANNEL = 774561548659458081
PIT_CATEGORY = 915494807349116958


async def setup(bot):
    await bot.add_cog(Hideout(bot))


def finder(text, collection, *, key=None, lazy=True):
    suggestions = []
    text = str(text)
    pat = ".*?".join(map(re.escape, text))
    regex = re.compile(pat, flags=re.IGNORECASE)
    for item in collection:
        to_search = key(item) if key else item
        r = regex.search(to_search)
        if r:
            suggestions.append((len(r.group()), r.start(), item))

    def sort_key(tup):
        if key:
            return tup[0], tup[1], key(tup[2])
        return tup

    if lazy:
        return (z for _, _, z in sorted(suggestions, key=sort_key))
    else:
        return [z for _, _, z in sorted(suggestions, key=sort_key)]


class SphinxObjectFileReader:
    # Inspired by Sphinx's InventoryFileReader
    BUFSIZE = 16 * 1024

    def __init__(self, buffer):
        self.stream = io.BytesIO(buffer)

    def readline(self):
        return self.stream.readline().decode("utf-8")

    def skipline(self):
        self.stream.readline()

    def read_compressed_chunks(self):
        decompressor = zlib.decompressobj()
        while True:
            chunk = self.stream.read(self.BUFSIZE)
            if len(chunk) == 0:
                break
            yield decompressor.decompress(chunk)
        yield decompressor.flush()

    def read_compressed_lines(self):
        buf = b""
        for chunk in self.read_compressed_chunks():
            buf += chunk
            pos = buf.find(b"\n")
            while pos != -1:
                yield buf[:pos].decode("utf-8")
                buf = buf[pos + 1 :]
                pos = buf.find(b"\n")


def whitelist():
    async def predicate(ctx: CustomContext):
        if await ctx.bot.db.fetchval("SELECT uid FROM inv_whitelist WHERE uid = $1", ctx.author.id):
            return True
        else:
            raise errors.NoHideout

    return commands.check(predicate)


def hideout_only():
    def predicate(ctx: CustomContext):
        if ctx.guild and ctx.guild.id == DUCK_HIDEOUT:
            return True
        raise errors.NoHideout

    return commands.check(predicate)


class Hideout(commands.Cog, name="DuckBot Hideout"):
    """
    🧪 Test commands. 💀 These may not work, or not be what you think they will.
    Remember that these commands are all a work in progress, and they may or may not ever be released
    """

    def __init__(self, bot):
        self.bot: DuckBot = bot

    async def build_rtfm_lookup_table(self, page_types):
        cache = {}
        for key, page in page_types.items():
            sub = cache[key] = {}
            async with self.bot.session.get(page + "/objects.inv") as resp:
                if resp.status != 200:
                    channel = self.bot.get_channel(880181130408636456)
                    await channel.send(f"```py\nCould not create RTFM lookup table for {page}\n```")
                    continue

                stream = SphinxObjectFileReader(await resp.read())
                cache[key] = self.parse_object_inv(stream, page)

        self._rtfm_cache = cache

    def parse_object_inv(self, stream, url):
        # key: URL
        # n.b.: key doesn't have `discord` or `discord.ext.commands` namespaces
        result = {}

        # first line is version info
        inv_version = stream.readline().rstrip()

        if inv_version != "# Sphinx inventory version 2":
            raise RuntimeError("Invalid objects.inv file version.")

        # next line is "# Project: <name>"
        # then after that is "# Version: <version>"
        projname = stream.readline().rstrip()[11:]
        version = stream.readline().rstrip()[11:]

        # next line says if it's a zlib header
        line = stream.readline()
        if "zlib" not in line:
            raise RuntimeError("Invalid objects.inv file, not z-lib compatible.")

        # This code mostly comes from the Sphinx repository.
        entry_regex = re.compile(r"(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)")
        for line in stream.read_compressed_lines():
            match = entry_regex.match(line.rstrip())
            if not match:
                continue

            name, directive, prio, location, dispname = match.groups()
            domain, _, subdirective = directive.partition(":")
            if directive == "py:module" and name in result:
                # From the Sphinx Repository:
                # due to a bug in 1.1 and below,
                # two inventory entries are created
                # for Python modules, and the first
                # one is correct
                continue

            # Most documentation pages have a label
            if directive == "std:doc":
                subdirective = "label"

            if location.endswith("$"):
                location = location[:-1] + name

            key = name if dispname == "-" else dispname
            prefix = f"{subdirective}:" if domain == "std" else ""

            if projname == "discord.py":
                key = key.replace("discord.ext.commands.", "").replace("discord.", "")

            result[f"{prefix}{key}"] = os.path.join(url, location)

        return result

    async def do_rtfm(self, ctx, key, obj):
        page_types = {
            "stable": "https://discordpy.readthedocs.io/en/stable"
            "latest": "https://discordpy.readthedocs.io/en/latest",
            "latest-jp": "https://discordpy.readthedocs.io/ja/latest",
            "python": "https://docs.python.org/3",
            "python-jp": "https://docs.python.org/ja/3",
            "bing": "https://asyncbing.readthedocs.io/en/latest",
            "twitchio": "https://twitchio.readthedocs.io/en/latest/",
            "pomice": "https://pomice.readthedocs.io/en/latest/",
        }
        embed_titles = {
            "stable": "Documentation for `discord.py v1.7.3`",
            "latest-jp": "Documentation for `discord.py v2.0.0a` in Japanese",
            "python": "Documentation for `python`",
            "python-jp": "Documentation for `python` in Japanese",
            "latest": "Documentation for `discord.py v2.0.0a`",
            "bing": "Documentation for `asyncbing`",
            "twitchio": "Documentation for `twitchio`",
            "pomice": "Documentation for `pomice`",
        }

        if obj is None:
            await ctx.send(page_types[key])
            return

        if not hasattr(self, "_rtfm_cache"):
            await ctx.typing()
            await self.build_rtfm_lookup_table(page_types)

        obj = re.sub(r"^(?:discord\.(?:ext\.)?)?(?:commands\.)?(.+)", r"\1", obj)

        if key.startswith("latest"):
            # point the abc.Messageable types properly:
            q = obj.lower()
            for name in dir(discord.abc.Messageable):
                if name[0] == "_":
                    continue
                if q == name:
                    obj = f"abc.Messageable.{name}"
                    break

        cache = list(self._rtfm_cache[key].items())

        matches = finder(obj, cache, key=lambda t: t[0], lazy=False)[:8]

        e = discord.Embed(
            colour=discord.Colour.blurple(),
            title=embed_titles.get(key, "Documentation"),
        )
        if len(matches) == 0:
            return await ctx.send("Could not find anything. Sorry.")

        e.description = "\n".join(f"[`{key}`]({url})" for key, url in matches)
        await ctx.send(embed=e)

    @commands.group(aliases=["rtfd", "rtdm"], invoke_without_command=True)
    async def rtfm(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a discord.py entity.
        Events, objects, and functions are all supported through
        a cruddy fuzzy algorithm.

        https://discordpy.readthedocs.io/en/stable
        """
        await self.do_rtfm(ctx, "stable", obj)

    @rtfm.command(name="jp")
    async def rtfm_jp(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a discord.py entity (Japanese).

        https://discordpy.readthedocs.io/ja/latest
        """
        await self.do_rtfm(ctx, "latest-jp", obj)

    @rtfm.command(name="python", aliases=["py"])
    async def rtfm_python(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a Python entity.

        https://docs.python.org/3
        """
        await self.do_rtfm(ctx, "python", obj)

    @rtfm.command(name="py-jp", aliases=["py-ja"])
    async def rtfm_python_jp(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a Python entity (Japanese).

        https://docs.python.org/ja/3
        """
        await self.do_rtfm(ctx, "python-jp", obj)

    @rtfm.command(name="latest", aliases=["2.0", "master"])
    async def rtfm_latest(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a discord.py entity (master branch)

        https://discordpy.readthedocs.io/en/latest
        """
        await self.do_rtfm(ctx, "latest", obj)

    @rtfm.command(name="asyncbing", aliases=["bing"])
    async def rtfm_asyncbing(self, ctx, *, obj: str = None):
        """Gives you a documentation link for an asyncbing entity

        https://asyncbing.readthedocs.io/en/latest
        """
        await self.do_rtfm(ctx, "bing", obj)

    @rtfm.command(name="twitchio")
    async def rtfm_twitchio(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a TwitchIO entry

        https://twitchio.readthedocs.io/en/latest

        """
        await self.do_rtfm(ctx, "twitchio", obj)

    @rtfm.command(name="pomice")
    async def rtfm_pomice(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a Pomice entry

        https://pomice.readthedocs.io/en/latest
        """
        await self.do_rtfm(ctx, "pomice", obj)

    @commands.command(name="impersonate", aliases=["webhook-send", "wh-send", "say-as"])
    @commands.bot_has_permissions(manage_webhooks=True)
    async def send_as_others(self, ctx: CustomContext, member: discord.Member, *, message):
        """Sends a message as another person."""
        if len(message) > 2000:
            raise commands.BadArgument(f"Message too long! {len(message)}/2000")
        wh = await get_webhook(ctx.channel)
        thread = discord.utils.MISSING
        if isinstance(ctx.channel, discord.Thread):
            thread = ctx.channel
        await wh.send(
            message,
            avatar_url=member.display_avatar.url,
            username=member.display_name,
            thread=thread,
        )
        await ctx.message.delete(delay=0)

    @commands.command(name="raw-message", aliases=["rmsg", "raw"])
    @commands.cooldown(rate=1, per=40, type=commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    async def raw_message(self, ctx: CustomContext, message: typing.Optional[discord.Message]):
        async with ctx.typing():
            message: discord.Message = getattr(ctx.message.reference, "resolved", message)
            if not message:
                raise commands.BadArgument("You must specify a message, or quote (reply to) one.")
            try:
                data = await self.bot.http.get_message(message.channel.id, message.id)
            except discord.HTTPException:
                raise commands.BadArgument("There was an error retrieving that message.")
            pretty_data = json.dumps(data, indent=4)
            if len(pretty_data) > 1990:
                gist = await self.bot.create_gist(
                    filename="raw_message.json",
                    description="Raw Message created by DuckBot",
                    content=pretty_data,
                )
                to_send = f"**Output too long:**\n<{gist}>"
            else:
                to_send = f"```json\n{pretty_data}\n```"
            return await ctx.send(to_send, reference=ctx.message)

    @commands.command()
    async def credits(self, ctx: CustomContext):
        embed = discord.Embed(
            description="**You copied something from my bad source code?**"
            "\nYou **don't need to credit me** in a command, don't"
            "\nworry. Although if you wish to do so, you can"
            "\nadd credits in the source code. ([Mozilla Public"
            "\nLicense](https://github.com/LeoCx1000/discord-bots/blob"
            "/master/LICENSE) btw one of the terms is to use the same for"
            "\nyour project). Just add a comment or something in"
            "\nthere saying where the code came from."
            "\nThe latter also being optional, of course."
            "\n(I don't know the legalities of the Mozilla Public "
            "\nLicense so this is not legal advice in any way.)"
            "\n"
            "\n**As for why I don't have a proper credits command?**"
            "\nI don't see the need to. I don't expect others to"
            "\ngive me credits. It's all up to them, and well,"
            "\nunder that same reasoning I don't add any credits"
            "\nhere. It's also because I (the developer of DuckBot)"
            "\nI'm an idiot, and I can't remember every person who"
            "\nhelped me, so as to not offend anyone I'd rather"
            "\njust not add a credits command."
            "\nOf course if you want to get credit because you"
            "\nhelped me, or because I took a snippet off your"
            "\ncode, let me know and I will gladly add a note"
            "\nin said command giving proper credits to your"
            "\nrepository 😊 Just that I can't remember anyone."
            "\n"
            "\n(Some users will show a small acknowledgement in the"
            "\nuser-info command if they did something remarkable)",
            title="Why no credits?",
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        if not isinstance(channel, discord.VoiceChannel):
            return
        query = "SELECT * FROM inviter WHERE guild_id = $1"
        if query := await self.bot.db.fetchrow(query, channel.guild.id):
            if channel.category_id == query["category"]:
                if send_to := self.bot.get_channel(query["text_channel"]):
                    invite = await channel.create_invite(max_age=3600 * 24)
                    message = await send_to.send(invite.url)
                    await self.bot.db.execute(
                        "INSERT INTO voice_channels(channel_id, message_id) " "VALUES ($1, $2)",
                        channel.id,
                        message.id,
                    )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if not isinstance(channel, discord.VoiceChannel):
            return
        query = "SELECT * FROM inviter WHERE guild_id = $1"
        if query := await self.bot.db.fetchrow(query, channel.guild.id):
            if channel.category_id == query["category"]:
                if delete_from := self.bot.get_channel(query["text_channel"]):
                    query = "SELECT message_id FROM voice_channels WHERE channel_id = $1"
                    if msg_id := await self.bot.db.fetchval(query, channel.id):
                        message = delete_from.get_partial_message(msg_id)
                        try:
                            await message.delete()
                        except discord.HTTPException:
                            pass

    @commands.group(invoke_without_command=True)
    @whitelist()
    async def inviter(self, ctx):
        """You probably are not whitelisted to see this!"""
        pass

    @commands.guild_only()
    @whitelist()
    @inviter.command(name="set")
    async def set_inviter(
        self,
        ctx: CustomContext,
        category: discord.CategoryChannel,
        text_channel: discord.TextChannel,
    ):
        await self.bot.db.execute(
            "INSERT INTO inviter(guild_id, category, text_channel) VALUES ($1, $2, $3) "
            "ON CONFLICT (guild_id) DO UPDATE SET "
            "category = $2, "
            "text_channel = $3;",
            ctx.guild.id,
            category.id,
            text_channel.id,
        )
        await ctx.message.add_reaction("✅")

    @commands.guild_only()
    @whitelist()
    @inviter.command(name="unset")
    async def unset_inviter(self, ctx: CustomContext):
        await self.bot.db.execute("DELETE FROM inviter WHERE guild_id = $1;", ctx.guild.id)
        await ctx.message.add_reaction("✅")

    @commands.is_owner()
    @inviter.group(name="w")
    async def inviter_whitelist(self, ctx):
        """To allow only some people to run the command."""
        pass

    @commands.is_owner()
    @inviter_whitelist.command(name="a")
    async def whitelist_add(self, ctx: CustomContext, user: discord.User):
        await self.bot.db.execute(
            "INSERT INTO inv_whitelist(uid) VALUES ($1) " "ON CONFLICT (uid) DO NOTHING",
            user.id,
        )
        await ctx.message.add_reaction("✅")

    @commands.is_owner()
    @inviter_whitelist.command(name="r")
    async def whitelist_rem(self, ctx: CustomContext, user: discord.User):
        await self.bot.db.execute("DELETE FROM inv_whitelist WHERE uid = $1", user.id)
        await ctx.message.add_reaction("✅")

    @commands.is_owner()
    @commands.command(name="guild-stats")
    async def _guilds(self, ctx: CustomContext, send_in_channel: bool = False):
        """Shows non-sensitive member count data about the bots guilds."""
        pages = WrappedPaginator(max_size=4096)
        title = (f"--- {ctx.me.name} ---", "All guild stats", "")
        for entr in title:
            pages.add_line(entr)

        total_per = 0
        total_users = 0
        total_bot = 0
        total_human = 0

        for n, g in enumerate(
            sorted(self.bot.guilds, key=lambda gu: gu.member_count, reverse=True),
            start=1,
        ):
            bots = sum(m.bot for m in g.members)
            humans = sum(not m.bot for m in g.members)
            bot_per = bots / g.member_count
            total_per += bot_per
            total_users += g.member_count
            total_bot += bots
            total_human += humans
            pages.add_line(
                f"{n}) Total: {g.member_count} - {math.ceil(bot_per * 100)}% bots"
                f"\n{'-' * len(str(n))}- Humans: {humans} - Bots: {bots}\n"
            )

        avg_per = (total_per / len(self.bot.guilds)) * 100
        footer = [
            "",
            f"Total users: {total_users}",
            f"Average {math.ceil(avg_per)}% bot",
            f"Total human: {total_human}",
            f"Total bot: {total_bot}",
        ]

        for entr in footer:
            pages.add_line(entr)

        if not send_in_channel:
            await ctx.send("📩 DMing you guild stats...")

        for p in pages.pages:
            destination = ctx.channel if send_in_channel else ctx.author
            embed = discord.Embed(description=p, color=discord.Color.blue())
            await destination.send(embed=embed)
