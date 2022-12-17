from __future__ import annotations
import re
import asyncio
import traceback
from types import SimpleNamespace
from typing import Any, Dict, Optional
import discord
import typing

import humanize
from discord.ext import commands
from discord.ext.commands import Paginator as CommandPaginator
from discord.ext import menus

from DuckBot.helpers import helper, constants
from DuckBot.__main__ import CustomContext

sep = '\u200b '


class InviteButtons(discord.ui.View):
    """Buttons to the top.gg and bots.gg voting sites"""

    def __init__(self):
        super().__init__()
        self.add_item(
            discord.ui.Button(emoji=constants.TOP_GG, label='top.gg', url="https://top.gg/bot/788278464474120202#/")
        )
        self.add_item(
            discord.ui.Button(
                emoji=constants.BOTS_GG, label='bots.gg', url="https://discord.bots.gg/bots/788278464474120202"
            )
        )


class ServerInvite(discord.ui.View):
    """Buttons to the support server invite"""

    def __init__(self):
        super().__init__()
        self.add_item(
            discord.ui.Button(
                emoji=constants.SERVERS_ICON, label='Join the Support Server!', url="https://discord.gg/TdRfGKg8Wh"
            )
        )


class OzAd(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label='Advertisement', style=discord.ButtonStyle.gray, emoji=constants.MINECRAFT_LOGO, custom_id='OzSmpAd'
    )
    async def advertisement(self,interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            description="\u200b"
            "\nWe’re not in Kansas anymore Toto. 🧙"
            "\n"
            "\n**Welcome to OZ SMP, your home away from home.** "
            "\nWe all know there's no place like home. "
            "Inspired by The Wizard of OZ, we are a small tight knit community "
            "from across the world with 20 active players and we’re "
            "looking for more to join us!"
            "\n"
            "\n**We’re a 1.17.1 JAVA server complete with McMMO, TPA, "
            "nether highways, `/sethome` and more!**"
            "\n"
            "\nCome join us, and remember- There's no place like home."
            "\n"
            "\n**Here's our [discord server](https://discord.gg/z5tuvXGFqX "
            "\"https://discord.gg/z5tuvXGFqX\")**"
            "\n**Take a peek at our [interactive web map](http://oz_smp.apexmc.co:7380"
            " \"http://oz_smp.apexmc.co:7380\")**"
            "\n**Server IP:** `OZ.apexmc.co`"
            "\n"
            "\n> _Note: You need to join the discord for whitelisting. "
            "Whitelisting is automatic, just read and agree to the rules._ 💞",
            color=discord.Colour.blurple(),
        )
        embed.set_image(
            url="https://media.discordapp.net/attachments/861134063489777664/888558076804857876/"
            "PicsArt_09-03-03.png?width=806&height=676"
        )
        embed.set_author(name="Hey! Thanks for being interested in OZ SMP", icon_url="https://i.imgur.com/CC9AWcz.png")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class InvSrc(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                emoji=constants.INVITE,
                label='Invite me',
                url="https://discord.com/api/oauth2/authorize?client_id="
                "788278464474120202&permissions=8&scope=bot%20applications.commands",
            )
        )
        self.add_item(
            discord.ui.Button(emoji=constants.GITHUB, label='Source code', url="https://github.com/LeoCx1000/discord-bots")
        )

    @discord.ui.button(label='Vote', style=discord.ButtonStyle.gray, emoji=constants.TOP_GG, custom_id='BotVoteSites')
    async def votes(self,interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            description=f"{constants.TOP_GG} **vote here!** {constants.TOP_GG}", color=discord.Colour.blurple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, view=InviteButtons())

    @discord.ui.button(
        label='Support Server', style=discord.ButtonStyle.gray, emoji=constants.SERVERS_ICON, custom_id='ServerInvite'
    )
    async def invite(self,interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            description=f"{constants.SERVERS_ICON} **Join my server!** {constants.SERVERS_ICON}"
            "\nNote that this **will not ask for consent** to join! "
            "\nIt will just yoink you into the server",
            color=discord.Colour.blurple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, view=ServerInvite())


class ViewPaginator(discord.ui.View):
    def __init__(
        self,
        source: menus.PageSource,
        *,
        ctx: commands.Context,
        check_embeds: bool = True,
        compact: bool = False,
    ):
        super().__init__()
        self.source: menus.PageSource = source
        self.check_embeds: bool = check_embeds
        self.ctx: commands.Context = ctx
        self.message: Optional[discord.Message] = None
        self.current_page: int = 0
        self.compact: bool = compact
        self.input_lock = asyncio.Lock()
        self.clear_items()
        self.fill_items()

    def fill_items(self) -> None:
        if not self.compact:
            self.numbered_page.row = 1
            self.stop_pages.row = 1

        if self.source.is_paginating():
            max_pages = self.source.get_max_pages()
            use_last_and_first = max_pages is not None and max_pages >= 2
            if use_last_and_first:
                self.add_item(self.go_to_first_page)  # type: ignore
            self.add_item(self.go_to_previous_page)  # type: ignore
            if not self.compact:
                self.add_item(self.go_to_current_page)  # type: ignore
            self.add_item(self.go_to_next_page)  # type: ignore
            if use_last_and_first:
                self.add_item(self.go_to_last_page)  # type: ignore
            if not self.compact:
                self.add_item(self.numbered_page)  # type: ignore
            self.add_item(self.stop_pages)  # type: ignore

    async def _get_kwargs_from_page(self, page: int) -> Dict[str, Any]:
        value = await discord.utils.maybe_coroutine(self.source.format_page, self, page)
        if isinstance(value, dict):
            return value
        elif isinstance(value, str):
            return {'content': value, 'embed': None}
        elif isinstance(value, discord.Embed):
            return {'embed': value, 'content': None}
        else:
            return {}

    async def show_page(self, interaction: discord.Interaction, page_number: int) -> None:
        page = await self.source.get_page(page_number)
        self.current_page = page_number
        kwargs = await self._get_kwargs_from_page(page)
        self._update_labels(page_number)
        if kwargs:
            if interaction.response.is_done():
                if self.message:
                    await self.message.edit(**kwargs, view=self)
            else:
                await interaction.response.edit_message(**kwargs, view=self)

    def _update_labels(self, page_number: int) -> None:
        self.go_to_first_page.disabled = page_number == 0
        if self.compact:
            max_pages = self.source.get_max_pages()
            self.go_to_last_page.disabled = max_pages is None or (page_number + 1) >= max_pages
            self.go_to_next_page.disabled = max_pages is not None and (page_number + 1) >= max_pages
            self.go_to_previous_page.disabled = page_number == 0
            return

        self.go_to_current_page.label = str(page_number + 1)
        self.go_to_previous_page.label = str(page_number)
        self.go_to_next_page.label = str(page_number + 2)
        self.go_to_next_page.disabled = False
        self.go_to_previous_page.disabled = False
        self.go_to_first_page.disabled = False

        max_pages = self.source.get_max_pages()
        if max_pages is not None:
            self.go_to_last_page.disabled = (page_number + 1) >= max_pages
            if (page_number + 1) >= max_pages:
                self.go_to_next_page.disabled = True
                self.go_to_next_page.label = '…'
            if page_number == 0:
                self.go_to_previous_page.disabled = True
                self.go_to_previous_page.label = '…'

    async def show_checked_page(self, interaction: discord.Interaction, page_number: int) -> None:
        max_pages = self.source.get_max_pages()
        try:
            if max_pages is None:
                # If it doesn't give maximum pages, it cannot be checked
                await self.show_page(interaction, page_number)
            elif max_pages > page_number >= 0:
                await self.show_page(interaction, page_number)
        except IndexError:
            # An error happened that can be handled, so ignore it.
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id in (self.ctx.bot.owner_id, self.ctx.author.id):
            return True
        await interaction.response.send_message(f'This menu belongs to **{self.ctx.author}**, sorry! 💖', ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        if self.message:
            await self.message.edit(view=None)

    async def on_error(self, error: Exception, item: discord.ui.Item, interaction: discord.Interaction) -> None:
        if interaction.user.id in self.ctx.bot.owner_ids:
            await self.ctx.reply(
                '```py' + ''.join(traceback.format_exception(etype=None, value=error, tb=error.__traceback__) + '\n```')
            )
        if interaction.response.is_done():
            await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
        else:
            try:
                await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)
            except discord.NotFound:
                for child in self.children:
                    child.disabled = True
                await self.message.edit(view=self)

    async def start(self, *, start_message: discord.Message = None) -> None:
        if self.check_embeds and not self.ctx.channel.permissions_for(self.ctx.me).embed_links:
            await self.ctx.send('Bot does not have embed links permission in this channel.')
            return

        await self.source._prepare_once()
        page = await self.source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        self._update_labels(0)
        if not start_message:
            self.message = await self.ctx.send(**kwargs, view=self)
        else:
            self.message = await start_message.edit(**kwargs, view=self)

    @discord.ui.button(label='≪', style=discord.ButtonStyle.grey)
    async def go_to_first_page(self,interaction: discord.Interaction, button: discord.ui.Button):
        """go to the first page"""
        await self.show_page(interaction, 0)

    @discord.ui.button(label='◀', style=discord.ButtonStyle.blurple)
    async def go_to_previous_page(self,interaction: discord.Interaction, button: discord.ui.Button):
        """go to the previous page"""
        await self.show_checked_page(interaction, self.current_page - 1)

    @discord.ui.button(label='◽', style=discord.ButtonStyle.grey, disabled=True)
    async def go_to_current_page(self,interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label='▶', style=discord.ButtonStyle.blurple)
    async def go_to_next_page(self,interaction: discord.Interaction, button: discord.ui.Button):
        """go to the next page"""
        await self.show_checked_page(interaction, self.current_page + 1)

    @discord.ui.button(label='≫', style=discord.ButtonStyle.grey)
    async def go_to_last_page(self,interaction: discord.Interaction, button: discord.ui.Button):
        """go to the last page"""
        # The call here is safe because it's guarded by skip_if
        await self.show_page(interaction, self.source.get_max_pages() - 1)

    @discord.ui.button(label='Skip to page...', style=discord.ButtonStyle.grey)
    async def numbered_page(self,interaction: discord.Interaction, button: discord.ui.Button):
        """lets you type a page number to go to"""
        if self.input_lock.locked():
            await interaction.response.send_message('Already waiting for your response...', ephemeral=True)
            return

        if self.message is None:
            return

        async with self.input_lock:
            channel = self.message.channel
            author_id = interaction.user and interaction.user.id
            await interaction.response.send_message('What page do you want to go to?', ephemeral=True)

            def message_check(m):
                return m.author.id == author_id and channel == m.channel and m.content.isdigit()

            try:
                msg = await self.ctx.bot.wait_for('message', check=message_check, timeout=30.0)
            except asyncio.TimeoutError:
                await interaction.followup.send('Took too long.', ephemeral=True)
                await asyncio.sleep(5)
            else:
                page = int(msg.content)
                await msg.delete()
                await self.show_checked_page(interaction, page - 1)

    @discord.ui.button(emoji='🗑', style=discord.ButtonStyle.red)
    async def stop_pages(self,interaction: discord.Interaction, button: discord.ui.Button):
        """stops the pagination session."""
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()


class FieldPageSource(menus.ListPageSource):
    """A page source that requires (field_name, field_value) tuple items."""

    def __init__(self, entries, *, per_page=12):
        super().__init__(entries, per_page=per_page)
        self.embed = discord.Embed(colour=discord.Colour.blurple())

    async def format_page(self, menu, entries):
        self.embed.clear_fields()
        self.embed.description = None

        for key, value in entries:
            self.embed.add_field(name=key, value=value, inline=False)

        maximum = self.get_max_pages()
        if maximum > 1:
            text = f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} entries)'
            self.embed.set_footer(text=text)

        return self.embed


class TextPageSource(menus.ListPageSource):
    def __init__(self, text, *, prefix='```', suffix='```', max_size=2000):
        pages = CommandPaginator(prefix=prefix, suffix=suffix, max_size=max_size - 200)
        for line in text.split('\n'):
            pages.add_line(line)

        super().__init__(entries=pages.pages, per_page=1)

    async def format_page(self, menu, content):
        maximum = self.get_max_pages()
        if maximum > 1:
            return f'{content}\nPage {menu.current_page + 1}/{maximum}'
        return content


class SimplePageSource(menus.ListPageSource):
    def __init__(self, entries, *, per_page):
        super().__init__(entries, per_page=per_page)
        self.embed = discord.Embed(
            title='Here are all members with a nick, sorted by name.', timestamp=discord.utils.utcnow()
        )

    async def format_page(self, menu, entries):
        pages = entries

        maximum = self.get_max_pages()
        if maximum > 1:
            footer = f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} entries)'
            self.embed.set_footer(text=footer)

        self.embed.description = '\n'.join(pages)
        return self.embed


class EnumeratedPageSource(menus.ListPageSource):
    def __init__(self, entries, *, per_page, embed_title: str = None):
        super().__init__(entries, per_page=per_page)
        self.embed = discord.Embed(title=embed_title, timestamp=discord.utils.utcnow())

    async def format_page(self, menu, entries):
        pages = []
        for index, entry in enumerate(entries, start=menu.current_page * self.per_page):
            pages.append(f'{index + 1}. {entry}')

        maximum = self.get_max_pages()
        if maximum > 1:
            footer = f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} entries)'
            self.embed.set_footer(text=footer)

        self.embed.description = '\n'.join(pages)
        return self.embed


class SimplePages(ViewPaginator):
    """A simple pagination session reminiscent of the old Pages interface.

    Basically an embed with some normal formatting.
    """

    def __init__(self, entries, *, ctx: commands.Context, per_page: int = 12):
        super().__init__(SimplePageSource(entries, per_page=per_page), ctx=ctx)
        self.embed = discord.Embed(colour=discord.Colour.blurple())


class UrbanPageSource(menus.ListPageSource):
    BRACKETED = re.compile(r'(\[(.+?)\])')

    def __init__(self, data):
        super().__init__(entries=data, per_page=1)

    def cleanup_definition(self, definition, *, regex=BRACKETED):
        def repl(m):
            word = m.group(2)
            return f'[{word}](http://{word.replace(" ", "-")}.urbanup.com)'

        ret = regex.sub(repl, definition)
        if len(ret) >= 2048:
            return ret[0:2000] + ' [...]'
        return ret

    async def format_page(self, menu, entry):
        maximum = self.get_max_pages()
        title = f'{entry["word"]}: {menu.current_page + 1} out of {maximum}' if maximum else entry['word']
        embed = discord.Embed(title=title, colour=discord.Colour.blurple(), url=entry['permalink'])
        embed.set_footer(text=f'by {entry["author"]}')
        embed.description = self.cleanup_definition(entry['definition'])

        try:
            up, down = entry['thumbs_up'], entry['thumbs_down']
        except KeyError:
            pass
        else:
            embed.add_field(name='Votes', value=f'\N{THUMBS UP SIGN} {up} \N{THUMBS DOWN SIGN} {down}', inline=False)

        try:
            date = discord.utils.parse_time(entry['written_on'][0:-1])
        except (ValueError, KeyError):
            pass
        else:
            embed.timestamp = date

        return embed


class ServerInfoPageSource(menus.ListPageSource):
    def __init__(self, guilds: typing.List[discord.Guild], ctx: CustomContext):
        self.guilds = guilds
        self.context = ctx
        super().__init__(guilds, per_page=1)

    async def format_page(self, menu, guild: discord.Guild) -> discord.Embed:
        enabled_features = []
        features = set(guild.features)

        for feature, label in constants.GUILD_FEATURES.items():
            if feature in features:
                enabled_features.append(f'{self.context.tick(True)} {label}')

        embed = discord.Embed(title=guild.name)

        embed.add_field(
            name=f"{constants.RICH_PRESENCE} Features:",
            value=(('\n'.join(enabled_features) if enabled_features else 'No features...') + '\n\u200b _ _'),
            inline=True,
        )

        embed.add_field(
            name=f"{constants.INFORMATION_SOURCE} General Info:",
            value=f"🆔 {guild.id}"
            f"\n{constants.OWNER_CROWN} {guild.owner}"
            f"\n🌐 Server Region:\n╰ {helper.get_server_region(guild)}"
            f"\n{constants.VERIFICATION_LEVEL[guild.verification_level]} "
            f"{str(guild.verification_level).replace('_', ' ').replace('none', 'no').title()} Verification Level"
            f"\n📁 File size limit: {humanize.naturalsize(guild.filesize_limit)}"
            f"\n{constants.ROLES_ICON} Role amount: {len(guild.roles)}"
            f"\n\u200b _ _",
        )

        embed.add_field(
            name=f"{constants.INFORMATION_SOURCE} Server description:",
            value=guild.description or f"{constants.TOGGLES[False]} Description disabled!",
            inline=False,
        )

        embed.add_field(
            name=f"{constants.JOINED_SERVER} Created at:",
            value=f"{discord.utils.format_dt(guild.created_at, 'F')} ({discord.utils.format_dt(guild.created_at, 'R')})",
            inline=False,
        )

        embed.add_field(
            name=f"{constants.VERIFICATION_LEVEL[guild.verification_level]} Server content filter:",
            value=f"{constants.CONTENT_FILTER[guild.explicit_content_filter]}\n\u200b _ _",
            inline=False,
        )

        embed.add_field(
            name=f"{constants.RICH_PRESENCE} Channels:",
            value=f"{constants.VOICE_CHANNEL} "
            f"{len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])}"
            f"\n{constants.TEXT_CHANNEL} Channels: "
            f"{len([c for c in guild.channels if isinstance(c, discord.TextChannel)])}"
            f"\n{constants.CATEGORY_CHANNEL} Categories: "
            f"{len([c for c in guild.channels if isinstance(c, discord.CategoryChannel)])}"
            f"\n{constants.STAGE_CHANNEL} Stages: "
            f"{len([c for c in guild.channels if isinstance(c, discord.StageChannel)])}"
            f"\n{constants.TEXT_CHANNEL_WITH_THREAD} Threads: {len(guild.threads)}"
            f"\n╰ (only threads visible by me)",
            inline=True,
        )

        embed.add_field(
            name=f"{constants.EMOJI_GHOST} Emojis:",
            value=f"Static: {len([e for e in guild.emojis if not e.animated])}/{guild.emoji_limit} "
            f"\nAnimated: {len([e for e in guild.emojis if e.animated])}/{guild.emoji_limit} ",
            inline=True,
        )

        last_boost = max(guild.members, key=lambda m: m.premium_since or guild.created_at)
        if last_boost.premium_since is not None:
            boost = f"\n{last_boost}" f"\n╰ {discord.utils.format_dt(last_boost.premium_since, style='R')}"
        else:
            boost = "\n╰ No active boosters"

        embed.add_field(
            name=f"{constants.BOOST} Boosts:",
            value=f"{constants.GUILD_BOOST_LEVEL_EMOJI[str(guild.premium_tier)]} Level: {guild.premium_tier}"
            f"\n╰ Amount: {guild.premium_subscription_count}"
            f"\n**{constants.BOOST} Last booster:**{boost}",
        )

        embed.add_field(
            name=f'👥 Member information:',
            value=f"\n👤 Humans: {len([m for m in guild.members if not m.bot])} "
            f"\n🤖 Bots: {len([m for m in guild.members if m.bot])}"
            f"\n♾ Total: {guild.member_count}"
            f"\n📂 Limit: {guild.max_members}",
        )
        embed.add_field(
            name=f"{constants.ROLES_ICON} Member statuses:",
            value=f"\n{constants.statuses.ONLINE} Online: {len(list(filter(lambda m: m.status == discord.Status.online, guild.members)))}"
            f"\n{constants.statuses.IDLE} Idle: {len(list(filter(lambda m: m.status == discord.Status.idle, guild.members)))}"
            f"\n{constants.statuses.DND} DND: {len(list(filter(lambda m: m.status == discord.Status.do_not_disturb, guild.members)))}"
            f"\n{constants.statuses.OFFLINE} Offline: {len(list(filter(lambda m: m.status == discord.Status.offline, guild.members)))}",
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        return embed


class ServerEmotesEmbedPage(menus.ListPageSource):
    def __init__(self, data: list, guild: discord.Guild) -> discord.Embed:
        self.data = data
        self.guild = guild
        super().__init__(data, per_page=15)

    async def format_page(self, menu, entries):
        offset = menu.current_page * self.per_page
        embed = discord.Embed(
            title=f"{self.guild if isinstance(self.guild, discord.Guild) else 'DuckBot'}'s "
            f"emotes ({len(self.guild.emojis)})",
            description="\n".join(f'{i}. {v}' for i, v in enumerate(entries, start=offset)),
        )
        return embed


class CharacterInformationPageSource(menus.ListPageSource):
    async def format_page(self, menu, item):
        embed = discord.Embed(description="\n".join(item), title="ℹ Character information")
        return embed


def emoji_str(emoji: typing.Union[discord.Emoji, discord.PartialEmoji]) -> str:
    return f"*`{str(emoji)}`".replace('<', '<`*`')


class EmojiListPageSource(menus.ListPageSource):
    def __init__(self, data: list, ctx: CustomContext) -> discord.Embed:
        self.data = data
        self.ctx = ctx
        self.time = discord.utils.utcnow()
        super().__init__(data, per_page=1)

    async def format_page(self, menu, emoji):

        if isinstance(emoji, discord.Emoji):
            if emoji.roles:
                roles_formatted = ', '.join([role.mention for role in emoji.roles])
                roles_formatted = f"\n**Locked to:** {roles_formatted}"
            else:
                roles_formatted = ""
            if emoji.guild.me.guild_permissions.manage_emojis:
                fetched = await emoji.guild.fetch_emoji(emoji.id)
                creator = f"\n**Created by:** {fetched.user}"
            else:
                creator = ""

            embed = discord.Embed(
                color=0xF4D58C,
                timestamp=self.time,
                description=f"**Format:** {emoji_str(emoji)}"
                f"\n**Created at:** {discord.utils.format_dt(emoji.created_at)}"
                f"\n**Name:** {emoji.name} **Url:** [url]({emoji.url})"
                f"\n**Id:** {emoji.id}"
                f"\n**Server:** {emoji.guild}"
                f"{creator}"
                f"{roles_formatted}",
            )
            embed.set_footer(text=f'Requested by {self.ctx.author}', icon_url=self.ctx.author.display_avatar.url)
            embed.set_image(url=emoji.url)
            return embed

        elif isinstance(emoji, discord.PartialEmoji):
            embed = discord.Embed(
                color=0xF4D58C,
                timestamp=self.time,
                description=f"**Format:** {emoji_str(emoji)}"
                f"\n**Created at:** {discord.utils.format_dt(emoji.created_at)}"
                f"\n**Name:** {emoji.name}{sep*12}**Url:** [here]({emoji.url})"
                f"\n**Id:** {emoji.id}",
            )
            embed.set_footer(text=f'Requested by {self.ctx.author}', icon_url=self.ctx.author.display_avatar.url)
            embed.set_image(url=emoji.url)
            return embed
        else:
            return discord.Embed(description='something went wrong...')


class HelpMenuPageSource(menus.ListPageSource):
    def __init__(
        self, data: typing.List[SimpleNamespace], ctx: CustomContext, help_class: commands.HelpCommand
    ) -> discord.Embed:
        self.data = data
        self.ctx = ctx
        self.help = help_class
        super().__init__(data, per_page=1)

    async def format_page(self, menu, data):
        embed = discord.Embed(
            color=self.ctx.color,
            description=f"\n> 🔄 **Total Commands:** {len(list(self.ctx.bot.commands))} | **Usable by you (here):** "
            f"{len(await self.help.filter_commands(list(self.ctx.bot.commands), sort=True))} 🔄"
            f"\n> 📰 **Do `{self.ctx.clean_prefix}news` to see the latest additions to {self.ctx.me.display_name}** 📰"
            f"\n"
            f"\n```css"
            f"\n{self.ctx.clean_prefix}help [command|category|group] - get more info."
            f"\n``````fix"
            f"\n(c) means command - [g] means command group."
            f'\nGroups have sub-commands = do "help [group]"'
            f"\n```"
            f"\n",
        )
        embed.add_field(name=data[0], value=data[1])
        embed.set_footer(text="Click the blue buttons to navigate these pages")
        return embed


class VotesButton(discord.ui.Button):
    def __init__(self, label: str, emoji: str, button_style: discord.ButtonStyle, row: int = None):
        super().__init__(style=button_style, label=label, emoji=emoji, row=row)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            description=f"{constants.TOP_GG} **vote here!** {constants.TOP_GG}", color=discord.Colour.blurple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, view=InviteButtons())


class InviteButton(discord.ui.Button):
    def __init__(self, label: str, emoji: str, button_style: discord.ButtonStyle, row: int = None):
        super().__init__(style=button_style, label=label, emoji=emoji, row=row)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            description=f"{constants.SERVERS_ICON} **Join my server!** {constants.SERVERS_ICON}"
            "\nNote that this **will not ask for consent** to join! "
            "\nIt will just yoink you into the server",
            color=discord.Colour.blurple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, view=ServerInvite())


class PaginatedStringListPageSource(menus.ListPageSource):
    def __init__(self, entries, *, per_page=1, ctx: CustomContext):
        super().__init__(entries, per_page=per_page)
        self.ctx = ctx

    def format_page(self, menu, page):
        embed = discord.Embed(color=discord.Colour.blurple(), description=page)
        embed.set_author(icon_url=self.ctx.author.display_avatar.url, name=str(self.ctx.author))
        return embed


class StopButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, emoji='🗑')

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.view.stop()


class TodoListPaginator(ViewPaginator):
    def __init__(self, source: menus.PageSource, *, ctx: commands.Context, check_embeds: bool = True, compact: bool = False):
        super().__init__(source, ctx=ctx, check_embeds=check_embeds, compact=compact)

    def fill_items(self) -> None:
        super().fill_items()
        if not self.children:
            self.add_item(StopButton())

    async def on_timeout(self) -> None:
        if self.message:
            await self.message.edit(view=None)
        self.stop()


class NodesMenu(menus.ListPageSource):
    """Nodes paginator class."""

    def __init__(self, data, ctx):
        self.data = data
        self.ctx = ctx
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):
        offset = menu.current_page * self.per_page
        embed = discord.Embed(title='<:rich_presence:658538493521166336> Node Stats', colour=self.ctx.color)

        for i, v in enumerate(entries, start=offset):
            embed.add_field(name=''.join(v.keys()), value=f'╰ {"".join(v.values())}', inline=True)
            # embed.add_field(name='Identifier',value=f'╰ {v[1]}', inline=False)
        return embed


class QueueMenu(menus.ListPageSource):
    def __init__(self, data, ctx) -> discord.Embed:
        self.data = data
        self.ctx: CustomContext = ctx
        super().__init__(data, per_page=10)

    async def format_page(self, menu, entries):
        offset = menu.current_page * self.per_page

        embed = discord.Embed(
            title=f'{len(self.data)} songs in the queue' if len(self.data) > 1 else '1 song in the queue',
            colour=self.ctx.color,
        )

        queue = [f'`{i + 1}.` {v}' for i, v in enumerate(entries, start=offset)]
        embed.description = '\n'.join(queue)

        return embed
