import contextlib
import random

import discord
from discord.ext import commands

from ._base import FunBase
from ...__main__ import DuckBot
from ...helpers import constants
from ...helpers.context import CustomContext

event_types = {
    # Credits to RemyK888
    'youtube': '880218394199220334',
    'poker': '755827207812677713',
    'betrayal': '773336526917861400',
    'fishing': '814288819477020702',
    'chess': '832012774040141894',

    # Credits to awesomehet2124
    'letter-tile': '879863686565621790',
    'word-snack': '879863976006127627',
    'doodle-crew': '878067389634314250',

    'spellcast': '852509694341283871',
    'awkword': '879863881349087252',
    'checkers': '832013003968348200',
}


async def create_link(bot: DuckBot, vc: discord.VoiceChannel, option: str) -> str:
    """
    Generates an invite link to a VC with the Discord Party VC Feature.
    Parameters
    ----------
    bot: :class: commands.Bot
        the bot instance. It must have a :attr:`session` attribute (a :class:`aiohttp.ClientSession`)
    vc: :class: discord.VoiceChannel
        the voice channel to create the invite link for
    option: str
        the event type to create the invite link for
    Returns
    ----------
    :class:`str`
        Contains the discord invite link which, upon clicked, starts the custom activity in the VC.
    """

    if not vc.permissions_for(vc.guild.me).create_instant_invite:
        raise commands.BotMissingPermissions(['CREATE_INSTANT_INVITE'])

    data = {
        'max_age': 0,
        'max_uses': 0,
        'target_application_id': event_types.get(option),
        'target_type': 2,
        'temporary': False,
        'validate': None
    }

    async with bot.session.post(f"https://discord.com/api/v8/channels/{vc.id}/invites",
                                  json=data, headers={'Authorization': f'Bot {bot.http.token}',
                                                      'Content-Type': 'application/json'}) as resp:
        resp_code = resp.status
        result = await resp.json()

    if resp_code == 429:
        raise commands.BadArgument('Woah there! Slow down. You are being rate-limited.'
                                   f'\nTry again in {result.get("X-RateLimit-Reset-After")}s')
    elif resp_code == 401:
        raise commands.BadArgument('Unauthorized')
    elif result['code'] == 10003 or (result['code'] == 50035 and 'channel_id' in result['errors']):
        raise commands.BadArgument('For some reason, that voice channel is not valid...')
    elif result['code'] == 50013:
        raise commands.BotMissingPermissions(['CREATE_INSTANT_INVITE'])
    elif result['code'] == 130000:
        raise commands.BadArgument('The api is currently overloaded... Try later maybe?')

    return f"https://discord.gg/{result['code']}"


class YoutubeDropdown(discord.ui.View):
    def __init__(self, ctx: CustomContext):
        super().__init__()
        self.ctx = ctx
        self.message: discord.Message = None  # type: ignore

    @discord.ui.select(placeholder='Select an activity type...', options=[
        discord.SelectOption(label='Cancel', value='cancel', emoji='❌'),
        discord.SelectOption(label='Youtube', value='youtube', emoji=constants.YOUTUBE_LOGO),
        discord.SelectOption(label='Poker', value='poker', emoji='<:poker_cards:917645571274195004>'),
        discord.SelectOption(label='Betrayal', value='betrayal', emoji='<:betrayal:917647390717141072>'),
        discord.SelectOption(label='Fishing', value='fishing', emoji='🎣'),
        discord.SelectOption(label='Chess', value='chess', emoji='\U0000265f\U0000fe0f'),
        discord.SelectOption(label='Letter Tile', value='letter-tile', emoji='<:letterTile:917647925927084032>'),
        discord.SelectOption(label='Word Snacks', value='word-snack', emoji='<:wordSnacks:917648019342655488>'),
        discord.SelectOption(label='Doodle Crew', value='doodle-crew', emoji='<:doodle:917648115656437810>'),
        discord.SelectOption(label='Spellcast', value='spellcast', emoji='📜'),
        discord.SelectOption(label='Awkword', value='awkword', emoji=constants.TYPING_INDICATOR),
        discord.SelectOption(label='Checkers', value='checkers', emoji='🏁'),
        discord.SelectOption(label='Cancel', value='cancel2', emoji='❌'),
    ])
    async def activity_select(self, select: discord.ui.Select, interaction: discord.Interaction):
        member = interaction.user
        if not member.voice:
            await interaction.response.edit_message(content='You are not connected to a voice channel', view=None)
            return self.stop()
        if 'cancel' in select.values[0]:
            self.stop()
            with contextlib.suppress(discord.HTTPException):
                await interaction.message.delete()
                await self.ctx.message.add_reaction(random.choice(constants.DONE))
            return
        try:
            link = await create_link(self.ctx.bot, member.voice.channel, select.values[0])
        except Exception as e:
            self.stop()
            self.ctx.bot.dispatch('command_error', self.ctx, e)
            with contextlib.suppress(discord.HTTPException):
                await self.message.delete()
            return
        await interaction.response.edit_message(content=f'**To start the activity, press the blue link:**'
                                                        f'\n> <{link}>'
                                                        f'\n_note: activities don\'t work on mobile yet..._', view=None)
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.ctx.author

    async def start(self):
        await self.ctx.send(':rocket: Select the activity you want to start!', view=self)

    async def on_timeout(self) -> None:
        with contextlib.suppress(discord.HTTPException):
            await self.message.delete()
            await self.ctx.message.add_reaction(random.choice(constants.DONE))


class DiscordActivities(FunBase):

    @commands.cooldown(1, 5, commands.BucketType.guild)
    @commands.command()
    async def activity(self, ctx: CustomContext):
        """ Method to start one of the new discord activities """
        if not ctx.author.voice:
            ctx.command.reset_cooldown(ctx)
            await ctx.send('You are not connected to a voice channel')
            return
        view = YoutubeDropdown(ctx)
        await view.start()
