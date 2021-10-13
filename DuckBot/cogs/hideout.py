import io
import json
import os
import re
import urllib
import zlib
from inspect import Parameter

import discord
import typing
import yarl
from discord.ext import commands

from DuckBot import errors
from DuckBot.__main__ import DuckBot
from DuckBot.cogs.management import get_webhook
from DuckBot.helpers.context import CustomContext


def hideout_only():
    def predicate(ctx: CustomContext):
        if ctx.guild.id == 774561547930304536:
            return True
        else:
            raise errors.NoHideout

    return commands.check(predicate)


url_regex = re.compile(r"^http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|)+$")


def setup(bot):
    bot.add_cog(Hideout(bot))


def finder(text, collection, *, key=None, lazy=True):
    suggestions = []
    text = str(text)
    pat = '.*?'.join(map(re.escape, text))
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
        return self.stream.readline().decode('utf-8')

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
        buf = b''
        for chunk in self.read_compressed_chunks():
            buf += chunk
            pos = buf.find(b'\n')
            while pos != -1:
                yield buf[:pos].decode('utf-8')
                buf = buf[pos + 1:]
                pos = buf.find(b'\n')


class Hideout(commands.Cog, name='DuckBot Hideout'):
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
            async with self.bot.session.get(page + '/objects.inv') as resp:
                if resp.status != 200:
                    raise RuntimeError('Cannot build rtfm lookup table, try again later.')

                stream = SphinxObjectFileReader(await resp.read())
                cache[key] = self.parse_object_inv(stream, page)

        self._rtfm_cache = cache

    def parse_object_inv(self, stream, url):
        # key: URL
        # n.b.: key doesn't have `discord` or `discord.ext.commands` namespaces
        result = {}

        # first line is version info
        inv_version = stream.readline().rstrip()

        if inv_version != '# Sphinx inventory version 2':
            raise RuntimeError('Invalid objects.inv file version.')

        # next line is "# Project: <name>"
        # then after that is "# Version: <version>"
        projname = stream.readline().rstrip()[11:]
        version = stream.readline().rstrip()[11:]

        # next line says if it's a zlib header
        line = stream.readline()
        if 'zlib' not in line:
            raise RuntimeError('Invalid objects.inv file, not z-lib compatible.')

        # This code mostly comes from the Sphinx repository.
        entry_regex = re.compile(r'(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)')
        for line in stream.read_compressed_lines():
            match = entry_regex.match(line.rstrip())
            if not match:
                continue

            name, directive, prio, location, dispname = match.groups()
            domain, _, subdirective = directive.partition(':')
            if directive == 'py:module' and name in result:
                # From the Sphinx Repository:
                # due to a bug in 1.1 and below,
                # two inventory entries are created
                # for Python modules, and the first
                # one is correct
                continue

            # Most documentation pages have a label
            if directive == 'std:doc':
                subdirective = 'label'

            if location.endswith('$'):
                location = location[:-1] + name

            key = name if dispname == '-' else dispname
            prefix = f'{subdirective}:' if domain == 'std' else ''

            if projname == 'discord.py':
                key = key.replace('discord.ext.commands.', '').replace('discord.', '')

            result[f'{prefix}{key}'] = os.path.join(url, location)

        return result

    async def do_rtfm(self, ctx, key, obj):
        page_types = {
            'latest': 'https://discordpy.readthedocs.io/en/latest',
            'latest-jp': 'https://discordpy.readthedocs.io/ja/latest',
            'python': 'https://docs.python.org/3',
            'python-jp': 'https://docs.python.org/ja/3',
            'master': 'https://discordpy.readthedocs.io/en/master',
        }

        if obj is None:
            await ctx.send(page_types[key])
            return

        if not hasattr(self, '_rtfm_cache'):
            await ctx.trigger_typing()
            await self.build_rtfm_lookup_table(page_types)

        obj = re.sub(r'^(?:discord\.(?:ext\.)?)?(?:commands\.)?(.+)', r'\1', obj)

        if key.startswith('latest'):
            # point the abc.Messageable types properly:
            q = obj.lower()
            for name in dir(discord.abc.Messageable):
                if name[0] == '_':
                    continue
                if q == name:
                    obj = f'abc.Messageable.{name}'
                    break

        cache = list(self._rtfm_cache[key].items())

        matches = finder(obj, cache, key=lambda t: t[0], lazy=False)[:8]

        e = discord.Embed(colour=discord.Colour.blurple())
        if len(matches) == 0:
            return await ctx.send('Could not find anything. Sorry.')

        e.description = '\n'.join(f'[`{key}`]({url})' for key, url in matches)
        await ctx.send(embed=e)

    def transform_rtfm_language_key(self, ctx, prefix):
        if ctx.guild is not None:
            #                             日本語 category
            if ctx.channel.category_id == 490287576670928914:
                return prefix + '-jp'
            #                    d.py unofficial JP   Discord Bot Portal JP
            elif ctx.guild.id in (463986890190749698, 494911447420108820):
                return prefix + '-jp'
        return prefix

    @commands.group(aliases=['rtfd'], invoke_without_command=True)
    async def rtfm(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a discord.py entity.
        Events, objects, and functions are all supported through
        a cruddy fuzzy algorithm.
        """
        key = self.transform_rtfm_language_key(ctx, 'latest')
        await self.do_rtfm(ctx, key, obj)

    @rtfm.command(name='jp')
    async def rtfm_jp(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a discord.py entity (Japanese)."""
        await self.do_rtfm(ctx, 'latest-jp', obj)

    @rtfm.command(name='python', aliases=['py'])
    async def rtfm_python(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a Python entity."""
        key = self.transform_rtfm_language_key(ctx, 'python')
        await self.do_rtfm(ctx, key, obj)

    @rtfm.command(name='py-jp', aliases=['py-ja'])
    async def rtfm_python_jp(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a Python entity (Japanese)."""
        await self.do_rtfm(ctx, 'python-jp', obj)

    @rtfm.command(name='master', aliases=['2.0'])
    async def rtfm_master(self, ctx, *, obj: str = None):
        """Gives you a documentation link for a discord.py entity (master branch)"""
        await self.do_rtfm(ctx, 'master', obj)

    @commands.command()
    @hideout_only()
    async def addbot(self, ctx: CustomContext, bot: discord.User, *, reason: commands.clean_content):
        bot_queue = self.bot.get_channel(870784166705393714)
        if not bot.bot:
            raise commands.BadArgument('That dos not seem to be a bot...')
        if bot in ctx.guild.members:
            raise commands.BadArgument('That bot is already on this server...')
        confirm = await ctx.confirm(
            f'Does your bot comply with {ctx.guild.rules_channel.mention if ctx.guild.rules_channel else "<channel deleted?>"}?'
            f'\n If so, press one of these:', return_message=True)
        if confirm[0]:
            await confirm[1].edit(content='✅ Done, you will be @pinged when the bot is added!', view=None)
            embed = discord.Embed(description=reason)
            embed.set_author(icon_url=bot.display_avatar.url, name=str(bot), url=discord.utils.oauth_url(bot.id))
            embed.set_footer(text=f"Requested by {ctx.author} ({ctx.author.id})")
            await bot_queue.send(embed=embed)
        else:
            await confirm[1].edit(content='Aborting...', view=None)

    @commands.command(name='decode-qr-code', aliases=['qr-decode', 'decode-qr', 'qr'])
    @commands.cooldown(2, 30, commands.BucketType.user)
    async def decode_qr_code(self, ctx: CustomContext, *, qr_code: typing.Optional[
        typing.Union[discord.Member,
                     discord.User,
                     discord.PartialEmoji,
                     discord.Guild,
                     discord.Invite, str]
    ]):
        """
        Attempts to decode a QR code
        Can decode from the following:
          - A direct URL to an image
          - An Emoji
          - A user's profile picture
          - A server icon:
            - from an ID/name (if the bot is in that server)
            - from an invite URL (if the bot is not in the server)
          - Others? Will attempt to decode if a link is passed.
        """
        if qr_code is None:
            if ctx.message.attachments:
                qr_code = ctx.message.attachments[0]
            elif ctx.message.stickers:
                qr_code = ctx.message.stickers[0].url
            elif ctx.message.reference:
                if ctx.message.reference.resolved.attachments:
                    qr_code = ctx.message.reference.resolved.attachments[0]
                elif ctx.message.reference.resolved.embeds:
                    if ctx.message.reference.resolved.embeds[0].thumbnail:
                        qr_code = ctx.message.reference.resolved.embeds[0].thumbnail.proxy_url
                    elif ctx.message.reference.resolved.embeds[0].image:
                        qr_code = ctx.message.reference.resolved.embeds[0].image.proxy_url
        if not qr_code:
            raise commands.MissingRequiredArgument(Parameter(name='qr_code', kind=Parameter.POSITIONAL_ONLY))

        async with ctx.typing():
            link = getattr(qr_code, 'avatar', None) \
                   or getattr(qr_code, 'icon', None) \
                   or getattr(qr_code, 'guild', None) \
                   or qr_code
            link = getattr(getattr(link, 'icon', link), 'url', link)
            if url_regex.match(link):
                url = urllib.parse.quote(link, safe='')
                async with self.bot.session.get(
                        yarl.URL(f"http://api.qrserver.com/v1/read-qr-code/?fileurl={url}", encoded=True)) as r:
                    if r.status == 200:
                        data = await r.json()
                        if data[0]['symbol'][0]['data'] is None:
                            raise commands.BadArgument(data[0]['symbol'][0]['error'])
                        embed = discord.Embed(title='I found the following data:',
                                              description=data[0]['symbol'][0]['data'])
                        embed.set_thumbnail(url=link)
                        await ctx.send(embed=embed)
                    else:
                        raise commands.BadArgument(f'API failed with status {r.status}')
            else:
                raise commands.BadArgument('No URL was found')

    @commands.command(name='impersonate', aliases=['webhook-send', 'wh-send', 'say-as'])
    @commands.bot_has_permissions(manage_webhooks=True)
    async def send_as_others(self, ctx: CustomContext, member: discord.Member, *, message):
        """ Sends a message as another person. """
        results = re.findall(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|)+", message)  # HTTP/HTTPS URL regex
        results2 = re.findall(r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?", message)  # Discord invite regex
        if results or results2:
            await ctx.send(f"hey, {ctx.author.mention}. Urls or invites aren't allowed!", delete_after=10)
        wh: discord.Webhook = await get_webhook(ctx.channel)
        await wh.send(message, avatar_url=member.display_avatar.url, username=member.display_name)
        await ctx.message.delete(delay=0)

    @commands.command(name='raw-message', aliases=['rmsg', 'raw'])
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @commands.max_concurrency(1, commands.BucketType.user)
    async def raw_message(self, ctx: CustomContext, message: typing.Optional[discord.Message]):
        async with ctx.typing():
            message: discord.Message = getattr(ctx.message.reference, 'resolved', message)
            if not message:
                raise commands.BadArgument('You must specify a message, or quote (reply to) one.')
            try:
                data = await self.bot.http.get_message(message.channel.id, message.id)
            except discord.HTTPException:
                raise commands.BadArgument('There was an error retrieving that message.')
            pretty_data = json.dumps(data, indent=4)
            if len(pretty_data) > 1990:
                gist = await self.bot.create_gist(filename='raw_message.json', description='Raw Message created by DuckBot', content=pretty_data)
                to_send = f"<{gist}>"
            else:
                to_send = f"```json\n{pretty_data}\n```"
            return await ctx.send(to_send)
