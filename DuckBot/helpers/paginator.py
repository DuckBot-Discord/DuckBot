from __future__ import annotations
import re
import asyncio
from typing import Any, Dict, Optional
import discord
import typing
from discord.ext import commands
from discord.ext.commands import Paginator as CommandPaginator
from discord.ext import menus

from DuckBot.helpers import helper
from DuckBot.__main__ import CustomContext


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
        await interaction.response.send_message(f'This menu belongs to **{self.ctx.author}**, sorry! 💖',
                                                ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        if self.message:
            await self.message.edit(view=None)

    async def on_error(self, error: Exception, item: discord.ui.Item, interaction: discord.Interaction) -> None:
        if interaction.response.is_done():
            await interaction.followup.send('An unknown error occurred, sorry', ephemeral=True)
        else:
            await interaction.response.send_message('An unknown error occurred, sorry', ephemeral=True)

    async def start(self) -> None:
        if self.check_embeds and not self.ctx.channel.permissions_for(self.ctx.me).embed_links:
            await self.ctx.send('Bot does not have embed links permission in this channel.')
            return

        await self.source._prepare_once()
        page = await self.source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        self._update_labels(0)
        self.message = await self.ctx.send(**kwargs, view=self)

    @discord.ui.button(label='≪', style=discord.ButtonStyle.grey)
    async def go_to_first_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        """go to the first page"""
        await self.show_page(interaction, 0)

    @discord.ui.button(label='Back', style=discord.ButtonStyle.blurple)
    async def go_to_previous_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        """go to the previous page"""
        await self.show_checked_page(interaction, self.current_page - 1)

    @discord.ui.button(label='Current', style=discord.ButtonStyle.grey, disabled=True)
    async def go_to_current_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        pass

    @discord.ui.button(label='Next', style=discord.ButtonStyle.blurple)
    async def go_to_next_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        """go to the next page"""
        await self.show_checked_page(interaction, self.current_page + 1)

    @discord.ui.button(label='≫', style=discord.ButtonStyle.grey)
    async def go_to_last_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        """go to the last page"""
        # The call here is safe because it's guarded by skip_if
        await self.show_page(interaction, self.source.get_max_pages() - 1)

    @discord.ui.button(label='Skip to page...', style=discord.ButtonStyle.grey)
    async def numbered_page(self, button: discord.ui.Button, interaction: discord.Interaction):
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

    @discord.ui.button(label='Quit', style=discord.ButtonStyle.red)
    async def stop_pages(self, button: discord.ui.Button, interaction: discord.Interaction):
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
        self.embed.description = discord.Embed.Empty

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
    async def format_page(self, menu, entries):
        pages = []
        for index, entry in enumerate(entries, start=menu.current_page * self.per_page):
            pages.append(f'{index + 1}. {entry}')

        maximum = self.get_max_pages()
        if maximum > 1:
            footer = f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} entries)'
            menu.embed.set_footer(text=footer)

        menu.embed.description = '\n'.join(pages)
        return menu.embed


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
        all_features = {
            'COMMUNITY': 'Community Server',
            'VERIFIED': 'Verified',
            'DISCOVERABLE': 'Discoverable',
            'PARTNERED': 'Partnered',
            'FEATURABLE': 'Featured',
            'COMMERCE': 'Commerce',
            'MONETIZATION_ENABLED': 'Monetization',
            'NEWS': 'News Channels',
            'PREVIEW_ENABLED': 'Preview Enabled',
            'INVITE_SPLASH': 'Invite Splash',
            'VANITY_URL': 'Vanity Invite URL',
            'ANIMATED_ICON': 'Animated Server Icon',
            'BANNER': 'Server Banner',
            'MORE_EMOJI': 'More Emoji',
            'MORE_STICKERS': 'More Stickers',
            'WELCOME_SCREEN_ENABLED': 'Welcome Screen',
            'MEMBER_VERIFICATION_GATE_ENABLED': 'Membership Screening',
            'TICKETED_EVENTS_ENABLED': 'Ticketed Events',
            'VIP_REGIONS': 'VIP Voice Regions',
            'PRIVATE_THREADS': 'Private Threads',
            'THREE_DAY_THREAD_ARCHIVE': '3 Day Thread Archive',
            'SEVEN_DAY_THREAD_ARCHIVE': '1 Week Thread Archive',
        }
        boosting_level_emojis = {
            '0': '<:Level0_guild:883081706918252604>',
            '1': '<:Level1_guild:883072977430794240>',
            '2': '<:Level2_guild:883073003984916491>',
            '3': '<:Level3_guild:883073034817245234>'
        }

        for feature, label in all_features.items():
            if feature in features:
                enabled_features.append(f'{self.context.tick(True)} {label}')

        embed = discord.Embed(title=guild.name)

        embed.add_field(name="<:rich_presence:658538493521166336> Features:",
                        value=('\n'.join(enabled_features) if enabled_features else 'No features...'), inline=True)

        embed.add_field(name="<:info:860295406349058068> General Info:",
                        value=f"🆔 {guild.id}"
                              f"\n<:owner_crown:845946530452209734> {guild.owner}"
                              f"\n👤 {len([m for m in guild.members if not m.bot])} "
                              f"(🤖 {len([m for m in guild.members if m.bot])})"
                              f"\n╰ ➕ {guild.member_count}/{guild.max_members}"
                              f"\n🌐 Server Region: {helper.get_server_region(guild)}"
                              f"\n<:role:860644904048132137> Roles: {len(guild.roles)}")

        if guild.description:
            desc = guild.description
        else:
            desc = "<:toggle_off:857842924544065536> Feature toggled off." \
                   "\nEnable it in `community -> overview` in server settings!"

        embed.add_field(name="<:info:860295406349058068> Server description:",
                        value=desc, inline=False)

        embed.add_field(name="<:rich_presence:658538493521166336> Channels:",
                        value=f"<:voice:860330111377866774> "
                              f"{len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])}"
                              f"\n<:view_channel:854786097023549491> Channels: "
                              f"{len([c for c in guild.channels if isinstance(c, discord.TextChannel)])}"
                              f"\n<:category:882685952999428107> Categories: "
                              f"{len([c for c in guild.channels if isinstance(c, discord.CategoryChannel)])}"
                              f"\n<:stagechannel:824240882793447444> Stages: "
                              f"{len([c for c in guild.channels if isinstance(c, discord.StageChannel)])}"
                              f"\n<:threadnew:833432474347372564> Threads: {len(guild.threads)}"
                              f"\n╰ (visible by me)",
                        inline=True)

        embed.add_field(name="<:emoji_ghost:658538492321595393> Emojis:",
                        value=f"Static: {len([e for e in guild.emojis if not e.animated])}/{guild.emoji_limit} "
                              f"\nAnimated: {len([e for e in guild.emojis if e.animated])}/{guild.emoji_limit} ",
                        inline=True)

        last_boost = max(guild.members, key=lambda m: m.premium_since or guild.created_at)
        if last_boost.premium_since is not None:
            boost = f"\n{last_boost}" \
                    f"\n╰ {discord.utils.format_dt(last_boost.premium_since, style='R')}"
        else:
            boost = "\n╰ No active boosters"

        embed.add_field(name="<:booster4:860644548887969832> Boosts:",
                        value=f"{boosting_level_emojis[str(guild.premium_tier)]} Level: {guild.premium_tier}"
                              f"\n╰ Amount: {guild.premium_subscription_count}"
                              f"\n**<:booster4:860644548887969832> Last booster:**{boost}")

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
        embed = discord.Embed(title=f"{self.guild}'s emotes ({len(self.guild.emojis)})",
                              description="\n".join(f'{i}. {v}' for i, v in enumerate(entries, start=offset)))
        return embed


class CharacterInformationPageSource(menus.ListPageSource):

    async def format_page(self, menu, item):
        embed = discord.Embed(description="\n".join(item), title="ℹ Character information")
        return embed


def emoji_str(emoji: typing.Union[discord.Emoji, discord.PartialEmoji]) -> str:
    return str(emoji).replace('<', '<\u200b').replace('>', '\u200b>')


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

            embed = discord.Embed(color=0xF4D58C, timestamp=self.time,
                                  description=
                                  f"**Format:** [{emoji_str(emoji)}]({emoji.url})"
                                  f"\n**Created at:** {discord.utils.format_dt(emoji.created_at)}"
                                  f"\n**Name:** {emoji.name}"
                                  f"\n**Id:** {emoji.id}"
                                  f"\n**Server:** {emoji.guild}"
                                  f"{creator}"
                                  f"{roles_formatted}")
            embed.set_footer(text=f'Requested by {self.ctx.author}', icon_url=self.ctx.author.display_avatar.url)
            embed.set_image(url=emoji.url)
            return embed

        elif isinstance(emoji, discord.PartialEmoji):
            embed = discord.Embed(color=0xF4D58C, timestamp=self.time,
                                  description=
                                  f"**Format:** [{emoji_str(emoji)}]({emoji.url})"
                                  f"**Created at:** {discord.utils.format_dt(emoji.created_at)}")
            embed.set_footer(text=f'Requested by {self.ctx.author}', icon_url=self.ctx.author.display_avatar.url)
            embed.set_image(url=emoji.url)
            return embed
        else:
            return discord.Embed(description='something went wrong...')
