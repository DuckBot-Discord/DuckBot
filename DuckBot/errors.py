# exceptions.py
import datetime

import discord
from discord import Enum
from discord.ext import commands


class NoEmojisFound(commands.CheckFailure):
    pass


class HigherRole(commands.CheckFailure):
    pass


class NoQuotedMessage(commands.CheckFailure):
    pass


class WaitForCancelled(commands.CheckFailure):
    pass


class MuteRoleNotFound(commands.CheckFailure):
    pass


class UserBlacklisted(commands.CheckFailure):
    pass


class NoWelcomeChannel(commands.CheckFailure):
    pass


class BotUnderMaintenance(commands.CheckFailure):
    pass


class NoHideout(commands.CheckFailure):
    pass


class EconomyNotSetup(commands.CheckFailure):
    def __init__(self, prompt: bool = False):
        self.prompt: bool = prompt


class AccountNotFound(commands.CheckFailure):
    def __init__(self, user: discord.User):
        self.user: discord.User = user


class AccountAlreadyExists(commands.CheckFailure):
    def __init__(self, user: discord.User):
        self.user: discord.User = user


class CooldownType(Enum):
    WORK = 0
    DAILY = 1
    WEEKLY = 2
    MONTHLY = 3


class EconomyOnCooldown(commands.CheckFailure):
    def __init__(self, cooldown_type: CooldownType, next_run: datetime.datetime):
        self.cooldown_type = cooldown_type
        self.next_run = next_run


class WalletInUse(commands.CheckFailure):
    def __init__(self, user: discord.User):
        self.user = user


class BaseError(commands.CommandError):
    def __init__(self, e) -> None:
        self.custom = True
        self.message = e
        super().__init__(e)


class NoPlayer(BaseError):
    def __init__(self) -> None:
        super().__init__(f'⚠ **|** There isn\'t an active player in your server.')


class FullVoiceChannel(BaseError):
    def __init__(self, ctx: commands.Context) -> None:
        super().__init__(f'⚠ **|** I can\'t join {ctx.author.voice.channel.mention}, because it\'s full.')


class NotAuthorized(BaseError):
    def __init__(self) -> None:
        super().__init__("⚠ **|** You cannot perform this action.")


class IncorrectChannelError(BaseError):
    def __init__(self, ctx: commands.Context) -> None:
        player = ctx.voice_client
        super().__init__(f'⚠ **|** {ctx.author.mention}, you must be in {player.channel.mention} for this session.')


class IncorrectTextChannelError(BaseError):
    def __init__(self, ctx: commands.Context) -> None:
        player = ctx.voice_client
        super().__init__(f'⚠ **|** {ctx.author.mention}, sorry, but this session is in {player.text_channel.mention}.')


class AlreadyConnectedToChannel(BaseError):
    def __init__(self, ctx: commands.Context) -> None:
        player = ctx.voice_client
        super().__init__(f"⚠ **|** I'm already in {player.channel.mention}")


class NoVoiceChannel(BaseError):
    def __init__(self) -> None:
        super().__init__("⚠ **|** I'm not connected to any voice channels.")


class QueueIsEmpty(BaseError):
    def __init__(self) -> None:
        super().__init__("⚠ **|** There are no tracks in the queue.")


class NoCurrentTrack(BaseError):
    def __init__(self) -> None:
        super().__init__("⚠ **|** There's nothing playing.")


class PlayerIsAlreadyPaused(BaseError):
    def __init__(self) -> None:
        super().__init__("⚠ **|** The current track is already paused.")


class PlayerIsNotPaused(BaseError):
    def __init__(self) -> None:
        super().__init__("⚠ **|** The current track is not paused.")


class NoMoreTracks(BaseError):
    def __init__(self) -> None:
        super().__init__("⚠ **|** There are no more tracks in the queue.")


class InvalidTimeString(BaseError):
    def __init__(self) -> None:
        super().__init__("⚠ **|** An invalid time was provided.")


class NoPerms(BaseError):
    def __init__(self, perms, channel) -> None:
        super().__init__(f"⚠ **|** I don't have permissions to `{perms}` in {channel.mention}")


class NoConnection(BaseError):
    def __init__(self) -> None:
        super().__init__("⚠ **|** You are not in a voice channel.")


class AfkChannel(BaseError):
    def __init__(self) -> None:
        super().__init__("⚠ **|** I can't play music in the afk channel.")


class InvalidTrack(BaseError):
    def __init__(self) -> None:
        super().__init__("⚠ **|** The given track is not in the queue.")


class InvalidPosition(BaseError):
    def __init__(self) -> None:
        super().__init__("⚠ **|** The given position doesn't point to a track in queue.")


class InvalidVolume(BaseError):
    def __init__(self) -> None:
        super().__init__('⚠ **|** The volume must be between **1** and **125**')


class InvalidSeek(BaseError):
    def __init__(self) -> None:
        super().__init__('⚠ **|** You can\'t seek with timestamps that are shorter/longer than the track\'s length')


class AlreadyVoted(BaseError):
    def __init__(self) -> None:
        super().__init__('⚠ **|** You\'ve already voted.')


class NothingToShuffle(BaseError):
    def __init__(self) -> None:
        super().__init__('⚠ **|** There is nothing to shuffle.')


class ActiveVote(BaseError):
    def __init__(self) -> None:
        super().__init__('⚠ **|** There is already an active vote.')


class LoadFailed(BaseError):
    def __init__(self) -> None:
        super().__init__('⚠ **|** Failed loading your query.')


class NoMatches(BaseError):
    def __init__(self) -> None:
        super().__init__('⚠ **|** No songs were found with that query, please try again.')


class InvalidInput(BaseError):
    def __init__(self) -> None:
        super().__init__('⚠ **|** Invalid input has been detected')


class TrackFailed(BaseError):
    def __init__(self, track) -> None:
        super().__init__(f'⚠ **|** There was an error playing {track.title}, skipping to next track.')

