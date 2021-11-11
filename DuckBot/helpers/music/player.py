import discord

from typing import Type, Union
from discord import Client, VoiceChannel
from pomice import Player, Track
from .handler import WaitQueue


def get_thumbnail(track: Track) -> Union[str, discord.embeds._EmptyEmbed]:
    if thumbnail := track.info.get("thumbnail"):
        return thumbnail
    elif any(i in track.uri for i in ("youtu.be", "youtube.com")):
        return f"https://img.youtube.com/vi/{track.identifier}/maxresdefault.jpg"
    else:
        return discord.embeds.EmptyEmbed


class QueuePlayer(Player):
    def __init__(self, client: Type[Client], channel: VoiceChannel):
        super().__init__(client, channel)
        self.queue = WaitQueue()
        self.dj: discord.Member = None
        self.text_channel: int = None
        self.loop: int = 0
        self.waiting: bool = False
        self.message: discord.Message = None

        self.current_vote: bool = False
        self.votes = set()

    def add_vote(self, member: discord.Member):
        self.votes.add(member)

    def clear_votes(self):
        """Clears all votes that have been added"""
        self.current_vote: bool = False
        self.votes.clear()

    async def skip(self):
        """Skips the currently playing track"""
        if self.loop == 1:
            self.loop = 0

        embed = discord.Embed(title='Song skipped')
        embed.description = f"Successfully skipped [{self.current.title}]({self.current.uri})"
        embed.set_thumbnail(url=get_thumbnail(self.current))

        await self.current.ctx.send(embed=embed)
        await self.stop()
