import aiohttp
import asyncio
import discord
import inspect
import os
import pkg_resources
import psutil
import re
import time
from discord.ext import commands, menus


def setup(bot):
    bot.add_cog(About(bot))


class DuckPaginator(menus.MenuPages):
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
            to_delete = [await channel.send('What page do you want to go to?')]

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
            except (discord.Forbidden, discord.HTTPException, discord.NotFound):
                pass


class InviteButtons(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(emoji="<:topgg:870133913102721045>", label='top.gg',
                                        url="https://top.gg/bot/788278464474120202#/"))
        self.add_item(discord.ui.Button(emoji="<:botsgg:870134146972938310>", label='bots.gg',
                                        url="https://discord.bots.gg/bots/788278464474120202"))


class ServerInvite(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(emoji="<:servers:870152102759006208>", label='discord.gg/TdRfGKg8Wh',
                                        url="https://discord.gg/TdRfGKg8Wh"))


class InvMe(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(emoji="<:invite:860644752281436171>", label='Invite me',
                                        url="https://discord.com/api/oauth2/authorize?client_id="
                                            "788278464474120202&permissions=8&scope=bot%20applications.commands"))


class InvSrc(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(emoji="<:invite:860644752281436171>", label='Invite me',
                                        url="https://discord.com/api/oauth2/authorize?client_id="
                                            "788278464474120202&permissions=8&scope=bot%20applications.commands"))
        self.add_item(discord.ui.Button(emoji="<:github:744345792172654643>", label='Source code',
                                        url="https://github.com/LeoCx1000/discord-bots"))

    @discord.ui.button(label='Vote', style=discord.ButtonStyle.gray, emoji="<:topgg:870133913102721045>",
                       custom_id='BotVoteSites')
    async def votes(self, button: discord.ui.Button, interaction: discord.Interaction):
        embed = discord.Embed(description="<:topgg:870133913102721045> **vote here!** <:botsgg:870134146972938310>",
                              color=discord.Colour.blurple())
        await interaction.response.send_message(embed=embed, ephemeral=True, view=InviteButtons())

    @discord.ui.button(label='Discord Server', style=discord.ButtonStyle.gray, emoji="<:servers:870152102759006208>",
                       custom_id='ServerInvite')
    async def invite(self, button: discord.ui.Button, interaction: discord.Interaction):
        embed = discord.Embed(
            description="<:servers:870152102759006208> **Join my server!** <:servers:870152102759006208>"
                        "\nNote that this **will not ask for consent** to join! "
                        "\nIt will just yoink you into the server",
            color=discord.Colour.blurple())
        await interaction.response.send_message(embed=embed, ephemeral=True, view=ServerInvite())


class HelpMenu(DuckPaginator):
    def __init__(self, source):
        super().__init__(source)

    @menus.button('\N{WHITE QUESTION MARK ORNAMENT}', position=menus.Last(5))
    async def show_bot_help(self, payload):
        """shows how to use the bot"""

        embed = discord.Embed(title='Using the bot', colour=discord.Colour.blurple())
        embed.title = 'Using the bot'
        embed.description = 'Hello! Welcome to the help page.'

        entries = (
            ('<argument>', 'This means the argument is __**required**__.'),
            ('[argument]', 'This means the argument is __**optional**__.'),
            ('[A|B]', 'This means that it can be __**either A or B**__.'),
            ('[argument...]', 'This means you can have multiple arguments.\n'
                              'Now that you know the basics, it should be noted that...\n'
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
        if isinstance(group, discord.ext.commands.Group):
            self.title = self.get_minimal_command_signature(group)
            self.description = f"```yaml\n{(self.group.help or 'No help given...').replace('%PRE%', self.prefix)}```"
        else:
            self.title = f'{self.group.qualified_name} Commands'
            self.description = self.group.description

    async def format_page(self, menu, commands):
        embed = discord.Embed(title=self.title, description=self.description, colour=discord.Colour.blurple())

        for command in commands:
            signature = f'{command.qualified_name} {command.signature}'
            if command.help:
                command_help = command.help.replace("%PRE%", self.prefix)
            else:
                command_help = 'No help given...'
            embed.add_field(name=signature, value=f"```yaml\n{command_help}```", inline=False)

        maximum = self.get_max_pages()
        if maximum > 1:
            embed.set_author(name=f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} commands)')

        embed.set_footer(text=f'Use "{self.prefix}help command" for more info on a command.')
        return embed

    def get_minimal_command_signature(self, group):
        return '%s%s %s' % (self.prefix, group.qualified_name, group.signature)


class MyHelp(commands.HelpCommand):

    # Formatting
    def get_minimal_command_signature(self, command):
        return '%s%s %s' % (self.context.clean_prefix, command.qualified_name, command.signature)

    @staticmethod
    def get_command_name(command):
        return '%s' % command.qualified_name

    # !help
    async def send_bot_help(self, mapping):
        embed = discord.Embed(color=discord.Colour.blurple(),
                              description=f"**Total Commands:** {len(list(self.context.bot.commands))} | **Usable by "
                                          f"you (here):** {len(await self.filter_commands(list(self.context.bot.commands), sort=True))} "
                                          "\n```diff"
                                          "\n- usage format: <required> [optional=default value]..."
                                          "\n- dont type these brackets when using the command!"
                                          f"\n+ {self.context.clean_prefix}help [command|subcommand] "
                                          f"- get information on a command"
                                          f"\n+ {self.context.clean_prefix}help [category|number] "
                                          f"- get information on a category"
                                          f"\n```",
                              timestamp=discord.utils.utcnow())
        embed.set_author(name=self.context.author, icon_url=self.context.author.display_avatar.url)
        all_cogs = []
        cog_index = []
        ignored_cogs = ['Jishaku', 'Events', 'Handler', 'Bot Management']
        iterations = 1
        for cog, commands in mapping.items():
            if cog is None or cog.qualified_name in ignored_cogs:
                continue
            num = f"{iterations}\U0000fe0f\U000020e3"
            cog_index.append(cog.qualified_name)
            all_cogs.append(f"{num} {cog.qualified_name}")
            iterations += 1
        self.context.bot.first_help_sent = True
        self.context.bot.all_cogs = cog_index
        nl = '\n'

        embed.add_field(name=f"Available categories [{len(all_cogs)}]", value=f"```fix\n{nl.join(all_cogs)}``````diff"
                                                                              f"\n! \"help [number]\""
                                                                              f"\n- to get help on"
                                                                              f"\n- a category by"
                                                                              f"\n- it's number."
                                                                              f"\n```")

        embed.add_field(name="📰 Latest News - <t:1630792260:d> (<t:1630792260:R>)", value=f"""
_ _
> <:commands:861817699729145901> **NEW! Mute commands**
_`mute`, `unmute`, `tempmute`, `muterole`, `selfmute` 🔇_

> **😂 New fun commands added to the Fun category!**
`meme`, `choose`, `coinFlip`, `roll`, `8ball`, `wikipedia`

> **👷 Added support for multiple prefixes:**
Now you can do `prefix add`, `prefix remove` and `prefix clear` 💞

""")

        embed.set_footer(text=f"Help command inspiration and credits at \"{self.context.clean_prefix}about\"")
        channel = self.get_destination()
        await channel.send(embed=embed, view=InvSrc())

    def common_command_formatting(self, embed_like, command):
        embed_like.title = self.get_command_signature(command)
        if command.description:
            embed_like.description = f'{command.description}\n\n```yaml\n{command.help}\n```'
        else:
            embed_like.description = command.help or '```yaml\nNo help found...\n```'

    # !help <command>
    async def send_command_help(self, command):
        alias = command.aliases
        if command.help:
            command_help = command.help.replace("%PRE%", self.context.clean_prefix)
        else:
            command_help = 'No help given...'
        if alias:
            embed = discord.Embed(color=discord.Colour.blurple(),
                                  title=f"information about: {self.context.clean_prefix}{command}",
                                  description=f"""
```yaml
      usage: {self.get_minimal_command_signature(command)}
    aliases: {', '.join(alias)}
description: {command_help}
```""")
        else:
            embed = discord.Embed(color=discord.Colour.blurple(),
                                  title=f"information about {self.context.clean_prefix}{command}", description=f"""```yaml
      usage: {self.get_minimal_command_signature(command)}
description: {command_help}
```""")
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_cog_help(self, cog):
        entries = cog.get_commands()
        menu = HelpMenu(GroupHelpPageSource(cog, entries, prefix=self.context.clean_prefix))
        await menu.start(self.context)

    async def send_group_help(self, group):
        subcommands = group.commands
        if len(subcommands) == 0:
            return await self.send_command_help(group)

        entries = await self.filter_commands(subcommands, sort=True)
        if len(entries) == 0:
            return await self.send_command_help(group)

        source = GroupHelpPageSource(group, entries, prefix=self.context.clean_prefix)
        menu = HelpMenu(source)
        await menu.start(self.context)

    async def send_error_message(self, error):
        channel = self.get_destination()
        cmd = [item[::-1] for item in (error.split('"', 1)[-1])[::-1].split('"', 1)][::-1][0]
        if cmd.lower() == 'credits':
            charles = self.context.bot.get_user(505532526257766411) or "Charles#5244"
            dutchy = self.context.bot.get_user(171539705043615744) or "Dutchy#6127"
            embed = discord.Embed(color=self.context.me.color, description=f"The main page of the help command was "
                                                                           f"not designed by me. It is inspired by "
                                                                           f"**{dutchy}**'s **{charles}** "
                                                                           f"bot.\n\ncheck it out at "
                                                                           f"https://charles-bot.com/ 💞")
            if isinstance(charles, (discord.User, discord.Member)):
                embed.set_thumbnail(url=charles.display_avatar.url)
            embed.set_author(icon_url=self.context.author.display_avatar.url,
                             name=f"{self.context.author} - help page credits")
            return await channel.send(embed=embed)

        if cmd.isdigit():
            if self.context.bot.first_help_sent is True:
                try:
                    return await self.context.send_help(self.context.bot.all_cogs[int(cmd) - 1])
                except IndexError:
                    pass
            else:
                return await channel.send(f"Whoops! I don't have the list of categories loaded 😔"
                                          f"\nDo `{self.context.clean_prefix}help` to load it! 💞")
        await channel.send(f"{error}"
                           f"\nDo `{self.context.clean_prefix}help` for a list of available commands! 💞")

    async def on_help_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(embed=discord.Embed(color=discord.Colour.blurple(), description=str(error.original)))


class About(commands.Cog):
    """😮 Bot information."""

    def __init__(self, bot):
        self.bot = bot
        help_command = MyHelp()
        help_command.cog = self
        bot.help_command = help_command
        bot.session = aiohttp.ClientSession()

    @commands.Cog.listener('on_ready')
    async def register_views(self):
        if not self.bot.persistent_views_added:
            self.bot.add_view(InvSrc())
            self.bot.persistent_views_added = True

    def get_bot_uptime(self):
        return f"<t:{round(self.bot.uptime.timestamp())}:R>"

    def get_bot_last_rall(self):
        return f"<t:{round(self.bot.last_rall.timestamp())}:R>"

    @commands.command(help="Sends a link to invite the bot to your server")
    async def invite(self, ctx):
        await ctx.send(
            embed=discord.Embed(description=f"[**<:invite:860644752281436171> invite me**]({self.bot.invite_url})",
                                color=ctx.me.color), view=InvMe())

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
                                          f"\n<:open_site:854786097363812352> **| `Websocket ═╣ {round(latency_ms, 3)}ms{' ' * (9 - len(str(round(latency_ms, 3))))}`** "
                                          f"\n<a:typing:597589448607399949> **| `Typing ════╣ {round(typing_ms, 3)}ms{' ' * (9 - len(str(round(typing_ms, 3))))}`**"
                                          f"\n:speech_balloon: **| `Message ═══╣ {round(message_ms, 3)}ms{' ' * (9 - len(str(round(message_ms, 3))))}`**"
                                          f"\n<:psql:871758815345901619> **| `Database ══╣ {round(postgres_ms, 3)}ms{' ' * (9 - len(str(round(postgres_ms, 3))))}`**"
                                          f"\n:infinity: **| `Average ═══╣ {round(average, 3)}ms{' ' * (9 - len(str(round(average, 3))))}`**"))

    @commands.command(help="Shows info about the bot", aliases=['info'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def about(self, ctx):
        """Tells you information about the bot itself."""
        information = await self.bot.application_info()
        embed = discord.Embed(color=discord.Colour.blurple(),
                              description=f"<:github:744345792172654643> [source]({self.bot.repo}) | "
                                          f"<:invite:860644752281436171> [invite me]({self.bot.invite_url}) | "
                                          f"<:topgg:870133913102721045> [top.gg]({self.bot.vote_top_gg}) | "
                                          f"<:botsgg:870134146972938310> [bots.gg]({self.bot.vote_bots_gg})"
                                          f"\n> Try also `{ctx.prefix}source [command]`"
                                          f"\n> or `{ctx.prefix}source [command.subcommand]`")

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
                        value=f"**total servers:** {guilds}\n**average server bot%:** {round(sum(avg) / len(avg), 2)}%")
        embed.add_field(name='Help command',
                        value=f"The help command's main page is inspired by another bot's - Do `{ctx.clean_prefix}help credits` for more info 💞")
        embed.add_field(name='Command info:',
                        value=f"**Last reboot:**\n{self.get_bot_uptime()}\n**Last command reload:**\n{self.get_bot_last_rall()}")

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
        source_url = 'https://github.com/LeoCx1000/discord-bots'
        branch = 'master/DuckBot'
        if command is None:
            embed = discord.Embed(color=ctx.me.color, description=f"**[Here's my source code]({source_url})**")
            return await ctx.send(embed=embed)

        if command == 'help':
            src = type(self.bot.help_command)
            module = src.__module__
            filename = inspect.getsourcefile(src)
        else:
            obj = self.bot.get_command(command.replace('.', ' '))
            if obj is None:
                embed = discord.Embed(color=ctx.me.color, description=f"**[Here's my source code]({source_url})**",
                                      title="command not found")
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
        embed = discord.Embed(color=ctx.me.color,
                              description=f"**[source for `{command}`]({final_url})**")
        embed.set_footer(text=f"{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}")
        await ctx.send(embed=embed)

    @commands.command(description="hiii")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def privacy(self, ctx):
        """
        Shows duckbot's privacy policies
        """
        embed = discord.Embed(title=f'{ctx.me.name} Privacy Policy', description=f"""
> We store your `server id` for purpose of custom prefixes.

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
    async def suggest(self, ctx: commands.Context, *, suggestion):
        channel = self.bot.get_channel(882634213516521473)
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

        await channel.send(embed=embed2)
        await ctx.send(embed=embed)
