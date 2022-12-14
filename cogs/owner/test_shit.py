from __future__ import annotations
from dataclasses import dataclass, field
from logging import getLogger
from typing_extensions import Self
import re
import textwrap
import tabulate

import discord
import asyncpg
from discord.ext import commands

from utils import DuckCog, command, DuckContext, cb

CATEGORY_ID = 993819813375914025

pattern = re.compile(r"Maya (?P<NUM>\d+): (?P<MSG>.+)")
log = getLogger(__name__)


@dataclass
class DM:
    user_id: int
    enabled: bool
    channel: int | None = None
    wh_url: str | None = None
    messages: list[tuple[discord.Message, discord.Message]] = field(default_factory=list)

    @classmethod
    def from_record(cls, record: asyncpg.Record) -> Self:
        return cls(
            user_id=record['user_id'],
            enabled=record['dms_enabled'],
            channel=record['dm_channel'],
            wh_url=record['dm_webhook'],
        )

    def update(self, record: asyncpg.Record) -> None:
        self.enabled = record['dms_enabled']
        self.channel = record['dm_channel']
        self.wh_url = record['dm_webhook']


class Prompt(discord.ui.View):
    def __init__(self, cog: TestingShit):
        self.cog: TestingShit = cog
        super().__init__(timeout=None)

    @classmethod
    async def prompt(cls, message: discord.Message, cog: TestingShit):
        view = cls(cog)
        embed = discord.Embed(
            title='Welcome to DuckBot\'s DMs!',
            description=(
                'This conversation will be sent to the bot developers.'
                '\nThey will reply to you as soon as possible! 💞'
                '\n'
                '\n**Message edits may not be portrayed correctly!**'
                '\n'
                '\nStickers will not be sent, as bots cannot use them.'
                '\nIf your message does not get the \N{WHITE HEAVY CHECK MARK} reaction, it failed to send!'
                '\n'
                '\nYou can toggle this at any time by checking the pinned messages.'
            ),
            color=view.cog.bot.colour,
        )
        newm = await message.channel.send(embed=embed, view=view)
        await view.cog.bot.pool.execute(
            'INSERT INTO dm_flow (user_id) VALUES ($1) ON CONFLICT DO NOTHING', message.author.id
        )
        await newm.pin()

    @discord.ui.button(custom_id='allow-dms', style=discord.ButtonStyle.gray, label='Contact DuckBot\'s developer team')
    async def allow_dms(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.bot.pool.execute('UPDATE dm_flow SET dms_enabled = TRUE WHERE user_id = $1', interaction.user.id)
        new = Prompt(self.cog)
        new.allow_dms.disabled = True
        if dm := self.cog.dms.get(interaction.user.id):
            dm.enabled = True

        await interaction.response.edit_message(view=new)

    @discord.ui.button(
        custom_id='deny-dms', style=discord.ButtonStyle.red, label='Keep my DMs private! (you can change this later)', row=1
    )
    async def deny_dms(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.bot.pool.execute('UPDATE dm_flow SET dms_enabled = FALSE WHERE user_id = $1', interaction.user.id)
        new = Prompt(self.cog)
        new.deny_dms.disabled = True
        if dm := self.cog.dms.get(interaction.user.id):
            dm.enabled = False
        await interaction.response.edit_message(view=new)


class TestingShit(DuckCog):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.dms: dict[int, DM] = {}

    async def cog_load(self) -> None:
        self.bot.add_view(Prompt(self))

    @property
    def dm_category(self) -> discord.CategoryChannel:
        if not self.bot.is_ready():
            raise RuntimeError('Bot not ready')
        channel = self.bot.get_channel(CATEGORY_ID)
        if not channel:
            raise RuntimeError('Channel not found')
        assert isinstance(channel, discord.CategoryChannel)
        return channel

    async def get_dm_object(self, obj: discord.abc.User | discord.abc.GuildChannel) -> DM | None:
        """gets a DM object from the database or cache"""
        log.info('Got request to get DM object')

        if isinstance(obj, discord.abc.User):
            log.info('With User')
            dm = self.dms.get(obj.id)
            query = "SELECT * FROM dm_flow WHERE user_id = $1"
        else:
            log.info('With channel')

            def pred(dm: DM):
                return dm.channel == obj.id

            dm = discord.utils.find(pred, self.dms.values())
            query = "SELECT * FROM dm_flow WHERE dm_channel = $1"
        if dm:
            log.info('Found cached dm, returning')
            return dm
        record = await self.bot.pool.fetchrow(query, obj.id)
        log.info('fetched from DB %s', record)
        if record:
            log.info('Created new DM object')
            dm = DM.from_record(record)
            self.dms[obj.id] = dm
            return dm
        log.info('Not Found')
        log.info('all records %s', await self.bot.pool.fetch('SELECT * FROM dm_flow'))

    @commands.Cog.listener('on_message')
    async def events_handler(self, message: discord.Message):
        """Takes a message, runs checks and passes information on to the main functions"""
        if message.author.bot:
            return

        if message.channel.type is discord.ChannelType.private:
            dm = await self.get_dm_object(message.author)
            if dm and dm.enabled:
                await self.process_dm(message, dm)
            elif dm is None:
                await Prompt.prompt(message, self)

        elif isinstance(message.channel, discord.TextChannel) and message.channel.category_id == CATEGORY_ID:
            dm = await self.get_dm_object(message.channel)
            if dm:
                return await self.process_message(message, dm)
            await message.delete()

    async def process_dm(self, message: discord.Message, dm: DM) -> None:
        """Takes a message and sends it to the DM channel"""
        channel = self.dm_category.guild.get_channel(dm.channel or 0)
        if not channel:
            channel = await self.dm_category.create_text_channel(name=str(message.author), topic=str(message.author.id))
            webhook = await channel.create_webhook(
                name=message.author.name, avatar=await message.author.display_avatar.read()
            )
            row = await self.bot.pool.fetchrow(
                'UPDATE dm_flow SET dm_channel = $1, dm_webhook = $2 WHERE user_id = $3 RETURNING *',
                channel.id,
                webhook.url,
                message.author.id,
            )
            if not row:
                return
            dm.update(row)
        assert dm.wh_url
        webhook = discord.Webhook.from_url(dm.wh_url, session=self.bot.session)

        content = message.content

        reference = message.reference
        if reference and reference.message_id:
            msgs = discord.utils.find(lambda x: x[0].id == reference.message_id, dm.messages)
            if msgs:
                content += f"\n\n*replying to [this message](<{msgs[1].jump_url}>)*"

        files = [await a.to_file() for a in message.attachments if a.size >= self.dm_category.guild.filesize_limit]

        if len(files) > len(message.attachments):
            content += '\n\n*some files could not be sent due to filesize limit*'

        try:
            try:
                wh_msg = await webhook.send(content=content, files=files, wait=True)
                dm.messages.append((message, wh_msg))
                await message.add_reaction('\N{WHITE HEAVY CHECK MARK}')
            except discord.HTTPException:
                await message.add_reaction('\N{WARNING SIGN}')
        except discord.HTTPException:
            pass

    async def process_message(self, message: discord.Message, dm: DM) -> None:
        user = self.bot.get_user(dm.user_id)
        if not user:
            await message.channel.send(embed=discord.Embed(title='No mutual guilds.'), delete_after=5)
            return await message.delete()

        content = message.content

        reference = message.reference
        reply: discord.Message = None  # type: ignore
        if reference and reference.message_id:
            msgs = discord.utils.find(lambda x: x[1].id == reference.message_id, dm.messages)
            if msgs:
                reply = msgs[0]

        files = [await a.to_file() for a in message.attachments if a.size >= self.dm_category.guild.filesize_limit]

        if len(files) > len(message.attachments):
            content += '\n\n*some files could not be sent due to filesize limit*'

        try:
            try:
                msg = await user.send(content=content, files=files, reference=reply)
            except discord.HTTPException:
                await message.delete()
                await message.channel.send(embed=discord.Embed(title='User has DMs closed.'), delete_after=5)
            else:
                dm.messages.append((msg, message))
        except discord.HTTPException:
            pass

    async def find_msgs(
        self, data: discord.RawMessageDeleteEvent | discord.RawMessageUpdateEvent
    ) -> tuple[discord.Message, discord.Message, DM, int] | None:
        cht = 0  # 0 = DM ; 1 = GUILD
        if data.guild_id:
            cht = 1
            channel = self.dm_category.guild.get_channel(data.channel_id)
            if not channel or channel.category != self.dm_category:
                return
            dm = await self.get_dm_object(channel)
        else:
            if data.cached_message:
                dm = await self.get_dm_object(data.cached_message.author)
            else:
                try:
                    channel = await self.bot.fetch_channel(data.channel_id)
                except discord.HTTPException:
                    return
                if isinstance(channel, discord.DMChannel):
                    if channel.recipient:
                        dm = await self.get_dm_object(channel.recipient)
                    else:
                        dm = None
                else:
                    dm = await self.get_dm_object(channel)  # type: ignore  # how?
                    cht = 1

        if not dm:
            return
        msgs = discord.utils.find(lambda m: m[cht].id == data.message_id, dm.messages)
        if msgs:
            return *msgs, dm, cht

    @commands.Cog.listener('on_raw_message_delete')
    async def delete_listener(self, data: discord.RawMessageDeleteEvent):
        stuff = await self.find_msgs(data)
        if not stuff:
            return
        dm_message, staff_message, dm, cht = stuff
        dm.messages.remove((dm_message, staff_message))
        if cht:
            await dm_message.delete()
        else:
            await staff_message.edit(
                content=None,
                embed=discord.Embed(description=staff_message.content, color=discord.Color.red()).set_footer(
                    text='deleted message'
                ),
            )

    @commands.Cog.listener('on_raw_message_edit')
    async def update_listener(self, data: discord.RawMessageUpdateEvent):
        if data.data.get('author', {}).get('bot'):
            return
        stuff = await self.find_msgs(data)
        if not stuff:
            return
        dm_message, staff_message, _, cht = stuff
        if cht:  # if message belongs to a guild
            new_message = discord.Message(state=self.bot._connection, channel=staff_message.channel, data=data.data)
            await dm_message.edit(content=new_message.content)
        else:
            new_message = discord.Message(state=self.bot._connection, channel=dm_message.channel, data=data.data)
            await staff_message.edit(content=new_message.content)

    @command()
    async def mayas(self, ctx: DuckContext):
        '''Gets all Mayas

        Parameters
        ----------
        ctx : DuckContext
            The context for this command
        '''
        guild = self.bot.get_guild(336642139381301249)
        if not guild:
            raise commands.CommandError('d.py guild not found.')

        mayas = {int(match.group(1)): m for m in guild.members if m.nick and (match := pattern.fullmatch(m.nick))}

        fmt = []
        msgsize = max(map(lambda m: len(m.nick or ''), mayas.values())) - 10
        nsize = max(map(lambda m: len(str(m)), mayas.values())) - 5

        for i in range(min(mayas.keys()), max(mayas.keys()) + 1):
            maya = mayas.get(i)
            if maya:
                fmt.append((maya.nick, str(maya)))
            else:
                fmt.append((f"Maya {i}: {'-'*msgsize}", "-" * nsize))

        await ctx.send(textwrap.indent(cb(tabulate.tabulate(fmt, tablefmt='plain'), lang=''), '> '))
