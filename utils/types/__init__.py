import discord

from typing import TypeAlias

DiscordMedium: TypeAlias = (
    discord.User
    | discord.Member
    | discord.Role
    | discord.TextChannel
    | discord.VoiceChannel
    | discord.CategoryChannel
    | discord.Thread
    | discord.ForumChannel
    | discord.StageChannel
    | discord.abc.GuildChannel
)
