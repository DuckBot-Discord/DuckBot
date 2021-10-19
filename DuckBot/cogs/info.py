import aiohttp
import asyncio
import discord
import inspect
import os
import pkg_resources
import psutil
import re
import time

import typing
from discord.ext import commands

from DuckBot.__main__ import DuckBot, CustomContext
from DuckBot.helpers import paginator, constants, helper

suggestions_channel = 882634213516521473


def setup(bot):
    bot.add_cog(About(bot))


class MyHelp(commands.HelpCommand):
    def __init__(self, **options):
        super().__init__(**options)
        self.context: CustomContext

    def get_bot_mapping(self):
        """Retrieves the bot mapping passed to :meth:`send_bot_help`."""
        bot = self.context.bot
        mapping = {cog: cog.get_commands() for cog in
                   sorted(bot.cogs.values(), key=lambda c: len(c.get_commands()), reverse=True)}
        mapping[None] = [c for c in bot.commands if c.cog is None]
        return mapping

    # Formatting
    def get_minimal_command_signature(self, command):
        if isinstance(command, commands.Group):
            return '[G] %s%s %s' % (self.context.clean_prefix, command.qualified_name, command.signature)
        return '(c) %s%s %s' % (self.context.clean_prefix, command.qualified_name, command.signature)

    @staticmethod
    def get_command_name(command):
        return '%s' % command.qualified_name

    # !help
    async def send_bot_help(self, mapping):
        data = []
        ignored_cogs = ['Jishaku', 'Events', 'Handler', 'Bot Management', 'DuckBot Hideout']
        for cog, cog_commands in mapping.items():

            if cog is None or cog.qualified_name in ignored_cogs:
                continue
            command_signatures = [self.get_minimal_command_signature(c) for c in cog_commands]
            if command_signatures:
                val = cog.description + '```css\n' + "\n".join(command_signatures) + '\n```'
                info = ('Category: ' + cog.qualified_name, f'{val}')

                data.append(info)

        source = paginator.HelpMenuPageSource(data=data, ctx=self.context, help_class=self)
        menu = paginator.ViewPaginator(source=source, ctx=self.context, compact=True)
        await menu.start()

    def common_command_formatting(self, embed_like, command):
        embed_like.title = self.get_command_signature(command)
        if command.description:
            embed_like.description = f'{command.description}\n\n```yaml\n{command.help}\n```'
        else:
            embed_like.description = command.help or '```yaml\nNo help found...\n```'

    # !help <command>
    async def send_command_help(self, command: commands.Command):
        embed = discord.Embed(title=f"information about: `{self.context.clean_prefix}{command}`",
                              description='**Description:**\n' + (command.help or 'No help given...').replace('%PRE%', self.context.clean_prefix))
        embed.add_field(name='Command usage:', value=f"```css\n{self.get_minimal_command_signature(command)}\n```")
        if command.aliases:
            embed.description = embed.description + f'\n\n**Aliases:**\n`{"`, `".join(command.aliases)}`'
        try:
            await command.can_run(self.context)
        except commands.MissingPermissions as error:
            embed.add_field(name='Permissions you\'re missing:', value=', '.join(error.missing_permissions).replace('_', ' ').replace('guild', 'server').title(), inline=False)
        except commands.BotMissingPermissions as error:
            embed.add_field(name='Permissions i\'m missing:', value=', '.join(error.missing_permissions).replace('_', ' ').replace('guild', 'server').title(), inline=False)
        else:
            pass
        await self.context.send(embed=embed, footer=False)

    async def send_cog_help(self, cog):
        entries = cog.get_commands()
        menu = paginator.ViewPaginator(paginator.GroupHelpPageSource(cog, entries, prefix=self.context.clean_prefix),
                                       ctx=self.context, compact=True)
        await menu.start()

    async def send_group_help(self, group):
        embed = discord.Embed(title=f"information about: `{self.context.clean_prefix}{group}`",
                              description='**Description:**\n' + (group.help or 'No help given...').replace('%PRE%', self.context.clean_prefix))
        embed.add_field(name='Command usage:', value=f"```css\n{self.get_minimal_command_signature(group)}\n```")
        if group.aliases:
            embed.description = embed.description + f'\n\n**Aliases:**\n`{"`, `".join(group.aliases)}`'
        # noinspection PyBroadException
        try:
            await group.can_run(self.context)
        except commands.MissingPermissions as error:
            embed.add_field(name='Permissions you\'re missing:', value=', '.join(error.missing_permissions).replace('_', ' ').replace('guild', 'server').title(), inline=False)
        except commands.BotMissingPermissions as error:
            embed.add_field(name='Permissions i\'m missing:', value=', '.join(error.missing_permissions).replace('_', ' ').replace('guild', 'server').title(), inline=False)
        except:
            pass

        if group.commands:
            formatted = '\n'.join([self.get_minimal_command_signature(c) for c in group.commands])
            embed.add_field(name='Sub-commands for this group:', value=f'```css\n{formatted}\n```**Do `{self.context.clean_prefix}help command subcommand` for more info on a sub-command**', inline=False)

        await self.context.send(embed=embed)

    async def send_error_message(self, error):
        await self.context.send(f"{error}"
                                f"\nDo `{self.context.clean_prefix}help` for a list of available commands! 💞")

    async def on_help_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(embed=discord.Embed(description=str(error.original)))


class About(commands.Cog):
    """
    😮 Commands related to the bot itself, that have the only purpose to show information.
    """

    def __init__(self, bot):
        self.bot: DuckBot = bot
        help_command = MyHelp()
        help_command.cog = self
        bot.help_command = help_command
        bot.session = aiohttp.ClientSession()

    @commands.Cog.listener('on_ready')
    async def register_views(self):
        if not self.bot.persistent_views_added:
            self.bot.add_view(paginator.InvSrc())
            self.bot.add_view(paginator.OzAd())
            self.bot.persistent_views_added = True

    def get_bot_uptime(self):
        return f"<t:{round(self.bot.uptime.timestamp())}:R>"

    def get_bot_last_rall(self):
        return f"<t:{round(self.bot.last_rall.timestamp())}:R>"

    @commands.command(help="Sends a link to invite the bot to your server")
    async def invite(self, ctx):
        await ctx.send(
            embed=discord.Embed(description=f"{constants.INVITE} **[invite me]({self.bot.invite_url})**"),
            view=paginator.InvMe())

    @commands.command(help="Checks the bot's ping to Discord")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def ping(self, ctx):
        pings = []
        number = 0

        typing_start = time.monotonic()
        await ctx.trigger_typing()
        typing_end = time.monotonic()
        typing_ms = (typing_end - typing_start) * 1000
        pings.append(typing_ms)

        start = time.perf_counter()
        message = await ctx.send("🏓 pong!")
        end = time.perf_counter()
        message_ms = (end - start) * 1000
        pings.append(message_ms)

        latency_ms = self.bot.latency * 1000
        pings.append(latency_ms)

        postgres_start = time.perf_counter()
        await self.bot.db.fetch("SELECT 1")
        postgres_end = time.perf_counter()
        postgres_ms = (postgres_end - postgres_start) * 1000
        pings.append(postgres_ms)

        for ms in pings:
            number += ms
        average = number / len(pings)

        await asyncio.sleep(0.7)

        await message.edit(content=re.sub('\n *', '\n',
                                          f"\n{constants.WEBSITE} **| `Websocket ═╣ "
                                          f"{round(latency_ms, 3)}ms{' ' * (9 - len(str(round(latency_ms, 3))))}`** "
                                          f"\n{constants.TYPING_INDICATOR} **| `Typing ════╣ "
                                          f"{round(typing_ms, 3)}ms{' ' * (9 - len(str(round(typing_ms, 3))))}`**"
                                          f"\n:speech_balloon: **| `Message ═══╣ "
                                          f"{round(message_ms, 3)}ms{' ' * (9 - len(str(round(message_ms, 3))))}`**"
                                          f"\n{constants.POSTGRE_LOGO} **| `Database ══╣ "
                                          f"{round(postgres_ms, 3)}ms{' ' * (9 - len(str(round(postgres_ms, 3))))}`**"
                                          f"\n:infinity: **| `Average ═══╣ "
                                          f"{round(average, 3)}ms{' ' * (9 - len(str(round(average, 3))))}`**"))

    @commands.command(help="Shows info about the bot", aliases=['info'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def about(self, ctx):
        """Tells you information about the bot itself."""
        information = await self.bot.application_info()
        embed = discord.Embed(description=f"{constants.GITHUB} [source]({self.bot.repo}) | "
                                          f"{constants.INVITE} [invite me]({self.bot.invite_url}) | "
                                          f"{constants.TOP_GG} [top.gg]({self.bot.vote_top_gg}) | "
                                          f"{constants.BOTS_GG} [bots.gg]({self.bot.vote_bots_gg})"
                                          f"\n> Try also `{ctx.prefix}source [command]`")

        embed.set_author(name=f"Made by {information.owner}", icon_url=information.owner.display_avatar.url)
        # statistics
        total_members = 0
        total_unique = len(self.bot.users)

        text = 0
        voice = 0
        guilds = 0
        for guild in self.bot.guilds:
            guilds += 1
            if guild.unavailable:
                continue

            total_members += guild.member_count
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    text += 1
                elif isinstance(channel, discord.VoiceChannel):
                    voice += 1
        avg = [(sum(m.bot for m in g.members) / g.member_count) * 100 for g in self.bot.guilds]

        embed.add_field(name='Members', value=f'{total_members} total\n{total_unique} unique')
        embed.add_field(name='Channels', value=f'{text + voice} total\n{text} text\n{voice} voice')

        memory_usage = psutil.Process().memory_full_info().uss / 1024 ** 2
        cpu_usage = psutil.cpu_percent()

        embed.add_field(name='Process', value=f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU')
        embed.add_field(name='Bot servers',
                        value=f"**total servers:** {guilds}\n**avg bot/human:** {round(sum(avg) / len(avg), 2)}%")
        embed.add_field(name='Command info:',
                        value=f"**Last reboot:**\n{self.get_bot_uptime()}"
                              f"\n**Last command reload:**\n{self.get_bot_last_rall()}")

        version = pkg_resources.get_distribution('discord.py').version
        embed.set_footer(text=f'Made with discord.py v{version} 💖', icon_url='http://i.imgur.com/5BFecvA.png')
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)

    @commands.command(aliases=['sourcecode', 'code'],
                      usage="[command|command.subcommand]")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def source(self, ctx, *, command: str = None):
        """
        Links to the bot's code, or a specific command's
        """
        global obj
        source_url = 'https://github.com/LeoCx1000/discord-bots'
        branch = 'master'
        license_url = f'{source_url}/blob/{branch}/LICENSE'
        mpl_advice = f'**This code is licensed under [MPL]({license_url})**' \
                     f'\nRemember that you must use the ' \
                     f'\nsame license! [[read more]]({license_url}#L160-L168)'
        obj = None

        if command is None:
            embed = discord.Embed(title=f'Here\'s my source code.',
                                  description=mpl_advice)
            embed.set_image(
                url='https://cdn.discordapp.com/attachments/879251951714467840/896445332509040650/unknown.png')
            return await ctx.send(embed=embed,
                                  view=helper.Url(source_url, label='Open on GitHub', emoji=constants.GITHUB),
                                  footer=False)

        if command == 'help':
            src = type(self.bot.help_command)
            module = src.__module__
            filename = inspect.getsourcefile(src)
        else:
            obj = self.bot.get_command(command.replace('.', ' '))
            if obj is None:
                embed = discord.Embed(title=f'Couldn\'t find command.',
                                      description=mpl_advice)
                embed.set_image(
                    url='https://cdn.discordapp.com/attachments/879251951714467840/896445332509040650/unknown.png')
                return await ctx.send(embed=embed,
                                      view=helper.Url(source_url, label='Open on GitHub', emoji=constants.GITHUB),
                                      footer=False)

            src = obj.callback.__code__
            module = obj.callback.__module__
            filename = src.co_filename

        lines, firstlineno = inspect.getsourcelines(src)
        if not module.startswith('discord'):
            # not a built-in command
            location = os.path.relpath(filename).replace('\\', '/')
        else:
            location = module.replace('.', '/') + '.py'
            source_url = 'https://github.com/Rapptz/discord.py'
            branch = 'master'

        final_url = f'{source_url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}'
        embed = discord.Embed(title=f'Here\'s `{str(obj)}`',
                              description=mpl_advice)
        embed.set_image(url='https://cdn.discordapp.com/attachments/879251951714467840/896445332509040650/unknown.png')
        embed.set_footer(text=f"{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}")
        await ctx.send(embed=embed, view=helper.Url(final_url, label=f'Here\'s {str(obj)}', emoji=constants.GITHUB),
                       footer=False)

    @commands.command(description="hiii")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def privacy(self, ctx):
        """
        Shows duckbot's privacy policies
        """
        embed = discord.Embed(title=f'{ctx.me.name} Privacy Policy', description=f"""
> We store your `server id` for purpose of custom prefixes.

> We store role_IDs for mute-role

> We store user_IDs for AFK / temporary mutes

> when a command error happens, we get the following data for troubleshooting purposes:
```yaml
The command executed
The server id, and server owner id
DuckBot's top role position
# This data is disposed of once
# the error has been fixed.
```""",
                              color=ctx.me.color)
        embed.set_footer(text='Privacy concerns, DM the bot.')
        await ctx.send(embed=embed)

    @commands.command()
    async def suggest(self, ctx: CustomContext, *, suggestion):
        channel = self.bot.get_channel(suggestions_channel)
        embed = discord.Embed(colour=ctx.me.color,
                              title="Suggestion successful!")
        embed.add_field(name="Thank you!", value="Your suggestion has been sent to the moderators of duckbot! "
                                                 "You will receive a Direct Message if your suggestion gets "
                                                 "approved. Keep your DMs with me open 💞")
        embed.add_field(name="Your suggestion:", value=f"```\n{suggestion}\n```")
        embed2 = discord.Embed(colour=ctx.me.color,
                               title=f"Suggestion from {ctx.author}",
                               description=f"```\n{suggestion}\n```")
        embed2.set_footer(text=f"Sender ID: {ctx.author.id}")

        if ctx.message.attachments:
            file = ctx.message.attachments[0]
            spoiler = file.is_spoiler()
            if not spoiler and file.url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
                embed.set_image(url=file.url)
                embed2.set_image(url=file.url)
            elif spoiler:
                embed.add_field(name='Attachment', value=f'||[{file.filename}]({file.url})||', inline=False)
                embed2.add_field(name='Attachment', value=f'||[{file.filename}]({file.url})||', inline=False)
            else:
                embed.add_field(name='Attachment', value=f'[{file.filename}]({file.url})', inline=False)
                embed2.add_field(name='Attachment', value=f'[{file.filename}]({file.url})', inline=False)

        message = await channel.send(embed=embed2)
        await ctx.send(embed=embed)
        await message.add_reaction('🔼')
        await message.add_reaction('🔽')

    @commands.command()
    async def news(self, ctx: CustomContext):
        """
        Shows the latest changes of the bot. ""
        """
        embed = discord.Embed(title="📰 Latest News - <t:1634379000:d> (<t:1634379000:R>)",
                              description=f"\u200b"
                                          f"\n> **#\️⃣ <t:1633210000:R> You're now able to play Tic-Tac-Toe**"
                                          f"\n> Just run the `{ctx.clean_prefix}ttt` command. Other users will be able to join your game by "
                                          f"pressing the 'Join this game!' button \🎫"
                                          f"\n"
                                          f"\n> **\✌ <t:1633110000:R> You're now able to play Rock-Paper-Scissors**"
                                          f"\n> Just run the `{ctx.clean_prefix}rps` command. Other users will be able to join your game by "
                                          f"pressing the 'Join this game!' button \🎫"
                                          f"\n"
                                          f"\n> **\🔇 <t:1633447880:R> New `multi-mute` and `multi-unmute` commands**"
                                          f"\n> Mute multiple people at once: `{ctx.clean_prefix}multi-mute @u1 @u2 @u3... reason`"
                                          f"\n"
                                          f"\n> **\👥 <t:1633642000:R> New `mutual-servers` command**"
                                          f"\n"
                                          f"\n> **\🎉 <t:1633753000:R> Improved upon the invitestats command**"
                                          f"\n"
                                          f"\n> **\📜 <t:1633848000:R> New `todo` command**"
                                          f"\n> _save things for later! don't forget about anything anymore._"
                                          f"\n"
                                          f"\n>  **\⛔ <t:1633908200:R> `block` and `unblock` commands**"
                                          f"\n> Block troublesome people from messaging in your current channel"
                                          f"\n"
                                          f"\n> **\🔢 <t:1634379000:R> NEW COUNTING GAME!!!**"
                                          f"\n> Run `{ctx.clean_prefix}counting` for more info!")
        await ctx.send(embed=embed, footer=None)

    @commands.command(hidden=True)
    async def oz_ad(self, ctx):
        embed = discord.Embed(title="Here's a cool minecraft server!",
                              description="Press the button for more info.")
        await ctx.send(embed=embed, view=paginator.OzAd(), footer=False)

    @commands.command(name='mutual-servers', aliases=['servers', 'mutual'])
    async def mutual_servers(self, ctx: CustomContext, user: typing.Optional[discord.User]):
        user = ctx.author if not await self.bot.is_owner(ctx.author) else (user or ctx.author)
        guilds = sorted(user.mutual_guilds, key=lambda g: g.member_count, reverse=True)[0:30]
        embed = discord.Embed(title=f'My top {len(guilds)} mutual servers with {user}:',
                              description='\n'.join(
                                  [f"[`{guild.member_count}`] **{guild.name}** " for guild in guilds]))
        await ctx.send(embed=embed)

    @commands.command(name="commands")
    async def _commands(self, ctx: CustomContext) -> discord.Message:
        """
        Shows all the bot commands, even the ones you can't run.
        """

        ignored_cogs = ("Bot Management", "Jishaku")

        def divide_chunks(str_list, n):
            for i in range(0, len(str_list), n):
                yield str_list[i:i + n]

        shown_commands = [c.name for c in self.bot.commands if c.cog_name not in ignored_cogs]
        ml = max([len(c.name) for c in self.bot.commands if c.cog_name not in ignored_cogs]) + 1

        all_commands = list(divide_chunks(shown_commands, 3))
        all_commands = '\n'.join([''.join([f"{x}{' ' * (ml - len(x))}" for x in c]).strip() for c in all_commands])

        return await ctx.send(embed=discord.Embed(title=f"Here are ALL my commands ({len(shown_commands)})",
                                                  description=f"```fix\n{all_commands}\n```"))
