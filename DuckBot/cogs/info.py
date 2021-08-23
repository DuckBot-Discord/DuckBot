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
from discord.ext import commands, menus
from helpers import helper


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

class InviteButtons(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(emoji="<:topgg:870133913102721045>", label='top.gg', url="https://top.gg/bot/788278464474120202#/"))
        self.add_item(discord.ui.Button(emoji="<:botsgg:870134146972938310>", label='bots.gg', url="https://discord.bots.gg/bots/788278464474120202"))

class ServerInvite(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(emoji="<:servers:870152102759006208>", label='discord.gg/TdRfGKg8Wh', url="https://discord.gg/TdRfGKg8Wh"))


class InvSrc(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(emoji="<:invite:860644752281436171>", label='Invite me', url="https://discord.com/api/oauth2/authorize?client_id=788278464474120202&permissions=8&scope=bot%20applications.commands"))
        self.add_item(discord.ui.Button(emoji="<:github:744345792172654643>", label='Source code', url="https://github.com/LeoCx1000/discord-bots"))

    @discord.ui.button(label='Vote', style=discord.ButtonStyle.gray, emoji = "<:topgg:870133913102721045>", custom_id='BotVoteSites')
    async def votes(self, button: discord.ui.Button, interaction: discord.Interaction):
        embed=discord.Embed(description="<:topgg:870133913102721045> **vote here!** <:botsgg:870134146972938310>", color = discord.Colour.blurple())
        await interaction.response.send_message(embed=embed, ephemeral=True, view=InviteButtons())

    @discord.ui.button(label='Discord Server', style=discord.ButtonStyle.gray, emoji = "<:servers:870152102759006208>", custom_id='ServerInvite')
    async def invite(self, button: discord.ui.Button, interaction: discord.Interaction):
        embed=discord.Embed(description="<:servers:870152102759006208> **Join my server!** <:servers:870152102759006208>"
                                        "\nNote that this **will not ask for consent** to join! \nIt will just yoink you into the server",
                                        color = discord.Colour.blurple())
        await interaction.response.send_message(embed=embed, ephemeral=True, view=ServerInvite())

class HelpMenu(Duckinator):
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
        embed = discord.Embed(title=self.title, description=self.description, colour=discord.Colour.blurple())

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
        return '%s%s %s' % (self.context.clean_prefix, command.qualified_name, command.signature)

    def get_command_name(self, command):
        return '%s' % (command.qualified_name)

   # !help
    async def send_bot_help(self, mapping):
        embed = discord.Embed(color=discord.Colour.blurple(),
        description=f"""
**Total Commands:** {len(list(self.context.bot.commands))} | **Usable by you (here):** {len(await self.filter_commands(list(self.context.bot.commands), sort=True))}
```diff
- usage format: <required> [optional]
- dont type these brackets when using the command!
+ {self.context.clean_prefix}help [command] - get information on a command
+ {self.context.clean_prefix}help [category] - get information on a category
```
""",
        timestamp = discord.utils.utcnow())
        embed.set_author(name=self.context.author, icon_url=self.context.author.avatar.url)
        allcogs = []
        cogindex = []
        ignored_cogs=[]
        iter = 1
        for cog, commands in mapping.items():
            if cog is None or cog.qualified_name in ignored_cogs: continue
            filtered = await self.filter_commands(commands, sort=True)
            command_signatures = [self.get_command_name(c) for c in filtered]
            if command_signatures:
                num = f"{iter}\U0000fe0f\U000020e3"
                cogindex.append(cog.qualified_name)
                allcogs.append(f"{num} {cog.qualified_name}")
                iter+=1
        self.context.bot.all_cogs = cogindex
        nl = '\n'

        embed.add_field(name=f"Available categories [{len(allcogs)}]", value=f"```fix\n{nl.join(allcogs)}```")

        embed.add_field(name="📰 Latest News - <t:1629668507:d> (<t:1629668507:R>)", value = f"""
_ _
> <:update:264184209617321984> **Updated to discord.py Version 2.0(BETA)**
‍*If a command isn't working as intended, or not at all, DM me ({self.context.me.mention}) with the command you tried to execute and it will be fixed!* 💞

> \U0001f518 **Added buttons to the help menu.**
_Press on them to invite me!_ ❣

> 🎓 **Added proper credits to the help command**
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
        if command.help: command_help = command.help.replace("%PRE%", self.context.clean_prefix)
        else: command_help = 'No help given...'
        if alias:
            embed = discord.Embed(color=discord.Colour.blurple(), title=f"information about: {self.context.clean_prefix}{command}",
            description=f"""
```yaml
      usage: {self.get_minimal_command_signature(command)}
    aliases: {', '.join(alias)}
description: {command_help}
```""")
        else:
            embed = discord.Embed(color=discord.Colour.blurple(), title=f"information about {self.context.clean_prefix}{command}", description=f"""```yaml
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
        cmd = error[19:][:-8]
        if cmd.lower() == 'credits':
            charles = self.context.bot.get_user(505532526257766411)
            print(charles, type(charles))
            if not charles: charles = "Charles#5244"
            dutchy = self.context.bot.get_user(171539705043615744)
            print(dutchy, type(dutchy))
            if not dutchy: charles = "Dutchy#6127"
            embed = discord.Embed(color = self.context.me.color, description = f"""
The main page of the help command was not designed by me. It is inspired by **{dutchy}**'s **{charles}** bot.

check it out at https://charles-bot.com/ 💞""")
            if not isinstance(charles, str):
                embed.set_thumbnail(url=charles.avatar.url)
            embed.set_author(icon_url=self.context.author.avatar.url, name=f"{self.context.author} - help page credits")
            return await channel.send(embed=embed)
        await channel.send(f"Sorry, i couldn't find a command named \"{cmd[:50]}\" 😔\ndo `{self.context.clean_prefix}help` for help with all commands")

    async def on_help_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(embed=discord.Embed(color=discord.Colour.blurple(), description=str(error.original)))


class about(commands.Cog):
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
        await ctx.send(embed=discord.Embed(description=f"[**<:invite:860644752281436171> invite me**]({self.bot.invite_url})",color=ctx.me.color))

    @commands.command(  help="Checks the bot's ping to Discord")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def ping(self, ctx):
        pings = []
        number = 0

        typings = time.monotonic()
        await ctx.trigger_typing()
        typinge = time.monotonic()
        typingms = (typinge - typings) * 1000
        pings.append(typingms)

        start = time.perf_counter()
        message = await ctx.send("🏓 pong!")
        end = time.perf_counter()
        messagems = (end - start) * 1000
        pings.append(messagems)

        discords = time.monotonic()
        url = "https://discordapp.com/"
        async with self.bot.session.get(url) as resp:
            if resp.setstatus == 200:
                discorde = time.monotonic()
                discordms = (discorde - discords) * 1000
                pings.append(discordms)
            else:
                discordms = 0

        latencyms = self.bot.latency * 1000
        pings.append(latencyms)

        pstart = time.perf_counter()
        await self.bot.db.fetch("SELECT 1")
        pend = time.perf_counter()
        psqlms = (pend - pstart) * 1000
        pings.append(psqlms)

        for ms in pings:
            number += ms
        average = number / len(pings)

        await asyncio.sleep(0.7)

        await message.edit(content=re.sub('\n *', '\n', f"""
     <:open_site:854786097363812352> **| `Websocket ═╣ {round(latencyms, 3)}ms{' ' * (9-len(str(round(latencyms, 3))))}`**
       <a:typing:597589448607399949> **| `Typing ════╣ {round(typingms, 3)}ms{' ' * (9-len(str(round(typingms, 3))))}`**
                    :speech_balloon: **| `Message ═══╣ {round(messagems, 3)}ms{' ' * (9-len(str(round(messagems, 3))))}`**
       <:discord:314003252830011395> **| `Discord ═══╣ {round(discordms, 3)}ms{' ' * (9-len(str(round(discordms, 3))))}`**
          <:psql:871758815345901619> **| `Database ══╣ {round(psqlms, 3)}ms{' ' * (9-len(str(round(psqlms, 3))))}`**
                          :infinity: **| `Average ═══╣ {round(average, 3)}ms{' ' * (9-len(str(round(average, 3))))}`**
"""))

    @commands.command(help="Shows info about the bot", aliases=['info'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def about(self, ctx):
        """Tells you information about the bot itself."""
        information = await self.bot.application_info()
        embed = discord.Embed(color=discord.Colour.blurple(), description=f"""
[<:github:744345792172654643> source]({self.bot.repo}) | [<:invite:860644752281436171> invite me]({self.bot.invite_url}) | [<:topgg:870133913102721045> top.gg]({self.bot.vote_top_gg}) | [<:botsgg:870134146972938310> bots.gg]({self.bot.vote_bots_gg})
> Try also `{ctx.prefix}source [command]`
> or `{ctx.prefix}source [command.subcommand]`
""")
        embed.set_author(name=f"Made by {information.owner}", icon_url=information.owner.avatar.url)
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
        embed.add_field(name='Bot servers', value=f"**total servers:** {guilds}\n**average server bot%:** {round(sum(l) / len(l), 2)}%")
        embed.add_field(name='Help command', value = f"The help command's main page is inspired by another bot's - Do `{ctx.clean_prefix}help credits` for more info 💞")
        embed.add_field(name='Command info:', value=f"**Last reboot:**\n{self.get_bot_uptime()}\n**Last command reload:**\n{self.get_bot_last_rall()}")

        version = pkg_resources.get_distribution('discord.py').version
        embed.set_footer(text=f'Made with discord.py v{version} 💖', icon_url='http://i.imgur.com/5BFecvA.png')
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)


    @commands.command(help="Links to the bot's code, or a specific command's",aliases = ['sourcecode', 'code'], usage="[command|command.subcommand]")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def source(self, ctx, *, command: str = None):
        source_url = 'https://github.com/LeoCx1000/discord-bots'
        branch = 'master/DuckBot'
        if command is None:
            embed=discord.Embed(color=ctx.me.color, description=f"**[Here's my source code]({source_url})**")
            return await ctx.send(embed=embed)

        if command == 'help':
            src = type(self.bot.help_command)
            module = src.__module__
            filename = inspect.getsourcefile(src)
        else:
            obj = self.bot.get_command(command.replace('.', ' '))
            if obj is None:
                embed=discord.Embed(color=ctx.me.color, description=f"**[Here's my source code]({source_url})**", title="command not found")
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

#-----------------------------------------------------------------#
#------------------------ USER-INFO ------------------------------#
#---------------------------------------------------=====---------#

    @commands.command(aliases = ['userinfo', 'ui', 'whois', 'whoami'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def uinfo(self, ctx, user: typing.Optional[discord.Member]):
        if not user: user = ctx.author
        # BADGES
        badges = helper.get_user_badges(user)
        if badges: badges = f"\n<:store_tag:658538492409806849>**Badges:**{badges}"
        else: badges = ''
        # BADGES
        perms = helper.get_perms(user.guild_permissions)
        if perms: perms = f"\n<:store_tag:658538492409806849>**Staff permissions:** {', '.join(perms)}"
        else: perms = ''
        # USERID
        userid = f"\n<:greyTick:596576672900186113>**ID:** `{user.id}`"
        # NICKNAME
        if user.nick: nick = f"\n<:nickname:850914031953903626>**Nickname:** `{user.nick}`"
        else: nick = ""
        # CREATION DATE
        date = f"<t:{round(user.created_at.timestamp())}:F>"
        rdate = f"<t:{round(user.created_at.timestamp())}:R>"
        created = f"\n<:invite:860644752281436171>**Created:** {date} ({rdate})"
        # JOIN DATE
        if user.joined_at:
            date = f"<t:{round(user.joined_at.timestamp())}:F>"
            rdate = f"<t:{round(user.joined_at.timestamp())}:R>"
            joined = f"\n<:joined:849392863557189633>**joined:** {date} ({rdate})"
        else: joined = ""
        # GUILD OWNER
        if user is ctx.guild.owner:
            owner = f"\n<:owner:585789630800986114>**Owner:** <:check:314349398811475968>"
        else: owner = ""
        # BOT
        if user.bot:
            bot = f"\n<:botTag:230105988211015680>**Bot:** <:check:314349398811475968>"
        else: bot = ""
        # BOOSTER SINCE
        if user.premium_since:
            date = user.premium_since.strftime("%b %-d %Y at %-H:%M")
            boost = f"\n<:booster4:585764446178246657>**Boosting since:** `{date} UTC`"
        else: boost = ""

        # Join Order
        order = f"\n<:moved:848312880666640394>**Join position:** `{sorted(ctx.guild.members, key=lambda user: user.joined_at).index(user) + 1}`"

        if user.premium_since:
            date = user.premium_since.strftime("%b %-d %Y at %-H:%M")
            boost = f"\n<:booster4:585764446178246657>**Boosting since:** `{date} UTC`"
        else: boost = ""
        # ROLES
        roles = ""
        for role in user.roles:
            if role is ctx.guild.default_role: continue
            roles = f"{roles} {role.mention}"
        if roles != "":
            roles = f"\n<:role:808826577785716756>**Roles:** {roles}"
        # EMBED
        embed = discord.Embed(color=ctx.me.color, description=f"{badges}{owner}{bot}{userid}{created}{nick}{joined}{order}{boost}{roles}{perms}")
        embed.set_author(name=user, icon_url=user.avatar.url)
        embed.set_thumbnail(url=user.avatar.url)
        await ctx.send(embed=embed)



def setup(bot):
    bot.add_cog(about(bot))
