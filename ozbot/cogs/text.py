import discord, asyncio, typing, aiohttp, random, json, yaml, re, psutil, pkg_resources, time, datetime, os, inspect, itertools, contextlib, datetime
from discord.ext import commands, menus
from discord.ext.commands import Paginator as CommandPaginator
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
**Total Commands:** {len(list(self.context.bot.commands))} | **Usable by you (here):** {len(await self.filter_commands(list(self.context.bot.commands), sort=True))}
```diff
- usage format: <required> [optional]
+ {self.clean_prefix}help [command] - get information on a command
+ {self.clean_prefix}help [category] - get information on a category
```""")
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



class text(commands.Cog):
    """📝 Text commands"""
    def __init__(self, bot):
        self.bot = bot
        help_command = MyHelp()
        help_command.cog = self
        bot.help_command = help_command


    words = ['nothing', 'nothing']
    with open(r'files/banned-words.yaml') as file:
        words = yaml.full_load(file)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        banned_words = self.words['pogwords']
        if any(ele in message.content.lower() for ele in banned_words):
            await message.add_reaction('<:nopog:848312880516562945>')
            await message.add_reaction('😡')

    ##### .s command ####
    # resends the message as the bot

    @commands.command(aliases=['s', 'send', 'foo'])
    @commands.has_permissions(manage_messages=True)
    async def say(self, ctx, *, msg):
        await ctx.message.delete()
        if ctx.channel.permissions_for(ctx.author).mention_everyone:
            if ctx.message.reference:
                reply = ctx.message.reference.resolved
                await reply.reply(msg)
            else:
                await ctx.send(msg)
        else:
            if ctx.message.reference:
                reply = ctx.message.reference.resolved
                await reply.reply(msg, allowed_mentions = discord.AllowedMentions(everyone = False))
            else:
                await ctx.send(msg, allowed_mentions = discord.AllowedMentions(everyone = False))

    @commands.command(aliases=['a', 'an'])
    @commands.has_permissions(manage_messages=True)
    async def announce(self, ctx, channels: commands.Greedy[discord.TextChannel], *, msg):
        await ctx.send(f"""```
{msg}
``` sent to: {', '.join([tc.mention for tc in channels])}""")
        for channel in channels:
            if channel.permissions_for(ctx.author).mention_everyone:
                if ctx.message.reference:
                    msg = ctx.message.reference.resolved.content
                await channel.send(msg)

            else:
                if ctx.message.reference:
                    msg = ctx.message.reference.resolved.content
                await channel.send(msg, allowed_mentions = discord.AllowedMentions(everyone = False))



    @commands.command(aliases=['e'])
    async def edit(self, ctx, *, new : typing.Optional[str] = '--d'):
            if ctx.author.guild_permissions.manage_messages == False:
                await ctx.message.add_reaction('🚫')
                await asyncio.sleep(3)
                try:
                    await ctx.message.delete()
                except discord.Forbidden:
                    return
                return
            if ctx.message.reference:
                msg = ctx.message.reference.resolved
                try:
                    if new.endswith("--s"): await msg.edit(content="{}".format(new[:-3]), suppress=True)
                    elif new.endswith('--d'): await msg.edit(content=None, suppress=True)
                    else: await msg.edit(content=new, suppress=False)
                    try: await ctx.message.delete()
                    except discord.Forbidden:
                        return
                except discord.Forbidden:
                    await ctx.message.add_reaction('🚫')
                    await asyncio.sleep(3)
                    try:
                        await ctx.message.delete()
                    except discord.Forbidden:
                        return
                    return
            else:
                await ctx.message.add_reaction('⚠')
                await asyncio.sleep(3)
                try:
                    await ctx.message.delete()
                except discord.Forbidden:
                    return

    @commands.command(aliases = ['source', 'code'])
    async def sourcecode(self, ctx):
        embed=discord.Embed(title="", description="**[Here's my source code](https://github.com/LeoCx1000/discord-bots)**", color=ctx.me.color)
        await ctx.send(embed=embed)

    @commands.command(aliases = ['getroles', 'buyrole'])
    async def patreon(self, ctx):
        embed=discord.Embed(title="", description="**Purchase a role at [patreon.com/OZ_SMP](https://www.patreon.com/OZ_SMP)**", color=ctx.me.color)
        await ctx.send(embed=embed)

    @commands.command()
    async def ping(self, ctx):
        embed = discord.Embed(title='', description="🏓 pong!", color=ctx.me.color)
        start = time.perf_counter()
        message = await ctx.send(embed=embed)
        end = time.perf_counter()
        await asyncio.sleep(0.7)
        duration = (end - start) * 1000
        embed = discord.Embed(title='', description=f'**websocket:** `{(self.bot.latency * 1000):.2f}ms` \n**message:** `{duration:.2f}ms`', color=ctx.me.color)
        await message.edit(embed=embed)

    @commands.command()
    async def uuid(self, ctx, *, argument: typing.Optional[str] = ''):
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f"https://api.mojang.com/users/profiles/minecraft/{argument}") as cs:
                embed = discord.Embed(color = ctx.me.color)
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

def setup(bot):
    bot.add_cog(text(bot))
