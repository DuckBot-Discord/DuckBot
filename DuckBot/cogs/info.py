import discord, asyncio, typing, aiohttp, random, json, yaml, re, psutil, pkg_resources, time, datetime, os, inspect, itertools, contextlib, datetime
from discord.ext import commands, menus
from discord.ext.commands import Paginator as CommandPaginator
from errors import HigherRole
from jishaku.models import copy_context_with


class Duckinator(menus.MenuPages):
    def __init__(self, source):
        super().__init__(source=source, check_embeds=True)
        self.input_lock = asyncio.Lock()

    async def finalize(self, timed_out):
        try:
            if timed_out:
                await self.message.clear_reactions()
            else:
                await self.message.delete()
        except discord.HTTPException:
            pass

    @menus.button('\N{INFORMATION SOURCE}\ufe0f', position=menus.Last(3))
    async def show_help(self, payload):
        """shows this message"""
        embed = discord.Embed(title='Paginator help', description='Hello! Welcome to the help page.')
        messages = []
        for (emoji, button) in self.buttons.items():
            messages.append(f'{emoji}: {button.action.__doc__}')

        embed.add_field(name='What are these reactions for?', value='\n'.join(messages), inline=False)
        embed.set_footer(text=f'We were on page {self.current_page + 1} before this message.')
        await self.message.edit(content=None, embed=embed)

        async def go_back_to_current_page():
            await asyncio.sleep(30.0)
            await self.show_page(self.current_page)

        self.bot.loop.create_task(go_back_to_current_page())

    @menus.button('\N{INPUT SYMBOL FOR NUMBERS}', position=menus.Last(1.5), lock=False)
    async def numbered_page(self, payload):
        """lets you type a page number to go to"""
        if self.input_lock.locked():
            return

        async with self.input_lock:
            channel = self.message.channel
            author_id = payload.user_id
            to_delete = []
            to_delete.append(await channel.send('What page do you want to go to?'))

            def message_check(m):
                return m.author.id == author_id and \
                       channel == m.channel and \
                       m.content.isdigit()

            try:
                msg = await self.bot.wait_for('message', check=message_check, timeout=30.0)
            except asyncio.TimeoutError:
                to_delete.append(await channel.send('Took too long.'))
                await asyncio.sleep(5)
            else:
                page = int(msg.content)
                to_delete.append(msg)
                await self.show_checked_page(page - 1)

            try:
                await channel.delete_messages(to_delete)
            except Exception:
                pass


class HelpMenu(Duckinator):
    def __init__(self, source):
        super().__init__(source)

    @menus.button('\N{WHITE QUESTION MARK ORNAMENT}', position=menus.Last(5))
    async def show_bot_help(self, payload):
        """shows how to use the bot"""

        embed = discord.Embed(title='Using the bot', colour=0x5865F2)
        embed.title = 'Using the bot'
        embed.description = 'Hello! Welcome to the help page.'

        entries = (
            ('<argument>', 'This means the argument is __**required**__.'),
            ('[argument]', 'This means the argument is __**optional**__.'),
            ('[A|B]', 'This means that it can be __**either A or B**__.'),
            ('[argument...]', 'This means you can have multiple arguments.\n' \
                              'Now that you know the basics, it should be noted that...\n' \
                              '__**You do not type in the brackets!**__')
        )

        embed.add_field(name='How do I use this bot?', value='Reading the bot signature is pretty simple.')

        for name, value in entries:
            embed.add_field(name=name, value=value, inline=False)

        embed.set_footer(text=f'We were on page {self.current_page + 1} before this message.')
        await self.message.edit(embed=embed)

        async def go_back_to_current_page():
            await asyncio.sleep(30.0)
            await self.show_page(self.current_page)

        self.bot.loop.create_task(go_back_to_current_page())

class GroupHelpPageSource(menus.ListPageSource):
    def __init__(self, group, commands, *, prefix):
        super().__init__(entries=commands, per_page=6)
        self.group = group
        self.prefix = prefix
        self.title = f'{self.group.qualified_name} Commands'
        self.description = self.group.description

    async def format_page(self, menu, commands):
        embed = discord.Embed(title=self.title, description=self.description, colour=0x5865F2)

        for command in commands:
            signature = f'{command.qualified_name} {command.signature}'
            if command.help: command_help = command.help.replace("%PRE%", self.prefix)
            else: command_help = 'No help given...'
            embed.add_field(name=signature, value=f"```yaml\n{command_help}```", inline=False)

        maximum = self.get_max_pages()
        if maximum > 1:
            embed.set_author(name=f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} commands)')

        embed.set_footer(text=f'Use "{self.prefix}help command" for more info on a command.')
        return embed

class MyHelp(commands.HelpCommand):
    # Formatting
    def get_minimal_command_signature(self, command):
        return '%s%s %s' % (self.clean_prefix, command.qualified_name, command.signature)

    def get_command_name(self, command):
        return '%s' % (command.qualified_name)

   # !help
    async def send_bot_help(self, mapping):
        embed = discord.Embed(color=0x5865F2, title=f"ℹ {self.context.me.name} help",
        description=f"""
📰 **__NEW: custom prefix! do__ `{self.clean_prefix}prefix [new]` __to change it!__** 📰
**Total Commands:** {len(list(self.context.bot.commands))} | **Usable by you (here):** {len(await self.filter_commands(list(self.context.bot.commands), sort=True))}
```diff
- usage format: <required> [optional]
+ {self.clean_prefix}help [command] - get information on a command
+ {self.clean_prefix}help [category] - get information on a category
```[<:invite:860644752281436171> invite me]({self.context.bot.invite_url}) | [<:topgg:870133913102721045> top.gg]({self.context.bot.vote_top_gg}) | [<:botsgg:870134146972938310> bots.gg]({self.context.bot.vote_bots_gg}) | [<:github:744345792172654643> source]({self.context.bot.repo})
> **server prefix:** `{await self.context.bot.db.fetchval('SELECT prefix FROM prefixes WHERE guild_id = $1', self.context.guild.id) or 'db.'}`

​_ _""")
        ignored_cogs=['helpcog']
        for cog, commands in mapping.items():
            if cog is None or cog.qualified_name in ignored_cogs: continue
            filtered = await self.filter_commands(commands, sort=True)
            command_signatures = [self.get_command_name(c) for c in filtered]
            if command_signatures:
                val = "`, `".join(command_signatures)
                embed.add_field(name=cog.qualified_name, value=f"{cog.description}\n`{val}`", inline=True)

        channel = self.get_destination()
        await channel.send(embed=embed)

    def common_command_formatting(self, embed_like, command):
        embed_like.title = self.get_command_signature(command)
        if command.description:
            embed_like.description = f'{command.description}\n\n```yaml\n{command.help}\n```'
        else:
            embed_like.description = command.help or '```yaml\nNo help found...\n```'

  # !help <command>
    async def send_command_help(self, command):
        alias = command.aliases
        if command.help: command_help = command.help.replace("%PRE%", self.clean_prefix)
        else: command_help = 'No help given...'
        if alias:
            embed = discord.Embed(color=0x5865F2, title=f"information about: {self.clean_prefix}{command}",
            description=f"""
```yaml
      usage: {self.get_minimal_command_signature(command)}
    aliases: {', '.join(alias)}
description: {command_help}
```""")
        else:
            embed = discord.Embed(color=0x5865F2, title=f"information about {self.clean_prefix}{command}", description=f"""```yaml
      usage: {self.get_minimal_command_signature(command)}
description: {command_help}
```""")
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_cog_help(self, cog):
        entries = cog.get_commands()
        menu = HelpMenu(GroupHelpPageSource(cog, entries, prefix=self.clean_prefix))
        await menu.start(self.context)


    async def send_group_help(self, group):
        subcommands = group.commands
        if len(subcommands) == 0:
            return await self.send_command_help(group)

        entries = await self.filter_commands(subcommands, sort=True)
        if len(entries) == 0:
            return await self.send_command_help(group)

        source = GroupHelpPageSource(group, entries, prefix=self.clean_prefix)
        menu = HelpMenu(source)
        await menu.start(self.context)


    async def on_help_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(embed=discord.Embed(color=0x5865F2, description=str(error.original)))


class about(commands.Cog):
    """😮 Bot information."""
    def __init__(self, bot):
        self.bot = bot
        help_command = MyHelp()
        help_command.cog = self
        bot.help_command = help_command

    def get_bot_uptime(self):
        return f"<t:{round(self.bot.uptime.timestamp())}:R>"

    def get_bot_last_rall(self):
        return f"<t:{round(self.bot.last_rall.timestamp())}:R>"

    @commands.command(help="Sends a link to invite the bot to your server")
    async def invite(self, ctx):
        await ctx.send(embed=discord.Embed(description=f"[**<:invite:860644752281436171> invite me**]({self.bot.invite_url})",color=ctx.me.color))

    @commands.command(  help="Checks the bot's ping to Discord")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def ping(self, ctx):
        embed = discord.Embed(title='', description="🏓 pong!", color=ctx.me.color)
        start = time.perf_counter()
        message = await ctx.send(embed=embed)
        end = time.perf_counter()

        pstart = time.perf_counter()
        await self.bot.db.fetch("SELECT 1")
        pend = time.perf_counter()
        ping = (pend - pstart) * 1000

        await asyncio.sleep(0.7)
        duration = (end - start) * 1000
        embed = discord.Embed(description=f"""**<:open_site:854786097363812352> Websocket:** `{(self.bot.latency * 1000):.2f}ms`
                                            **<a:typing:597589448607399949> Message:** `{duration:.2f}ms`
                                            **<:psql:871758815345901619> Database:** `{ping:.2f}ms`""", color=ctx.me.color)
        await message.edit(embed=embed)

    @commands.command(help="Shows info about the bot", aliases=['info'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def about(self, ctx):
        """Tells you information about the bot itself."""
        information = await self.bot.application_info()
        embed = discord.Embed(color=0x5865F2, description=f"""
[<:github:744345792172654643> source]({self.bot.repo}) | [<:invite:860644752281436171> invite me]({self.bot.invite_url}) | [<:topgg:870133913102721045> top.gg]({self.bot.vote_top_gg}) | [<:botsgg:870134146972938310> bots.gg]({self.bot.vote_bots_gg})
> Try also `{ctx.prefix}source [command]`
> or `{ctx.prefix}source [command.subcommand]`
""")
        embed.set_author(name=f"Made by {information.owner}", icon_url=information.owner.avatar_url)
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
        l = [(sum(m.bot for m in g.members) / g.member_count)*100 for g in self.bot.guilds]

        embed.add_field(name='Members', value=f'{total_members} total\n{total_unique} unique')
        embed.add_field(name='Channels', value=f'{text + voice} total\n{text} text\n{voice} voice')

        memory_usage = psutil.Process().memory_full_info().uss / 1024**2
        cpu_usage = psutil.cpu_percent()
        embed.add_field(name='Process', value=f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU')

        version = pkg_resources.get_distribution('discord.py').version
        embed.add_field(name='Bot servers', value=f"**total servers:** {guilds}\n**average server bot%:** {round(sum(l) / len(l), 2)}%")
        embed.add_field(name='Command info:', value=f"**Last reboot:**\n{self.get_bot_uptime()}\n**Last command reload:**\n{self.get_bot_last_rall()}")
        embed.set_footer(text=f'Made with discord.py v{version} 💖', icon_url='http://i.imgur.com/5BFecvA.png')
        embed.timestamp = datetime.datetime.utcnow()
        await ctx.send(embed=embed)


    @commands.command(help="Links to the bot's code, or a specific command's",aliases = ['sourcecode', 'code'], usage="[command|command.subcommand]")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def source(self, ctx, *, command: str = None):
        source_url = 'https://github.com/LeoCx1000/discord-bots'
        branch = 'master/DuckBot'
        if command is None:
            embed=discord.Embed(color=ctx.me.color, description=f"**[Here's my surce code]({source_url})**")
            return await ctx.send(embed=embed)

        if command == 'help':
            src = type(self.bot.help_command)
            module = src.__module__
            filename = inspect.getsourcefile(src)
        else:
            obj = self.bot.get_command(command.replace('.', ' '))
            if obj is None:
                embed=discord.Embed(color=ctx.me.color, description=f"**[Here's my surce code]({source_url})**", title="command not found")
                return await ctx.send(embed=embed)

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

        final_url = f'<{source_url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>'
        embed=discord.Embed(color=ctx.me.color,
                            description=f"**[source for `{command}`]({final_url})**")
        embed.set_footer(   text=f"{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}")
        await ctx.send(embed=embed)



    @commands.command(help="Shows duckbot's privacy policies", description="hiii")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def privacy(self, ctx):
        embed = discord.Embed(title=f'{ctx.me.name} Privacy Policy', description=f"""
> We store your `server id` for purpose of custom prefixes.
""", color=ctx.me.color)
        embed.set_footer(text='Privacy concerns, DM the bot.')
        await ctx.send(embed=embed)



def setup(bot):
    bot.add_cog(about(bot))
