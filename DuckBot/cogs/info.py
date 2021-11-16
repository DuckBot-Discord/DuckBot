import asyncio
import difflib
import inspect
import itertools
import os
import re
import time
import typing

import discord
import pkg_resources
import psutil
from discord import Interaction
from discord.ext import commands
from jishaku.paginators import WrappedPaginator

from DuckBot.__main__ import DuckBot, CustomContext
from DuckBot.helpers import paginator, constants, helper
from DuckBot.helpers.helper import count_lines, count_others
from DuckBot.helpers.paginator import InvSrc

suggestions_channel = 882634213516521473
newline = "\n"


def setup(bot):
    bot.add_cog(About(bot))


def get_minimal_command_signature(ctx, command):
    if isinstance(command, commands.Group):
        return '[G] %s%s %s' % (ctx.clean_prefix, command.qualified_name, command.signature)
    return '(c) %s%s %s' % (ctx.clean_prefix, command.qualified_name, command.signature)


class HelpCentre(discord.ui.View):
    def __init__(self, ctx: CustomContext, other_view: discord.ui.View):
        super().__init__()
        self.embed = None
        self.ctx = ctx
        self.other_view = other_view

    @discord.ui.button(emoji='🏠', label="Go Back", style=discord.ButtonStyle.blurple)
    async def go_back(self, _, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.embed, view=self.other_view)
        self.stop()

    async def start(self, interaction: discord.Interaction):
        embed = discord.Embed(title='Here is a guide on how to understand this help command',
                              description="\n__**Do not not include these brackets when running a command!**__"
                                          "\n__**They are only there to indicate the argument type**__",
                              color=self.ctx.color)
        embed.add_field(name="`<argument>`", value="Means that this argument is __**required**__", inline=False)
        embed.add_field(name="`[argument]`", value="Means that this argument is __**optional**__", inline=False)
        embed.add_field(name="`[argument='default']`",
                        value="Means that this argument is __**optional**__ and has a default value", inline=False)
        embed.add_field(name="`[argument]...` or `[argument...]`",
                        value="Means that this argument is __**optional**__ and can take __**multiple entries**__",
                        inline=False)
        embed.add_field(name="`<argument>...` or `<argument...>`",
                        value="Means that this argument is __**required**__ and can take __**multiple entries**__"
                              "\nFor example: db.mass-mute @user1 @user2 @user3", inline=False)
        embed.add_field(name="`[X|Y|Z]`", value="Means that this argument can be __**either X, Y or Z**__",
                        inline=False)
        embed.set_footer(text="To continue browsing the help menu, press 🏠Go Back")
        embed.set_author(name='About this Help Command', icon_url=self.ctx.me.display_avatar.url)
        self.embed = interaction.message.embeds[0]
        self.add_item(discord.ui.Button(label='Support Server', url='https://discord.gg/TdRfGKg8Wh'))
        self.add_item(discord.ui.Button(label='Invite Me', url=discord.utils.oauth_url(self.ctx.bot.user.id,
                                        permissions=discord.Permissions(294171045078), scopes=('applications.commands', 'bot'))))
        await interaction.response.edit_message(embed=embed, view=self)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user and interaction.user == self.ctx.author:
            return True
        await interaction.response.defer()
        return False


class NewsMenu(discord.ui.View):
    def __init__(self, ctx: CustomContext, *, other_view: discord.ui.View):
        super().__init__()
        self.embed: discord.Embed = None
        self.ctx = ctx
        self.bot: DuckBot = ctx.bot
        self.other_view = other_view

    @discord.ui.button(emoji='🏠', label="Go Back", style=discord.ButtonStyle.blurple)
    async def go_back(self, _, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.embed, view=self.other_view)
        self.stop()

    @discord.ui.button(emoji='🙏', label='Voting helps a lot to make DuckBot grow. Please vote!',
                       style=discord.ButtonStyle.green, disabled=True, row=2)
    async def vote(self, _, __):
        return

    async def start(self, interaction: discord.Interaction):
        info: About = self.bot.get_cog('About')
        embed = await info.news(self.ctx, return_embed=True)
        self.embed = interaction.message.embeds[0]
        self.add_item(discord.ui.Button(emoji=constants.TOP_GG, label='Vote on top.gg!', url=f'https://top.gg/bot/{self.ctx.author.id}'))
        self.add_item(discord.ui.Button(emoji=constants.BOTS_GG, label='Vote bots.gg!', url=f'https://discord.bots.gg/{self.ctx.me.id}'))
        embed.set_footer(text="To continue browsing the news, press 🏠Go Back")
        await interaction.response.edit_message(embed=embed, view=self)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user and interaction.user == self.ctx.author:
            return True
        await interaction.response.defer()
        return False

    async def on_timeout(self) -> None:
        await self.other_view.on_timeout()
        self.other_view.stop()


class HelpView(discord.ui.View):
    def __init__(self, ctx: CustomContext, data: typing.Dict[commands.Cog, typing.List[commands.Command]], help_command: commands.HelpCommand):
        super().__init__()
        self.ctx = ctx
        self.data = data
        self.help_command = help_command
        self.bot: DuckBot = ctx.bot
        self.main_embed = self.build_main_page()
        self.current_page = 0
        self.message: discord.Message = None
        self.embeds: typing.List[discord.Embed] = [self.main_embed]

    @discord.ui.select(placeholder="Select a category", row=0)
    async def category_select(self, select: discord.ui.Select, interaction: discord.Interaction):
        if select.values[0] == "index":
            self.current_page = 0
            self.embeds = [self.main_embed]
            self._update_buttons()
            return await interaction.response.edit_message(embed=self.main_embed, view=self)
        elif select.values[0] == "old_help_command":
            await self.old_help(self.data)
            self.stop()
            return
        cog = self.bot.get_cog(select.values[0])
        if not cog:
            return await interaction.response.send_message('Somehow, that category was not found? 🤔', ephemeral=True)
        else:
            self.embeds = self.build_embeds(cog)
            self.current_page = 0
            self._update_buttons()
            return await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    def build_embeds(self, cog: commands.Cog) -> typing.List[discord.Embed]:
        embeds = []
        comm = cog.get_commands()
        embed = discord.Embed(title=f"{cog.qualified_name} commands [{len(comm)}]", color=self.ctx.color,
                              description=cog.description or "No description provided")
        for cmd in comm:
            embed.add_field(name=f"{constants.ARROW}`{cmd.name}{f' {cmd.signature}`' if cmd.signature else '`'}",
                            value=(cmd.brief or cmd.help or 'No help given...').replace('%PRE%', self.ctx.clean_prefix)[0:1024], inline=False)
            embed.set_footer(text="For more info on a command run \"help [command]\"")
            if len(embed.fields) == 5:
                embeds.append(embed)
                embed = discord.Embed(title=f"{cog.qualified_name} commands [{len(comm)}]", color=self.ctx.color,
                                      description=cog.description or "No description provided")
        if len(embed.fields) > 0:
            embeds.append(embed)
        return embeds

    def build_select(self) -> None:
        self.category_select: discord.ui.Select
        self.category_select.options = []
        self.category_select.add_option(label='Main Page', value='index', emoji='🏠')
        for cog, comm in self.data.items():
            if not comm:
                continue
            emoji = getattr(cog, 'select_emoji', None)
            label = cog.qualified_name + f" ({len(comm)})"
            brief = getattr(cog, 'select_brief', None)
            self.category_select.add_option(label=label, value=cog.qualified_name, emoji=emoji, description=brief)
        self.category_select.add_option(label='Browse Old Help Command', value='old_help_command', emoji='💀',
                                        description='Not recommended, but still available.')

    def build_main_page(self) -> discord.Embed:
        embed = discord.Embed(color=self.ctx.color, title='DuckBot Help Menu',
                              description="Hello, I'm DuckBot! A multi-purpose bot with a lot of features.")
        embed.add_field(name="Getting Help", inline=False,
                        value="Use `db.help <command>` for more info on a command."
                              "\nThere is also `db.help <command> [subcommand]`."
                              "\nUse `db.help <category>` for more info on a category."
                              "\nYou can also use the menu below to view a category.")
        embed.add_field(name='Getting Support', inline=False,
                        value='To get help, you can join my support server.'
                              f'\n{constants.SERVERS_ICON} <https://discord.gg/TdRfGKg8Wh>'
                              '\n📨 You can also send me a DM if you prefer to.')
        embed.add_field(name='Who Am I?', inline=False,
                        value=f'I\'m DuckBot, a multipurpose bot created and maintained '
                              f'\nby {constants.GITHUB}[LeoCx1000](https://github.com/'
                              f'leoCx1000). You can use me to play games, moderate '
                              f'\nyour server, mess with some images and more! Check out '
                              f'\nall my features using the dropdown below.'
                              
                              
                              f'\n\nI\'ve been up since {discord.utils.format_dt(self.bot.uptime)}'
                              f'\nYou can also find my source code on {constants.GITHUB}[GitHub](https://github.com/LeoCx1000/discord-bots)')
        embed.set_footer(text='For more info on the help command press ❓help',
                         icon_url='https://cdn.discordapp.com/emojis/895407958035431434.png')
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar.url)
        return embed

    @discord.ui.button(emoji='❓', label='help', row=1, style=discord.ButtonStyle.green)
    async def help(self, _, interaction: Interaction):
        view = HelpCentre(self.ctx, self)
        await view.start(interaction)

    @discord.ui.button(emoji=constants.ARROWBACKZ, row=1)
    async def previous(self, _, interaction: Interaction):
        self.current_page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(emoji='🗑', row=1, style=discord.ButtonStyle.red)
    async def _end(self, _, interaction: Interaction):
        await interaction.message.delete()
        if self.ctx.channel.permissions_for(self.ctx.me).manage_messages:
            await self.ctx.message.delete(delay=0)

    @discord.ui.button(emoji=constants.ARROWFWDZ, row=1)
    async def next(self, _, interaction: Interaction):
        self.current_page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @discord.ui.button(emoji='📰', label='news', row=1, style=discord.ButtonStyle.green)
    async def vote(self, _, interaction: Interaction):
        view = NewsMenu(self.ctx, other_view=self)
        await view.start(interaction)

    def _update_buttons(self):
        styles = {True: discord.ButtonStyle.gray, False: discord.ButtonStyle.blurple}
        page = self.current_page
        total = len(self.embeds) - 1
        self.next.disabled = page == total
        self.previous.disabled = page == 0
        self.next.style = styles[page == total]
        self.previous.style = styles[page == 0]

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user and interaction.user == self.ctx.author:
            return True
        await interaction.response.defer()
        return False

    async def on_timeout(self) -> None:
        self.clear_items()
        await self.message.edit(view=self)

    async def start(self):
        self.build_select()
        self._update_buttons()
        self.message = await self.ctx.send(embed=self.main_embed, view=self, footer=False)

    async def old_help(self, mapping):
        data = []
        ignored_cogs = ['Jishaku', 'Events', 'Handler', 'Bot Management', 'DuckBot Hideout']
        for cog, cog_commands in mapping.items():

            if cog is None or cog.qualified_name in ignored_cogs:
                continue
            command_signatures = [get_minimal_command_signature(self.ctx, c) for c in cog_commands]
            if command_signatures:
                if cog.qualified_name in ('Image',):
                    pages = WrappedPaginator(prefix=f'{cog.description}\n```css\n', suffix='\n```', max_size=450)
                    for s in command_signatures:
                        pages.add_line(s)
                    for p in pages.pages:
                        info = ('Category: ' + cog.qualified_name, p)
                        data.append(info)
                else:
                    val = cog.description + '```css\n' + "\n".join(command_signatures) + '\n```'
                    info = ('Category: ' + cog.qualified_name, f'{val}')

                    data.append(info)

        source = paginator.HelpMenuPageSource(data=data, ctx=self.ctx, help_class=self.help_command)
        menu = paginator.ViewPaginator(source=source, ctx=self.ctx, compact=True)
        await menu.start(start_message=self.message)


class MyHelp(commands.HelpCommand):
    def __init__(self, **options):
        super().__init__(**options)
        self.context: CustomContext = None

    def get_bot_mapping(self):
        """Retrieves the bot mapping passed to :meth:`send_bot_help`."""
        bot = self.context.bot
        ignored_cogs = ['Jishaku', 'Events', 'Handler', 'Bot Management', 'DuckBot Hideout']
        mapping = {cog: cog.get_commands() for cog in
                   sorted(bot.cogs.values(), key=lambda c: len(c.get_commands()), reverse=True) if
                   cog.qualified_name not in ignored_cogs}
        return mapping

    def get_minimal_command_signature(self, command):
        if isinstance(command, commands.Group):
            return '[G] %s%s %s' % (self.context.clean_prefix, command.qualified_name, command.signature)
        return '(c) %s%s %s' % (self.context.clean_prefix, command.qualified_name, command.signature)

    # !help
    async def send_bot_help(self, mapping):

        view = HelpView(self.context, data=mapping, help_command=self)
        await view.start()

    # !help <command>
    async def send_command_help(self, command: commands.Command):
        embed = discord.Embed(title=f"information about: `{self.context.clean_prefix}{command}`",
                              description='**Description:**\n' + (command.help or 'No help given...').replace('%PRE%',
                                                                                                              self.context.clean_prefix))
        embed.add_field(name='Command usage:', value=f"```css\n{self.get_minimal_command_signature(command)}\n```")
        try:
            preview = command.__original_kwargs__['preview']
            embed.set_image(url=preview)
        except KeyError:
            pass
        if command.aliases:
            embed.description = embed.description + f'\n\n**Aliases:**\n`{"`, `".join(command.aliases)}`'
        try:
            await command.can_run(self.context)
        except BaseException as e:
            try:
                if isinstance(e, discord.ext.commands.CheckAnyFailure):
                    for e in e.errors:
                        if not isinstance(e, commands.NotOwner):
                            raise e
                raise e
            except commands.MissingPermissions as error:
                embed.add_field(name='Permissions you\'re missing:',
                                value=', '.join(error.missing_permissions).replace('_', ' ').replace('guild',
                                                                                                     'server').title(),
                                inline=False)
            except commands.BotMissingPermissions as error:
                embed.add_field(name='Permissions i\'m missing:',
                                value=', '.join(error.missing_permissions).replace('_', ' ').replace('guild',
                                                                                                     'server').title(),
                                inline=False)
            except commands.NotOwner:
                embed.add_field(name='Rank you are missing:', value='Bot owner', inline=False)
            except commands.PrivateMessageOnly:
                embed.add_field(name='Cant execute this here:', value='Can only be executed in DMs.', inline=False)
            except commands.NoPrivateMessage:
                embed.add_field(name='Cant execute this here:', value='Can only be executed in a server.', inline=False)
            except commands.DisabledCommand:
                embed.add_field(name='Cant execute this command:',
                                value='This command is restricted to slash commands.', inline=False)
            except Exception as exc:
                embed.add_field(name='Cant execute this command:', value='Unknown/unhandled reason.', inline=False)
                print(f'{command} failed to execute: {exc}')
        finally:
            await self.context.send(embed=embed, footer=False)

    async def send_cog_help(self, cog):
        entries = cog.get_commands()
        if entries:
            data = [self.get_minimal_command_signature(entry) for entry in entries]
            embed = discord.Embed(title=f"`{cog.qualified_name}` category commands",
                                  description='**Description:**\n' + cog.description.replace('%PRE%',
                                                                                             self.context.clean_prefix))
            embed.description = embed.description + f'\n\n**Commands:**\n```css\n{newline.join(data)}\n```' \
                                                    f'\n`[G]` means group, these have sub-commands.' \
                                                    f'\n`(C)` means command, these do not have sub-commands.'
            await self.context.send(embed=embed, footer=False)
        else:
            await self.context.send(f'No commands found in {cog.qualified_name}')

    async def send_group_help(self, group):
        embed = discord.Embed(title=f"information about: `{self.context.clean_prefix}{group}`",
                              description='**Description:**\n' + (group.help or 'No help given...').replace('%PRE%',
                                                                                                            self.context.clean_prefix))
        embed.add_field(name='Command usage:', value=f"```css\n{self.get_minimal_command_signature(group)}\n```")
        if group.aliases:
            embed.description = embed.description + f'\n\n**Aliases:**\n`{"`, `".join(group.aliases)}`'
        if group.commands:
            formatted = '\n'.join([self.get_minimal_command_signature(c) for c in group.commands])
            embed.add_field(name='Sub-commands for this command:',
                            value=f'```css\n{formatted}\n```**Do `{self.context.clean_prefix}help command subcommand` for more info on a sub-command**',
                            inline=False)
        # noinspection PyBroadException
        try:
            await group.can_run(self.context)
        except commands.MissingPermissions as error:
            embed.add_field(name='Permissions you\'re missing:',
                            value=', '.join(error.missing_permissions).replace('_', ' ').replace('guild',
                                                                                                 'server').title(),
                            inline=False)
        except commands.BotMissingPermissions as error:
            embed.add_field(name='Permissions i\'m missing:',
                            value=', '.join(error.missing_permissions).replace('_', ' ').replace('guild',
                                                                                                 'server').title(),
                            inline=False)

        except commands.NotOwner:
            embed.add_field(name='Rank you are missing:', value='Bot owner', inline=False)
        except commands.PrivateMessageOnly:
            embed.add_field(name='Cant execute this here:', value='Can only be executed in DMs.', inline=False)
        except commands.NoPrivateMessage:
            embed.add_field(name='Cant execute this here:', value='Can only be executed in a server.', inline=False)
        except commands.DisabledCommand:
            embed.add_field(name='Cant execute this command:',
                            value='This command is restricted to slash commands.', inline=False)
        except Exception as exc:
            embed.add_field(name='Cant execute this command:', value='Unknown error.', inline=False)
            print(f'{group} failed to execute: {exc}')
        finally:
            await self.context.send(embed=embed)

    def command_not_found(self, string):
        return string

    def subcommand_not_found(self, command, string):
        if isinstance(command, commands.Group) and len(command.all_commands) > 0:
            return command.qualified_name + string
        return command.qualified_name

    async def send_error_message(self, error):
        matches = difflib.get_close_matches(error, self.context.bot.cogs.keys())
        if matches:
            confirm = await self.context.confirm(
                message=f"Sorry but i couldn't recognise {error} as one of my categories!"
                        f"\n{f'**did you mean... `{matches[0]}`?**' if matches else ''}",
                delete_after_confirm=True, delete_after_timeout=True,
                delete_after_cancel=True, buttons=(('✅', f'See {matches[0]}'[0:80], discord.ButtonStyle.blurple),
                                                   ('🗑', None, discord.ButtonStyle.red)), timeout=15)
            if confirm is True:
                return await self.send_cog_help(self.context.bot.cogs[matches[0]])
            return
        else:
            command_names = []
            for command in [c for c in self.context.bot.commands]:
                # noinspection PyBroadException
                try:
                    if await command.can_run(self.context):
                        command_names.append([command.name] + command.aliases)
                except:
                    continue
            command_names = list(itertools.chain.from_iterable(command_names))
            matches = difflib.get_close_matches(error, command_names)
            if matches:
                confirm = await self.context.confirm(
                    message=f"Sorry but i couldn't recognise {error} as one of my commands!"
                            f"\n{f'**did you mean... `{matches[0]}`?**' if matches else ''}",
                    delete_after_confirm=True, delete_after_timeout=True,
                    delete_after_cancel=True, buttons=(('✅', f'See {matches[0]}'[0:80], discord.ButtonStyle.blurple),
                                                       ('🗑', None, discord.ButtonStyle.red)), timeout=15)
                if confirm is True:
                    return await self.send_command_help(self.context.bot.get_command(matches[0]))
                return

        await self.context.send(
            f"Sorry but i couldn't recognise \"{discord.utils.remove_markdown(error)}\" as one of my commands or categories!"
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
        help_command.command_attrs = {
            'help': 'Shows help about a command or category, it can also display other useful information, such as '
                    'examples on how to use the command, or special syntax that can be used for a command, for example, '
                    'in the `welcome message` command, it shows all available special tags.',
            'name': 'help', 'slash_command': True}
        help_command.cog = self
        bot.help_command = help_command
        self.select_emoji = constants.INFORMATION_SOURCE
        self.select_brief = 'Bot Information commands.'

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

    def oauth(self, perms: discord.Permissions = 0):
        """ Generates a discord oauth url """
        return discord.utils.oauth_url(self.bot.user.id,
                                       permissions=discord.Permissions(perms),
                                       scopes=('applications.commands', 'bot'))

    @commands.command(help="Sends a link to invite the bot to your server")
    async def invite(self, ctx: CustomContext):
        if not self.bot.is_ready():
            await ctx.trigger_typing()
            await self.bot.wait_until_ready()
        embed = discord.Embed(
            title="Invite me to your server!",
            description=f"\n• [No Permissions]({self.oauth(0)})"
                        f"\n• [Minimal Permissions]({self.oauth(274948541504)})"
                        f"\n• **[Mod Permissions]({self.oauth(294171045078)})** ⭐"
                        f"\n• [Admin Permissions]({self.oauth(8)})"
                        f"\n• [All Permissions]({self.oauth(549755813887)}) <:certified_moderator:895393984308981930>")
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        view = discord.ui.View()
        view.add_item(discord.ui.Button(emoji='⭐', label='Recommended', url=self.oauth(294171045078)))
        view.add_item(discord.ui.Button(emoji='<:certified_moderator:895393984308981930>', label='All',
                                        url=self.oauth(549755813887)))
        await ctx.send(embed=embed, view=view)

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
        total = 0
        guilds = 0
        for guild in self.bot.guilds:
            guilds += 1
            if guild.unavailable:
                continue

            total_members += guild.member_count
            for channel in guild.channels:
                total += 1
                if isinstance(channel, discord.TextChannel):
                    text += 1
                elif isinstance(channel, discord.VoiceChannel):
                    voice += 1
        avg = [(len(g.bots) / g.member_count) * 100 for g in self.bot.guilds]

        embed.add_field(name='Members', value=f'{total_members:,} total\n{total_unique:,} unique')
        embed.add_field(name='Channels', value=f'{total:,} total\n{text:,} text\n{voice:,} voice')

        memory_usage = psutil.Process().memory_full_info().uss / 1024 ** 2
        cpu_usage = psutil.cpu_percent()

        embed.add_field(name='Process', value=f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU')
        embed.add_field(name='Bot servers',
                        value=f"**total servers:** {guilds}\n**avg bot/human:** {round(sum(avg) / len(avg), 2)}%")
        embed.add_field(name='Command info:',
                        value=f"**Last reboot:**\n{self.get_bot_uptime()}"
                              f"\n**Last reload:**\n{self.get_bot_last_rall()}")
        try:
            embed.add_field(name='Lines', value=f"Lines: {await count_lines('DuckBot/', '.py'):,}"
                                                f"\nFunctions: {await count_others('DuckBot/', '.py', 'def '):,}"
                                                f"\nClasses: {await count_others('DuckBot/', '.py', 'class '):,}")
        except FileNotFoundError:
            pass

        version = pkg_resources.get_distribution('discord.py').version
        embed.set_footer(text=f'Made with discord.py v{version} 💖', icon_url='http://i.imgur.com/5BFecvA.png')
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)

    @commands.command(aliases=['sourcecode', 'code'],
                      usage="[command|command.subcommand]")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def source(self, ctx, *, command: str = None):
        """
        Links to the bots code, or a specific command's
        """
        # noinspection PyGlobalUndefined
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
            obj = 'help'
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

    @commands.command(usage=None)
    async def news(self, ctx: CustomContext, *, _=None, return_embed: typing.Optional[bool] = True) -> typing.Optional[discord.Embed]:
        """
        Shows the latest changes of the bot. ""
        """
        embed = discord.Embed(title="📰 Latest News - <t:1636731000:d> (<t:1636731000:R>)", colour=ctx.colour,
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
                                          f"\n> Run `{ctx.clean_prefix}counting` for more info!"
                                          f"\n"
                                          f"\n> **\🎤 <t:1634654000:R> New `lyrics` command to search lyrics!**"
                                          f"\n"
                                          f"\n> **\⌨ <t:1634660000:R> New `type-race` command!**"
                                          f"\n> _See who of your friends can type the word the fastest. **No copy paste!**_"
                                          f"\n"
                                          f"\n> **\📸 <t:1635068000:R> New image manipulation commands!**"
                                          f"\n> do `{ctx.clean_prefix}help image` for more information"
                                          f"\n"
                                          f"\n> **\📜 <t:1635314000:R> __NEW logging module__**"
                                          f"\n> Log all your server's events! Do `{ctx.clean_prefix} log` for more info."
                                          f"\n"
                                          f"\n> **\📜 <t:1635359000:R> auto logging setup command**"
                                          f"\n> Creates all the logging channels for you: do `{ctx.clean_prefix} log auto-setup`"
                                          f"\n"
                                          f"\n> **\🎶 <t:1636421000:R> music commands overhauled**"
                                          f"\n> Music commands should be better and music quality should be superior."
                                          f"\n"
                                          f"\n> **\🔎 <t:1636731000:R> New search options when enqueueing tracks**"
                                          f"\n> Commands for music added: `search`, `search-now`, `search-next`"
                              )
        if return_embed is True:
            return embed
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

    @commands.command()
    async def vote(self, ctx):
        embed = discord.Embed(title='Here\'s some buttons:')
        await ctx.send(embed=embed, view=InvSrc())
