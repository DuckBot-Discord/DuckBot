import asyncio

import discord
from discord.ext import commands, menus


async def setup(bot):
    await bot.add_cog(About(bot))


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

    @menus.button("\N{INFORMATION SOURCE}\ufe0f", position=menus.Last(3))
    async def show_help(self, payload):
        """shows this message"""
        embed = discord.Embed(title="Paginator help", description="Hello! Welcome to the help page.")
        messages = []
        for (emoji, button) in self.buttons.items():
            messages.append(f"{emoji}: {button.action.__doc__}")

        embed.add_field(
            name="What are these reactions for?",
            value="\n".join(messages),
            inline=False,
        )
        embed.set_footer(text=f"We were on page {self.current_page + 1} before this message.")
        await self.message.edit(content=None, embed=embed)

        async def go_back_to_current_page():
            await asyncio.sleep(30.0)
            await self.show_page(self.current_page)

        self.bot.loop.create_task(go_back_to_current_page())

    @menus.button("\N{INPUT SYMBOL FOR NUMBERS}", position=menus.Last(1.5), lock=False)
    async def numbered_page(self, payload):
        """lets you type a page number to go to"""
        if self.input_lock.locked():
            return

        async with self.input_lock:
            channel = self.message.channel
            author_id = payload.user_id
            to_delete = [await channel.send("What page do you want to go to?")]

            def message_check(m):
                return m.author.id == author_id and channel == m.channel and m.content.isdigit()

            try:
                msg = await self.bot.wait_for("message", check=message_check, timeout=30.0)
            except asyncio.TimeoutError:
                to_delete.append(await channel.send("Took too long."))
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
        self.add_item(
            discord.ui.Button(
                emoji="<:topgg:870133913102721045>",
                label="top.gg",
                url="https://top.gg/bot/788278464474120202#/",
            )
        )
        self.add_item(
            discord.ui.Button(
                emoji="<:botsgg:870134146972938310>",
                label="bots.gg",
                url="https://discord.bots.gg/bots/788278464474120202",
            )
        )


class ServerInvite(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(
            discord.ui.Button(
                emoji="<:servers:870152102759006208>",
                label="discord.gg/TdRfGKg8Wh",
                url="https://discord.gg/TdRfGKg8Wh",
            )
        )


class InvMe(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                emoji="<:invite:860644752281436171>",
                label="Invite me",
                url="https://discord.com/api/oauth2/authorize?client_id="
                "788278464474120202&permissions=8&scope=bot%20applications.commands",
            )
        )


class InvSrc(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                emoji="<:invite:860644752281436171>",
                label="Invite me",
                url="https://discord.com/api/oauth2/authorize?client_id="
                "788278464474120202&permissions=8&scope=bot%20applications.commands",
            )
        )
        self.add_item(
            discord.ui.Button(
                emoji="<:github:744345792172654643>",
                label="Source code",
                url="https://github.com/LeoCx1000/discord-bots",
            )
        )

    @discord.ui.button(
        label="Vote",
        style=discord.ButtonStyle.gray,
        emoji="<:topgg:870133913102721045>",
        custom_id="BotVoteSites",
    )
    async def votes(self, button: discord.ui.Button, interaction: discord.Interaction):
        embed = discord.Embed(
            description="<:topgg:870133913102721045> **vote here!** <:botsgg:870134146972938310>",
            color=discord.Colour.blurple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, view=InviteButtons())

    @discord.ui.button(
        label="Discord Server",
        style=discord.ButtonStyle.gray,
        emoji="<:servers:870152102759006208>",
        custom_id="ServerInvite",
    )
    async def invite(self, button: discord.ui.Button, interaction: discord.Interaction):
        embed = discord.Embed(
            description="<:servers:870152102759006208> **Join my server!** <:servers:870152102759006208>"
            "\nNote that this **will not ask for consent** to join! "
            "\nIt will just yoink you into the server",
            color=discord.Colour.blurple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, view=ServerInvite())


class HelpMenu(DuckPaginator):
    def __init__(self, source):
        super().__init__(source)

    @menus.button("\N{WHITE QUESTION MARK ORNAMENT}", position=menus.Last(5))
    async def show_bot_help(self, payload):
        """shows how to use the bot"""

        embed = discord.Embed(title="Using the bot", colour=discord.Colour.blurple())
        embed.title = "Using the bot"
        embed.description = "Hello! Welcome to the help page."

        entries = (
            ("<argument>", "This means the argument is __**required**__."),
            ("[argument]", "This means the argument is __**optional**__."),
            ("[A|B]", "This means that it can be __**either A or B**__."),
            (
                "[argument...]",
                "This means you can have multiple arguments.\n"
                "Now that you know the basics, it should be noted that...\n"
                "__**You do not type in the brackets!**__",
            ),
        )

        embed.add_field(
            name="How do I use this bot?",
            value="Reading the bot signature is pretty simple.",
        )

        for name, value in entries:
            embed.add_field(name=name, value=value, inline=False)

        embed.set_footer(text=f"We were on page {self.current_page + 1} before this message.")
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
            self.title = f"{self.group.qualified_name} Commands"
            self.description = self.group.description

    async def format_page(self, menu, commands):
        embed = discord.Embed(
            title=self.title,
            description=self.description,
            colour=discord.Colour.blurple(),
        )

        for command in commands:
            signature = f"{command.qualified_name} {command.signature}"
            if command.help:
                command_help = command.help.replace("%PRE%", self.prefix)
            else:
                command_help = "No help given..."
            embed.add_field(name=signature, value=f"```yaml\n{command_help}```", inline=False)

        maximum = self.get_max_pages()
        if maximum > 1:
            embed.set_author(name=f"Page {menu.current_page + 1}/{maximum} ({len(self.entries)} commands)")

        embed.set_footer(text=f'Use "{self.prefix}help command" for more info on a command.')
        return embed

    def get_minimal_command_signature(self, group):
        return "%s%s %s" % (self.prefix, group.qualified_name, group.signature)


class MyHelp(commands.HelpCommand):

    # Formatting
    def get_minimal_command_signature(self, command):
        return "%s%s %s" % (
            self.context.clean_prefix,
            command.qualified_name,
            command.signature,
        )

    @staticmethod
    def get_command_name(command):
        return "%s" % command.qualified_name

    # !help
    async def send_bot_help(self, mapping):
        embed = discord.Embed(
            color=discord.Colour.blurple(),
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
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(name=self.context.author, icon_url=self.context.author.display_avatar.url)
        all_cogs = []
        cog_index = []
        ignored_cogs = ["Jishaku", "Events", "Handler", "Bot Management"]
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
        nl = "\n"

        embed.add_field(
            name=f"Available categories [{len(all_cogs)}]",
            value=f"```fix\n{nl.join(all_cogs)}``````diff"
            f'\n! "help [number]"'
            f"\n- to get help on"
            f"\n- a category by"
            f"\n- it's number."
            f"\n```",
        )

        embed.add_field(
            name="📰 Latest News - <t:69696969:d> (<t:69696969:R>)",
            value=f"""
Wow
this is so sad.
this is gone! :o
Yeah I had the realization that it was not very human friendly... TMI 
""",
        )

        embed.set_footer(text=f'Help command inspiration and credits at "{self.context.clean_prefix}about"')
        channel = self.get_destination()
        await channel.send(embed=embed, view=InvSrc())

    def common_command_formatting(self, embed_like, command):
        embed_like.title = self.get_command_signature(command)
        if command.description:
            embed_like.description = f"{command.description}\n\n```yaml\n{command.help}\n```"
        else:
            embed_like.description = command.help or "```yaml\nNo help found...\n```"

    # !help <command>
    async def send_command_help(self, command):
        alias = command.aliases
        if command.help:
            command_help = command.help.replace("%PRE%", self.context.clean_prefix)
        else:
            command_help = "No help given..."
        if alias:
            embed = discord.Embed(
                color=discord.Colour.blurple(),
                title=f"information about: {self.context.clean_prefix}{command}",
                description=f"""
```yaml
      usage: {self.get_minimal_command_signature(command)}
    aliases: {', '.join(alias)}
description: {command_help}
```""",
            )
        else:
            embed = discord.Embed(
                color=discord.Colour.blurple(),
                title=f"information about {self.context.clean_prefix}{command}",
                description=f"""```yaml
      usage: {self.get_minimal_command_signature(command)}
description: {command_help}
```""",
            )
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
        if cmd.lower() == "credits":
            charles = self.context.bot.get_user(505532526257766411) or "Charles#5244"
            dutchy = self.context.bot.get_user(171539705043615744) or "Dutchy#6127"
            embed = discord.Embed(
                color=self.context.me.color,
                description=f"The main page of the help command was "
                f"not designed by me. It is inspired by "
                f"**{dutchy}**'s **{charles}** "
                f"bot.\n\ncheck it out at "
                f"https://charles-bot.com/ 💞",
            )
            if isinstance(charles, (discord.User, discord.Member)):
                embed.set_thumbnail(url=charles.display_avatar.url)
            embed.set_author(
                icon_url=self.context.author.display_avatar.url,
                name=f"{self.context.author} - help page credits",
            )
            return await channel.send(embed=embed)

        if cmd.isdigit():
            if self.context.bot.first_help_sent is True:
                try:
                    return await self.context.send_help(self.context.bot.all_cogs[int(cmd) - 1])
                except IndexError:
                    pass
            else:
                return await channel.send(
                    f"Whoops! I don't have the list of categories loaded 😔"
                    f"\nDo `{self.context.clean_prefix}help` to load it! 💞"
                )
        await channel.send(f"{error}" f"\nDo `{self.context.clean_prefix}help` for a list of available commands! 💞")

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
