import discord
from discord.ext import commands

from ._base import LoggingBase
from DuckBot.helpers import constants


class VoiceLogs(LoggingBase):

    @commands.Cog.listener('on_voice_state_update')
    async def logger_on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.guild.id not in self.bot.log_channels:
            return
        if before.channel and after.channel and before.channel != after.channel and self.bot.guild_loggings[member.guild.id].voice_move:
            embed = discord.Embed(title='Member moved voice channels:', colour=discord.Colour.blurple(), timestamp=discord.utils.utcnow(),
                                  description=f"**From:** {before.channel.mention} ({after.channel.id})"
                                              f"\n**To:** {after.channel.mention} ({after.channel.id})")
            embed.set_author(name=str(member), icon_url=member.display_avatar.url)
            embed.set_footer(text=f"Member ID: {member.id}")
            self.log(embed, guild=member.guild, send_to=self.send_to.voice)
        if not before.channel and after.channel and self.bot.guild_loggings[member.guild.id].voice_join:
            embed = discord.Embed(title='Member joined a voice channel:', colour=discord.Colour.green(), timestamp=discord.utils.utcnow(),
                                  description=f"**Joined:** {after.channel.mention} ({after.channel.id})")
            embed.set_author(name=str(member), icon_url=member.display_avatar.url)
            embed.set_footer(text=f"Member ID: {member.id}")
            self.log(embed, guild=member.guild, send_to=self.send_to.voice)
        if before.channel and not after.channel and self.bot.guild_loggings[member.guild.id].voice_leave:
            embed = discord.Embed(title='Member left a voice channel:', colour=discord.Colour.red(), timestamp=discord.utils.utcnow(),
                                  description=f"**Left:** {before.channel.mention} ({before.channel.id})")
            embed.set_author(name=str(member), icon_url=member.display_avatar.url)
            embed.set_footer(text=f"Member ID: {member.id}")
            self.log(embed, guild=member.guild, send_to=self.send_to.voice)
        if not self.bot.guild_loggings[member.guild.id].voice_mod:
            return
        if before.deaf != after.deaf:
            if after.deaf:
                embed = discord.Embed(title='Member Deafened by a Moderator', colour=discord.Colour.dark_gold(), timestamp=discord.utils.utcnow())
                embed.set_author(name=str(member), icon_url=member.display_avatar.url)
                embed.set_footer(text=f"Member ID: {member.id}")
                self.log(embed, guild=member.guild, send_to=self.send_to.voice)
            if before.deaf:
                embed = discord.Embed(title='Member Un-deafened by a Moderator', colour=discord.Colour.yellow(), timestamp=discord.utils.utcnow())
                embed.set_author(name=str(member), icon_url=member.display_avatar.url)
                embed.set_footer(text=f"Member ID: {member.id}")
                self.log(embed, guild=member.guild, send_to=self.send_to.voice)
        if before.mute != after.mute:
            if after.mute:
                embed = discord.Embed(title='Member Muted by a Moderator', colour=discord.Colour.dark_gold(), timestamp=discord.utils.utcnow())
                embed.set_author(name=str(member), icon_url=member.display_avatar.url)
                embed.set_footer(text=f"Member ID: {member.id}")
                self.log(embed, guild=member.guild, send_to=self.send_to.voice)
            if before.mute:
                embed = discord.Embed(title='Member Un-muted by a Moderator', colour=discord.Colour.yellow(), timestamp=discord.utils.utcnow())
                embed.set_author(name=str(member), icon_url=member.display_avatar.url)
                embed.set_footer(text=f"Member ID: {member.id}")
                self.log(embed, guild=member.guild, send_to=self.send_to.voice)

    @commands.Cog.listener('on_stage_instance_create')
    async def logger_on_stage_instance_create(self, stage_instance: discord.StageInstance):
        if stage_instance.guild.id not in self.bot.log_channels or not self.bot.guild_loggings[stage_instance.guild.id].stage_open:
            return
        embed = discord.Embed(title='Stage opened', colour=discord.Colour.teal(), timestamp=discord.utils.utcnow(),
                              description=f"**Channel** <#{stage_instance.channel_id}> ({stage_instance.channel_id})\n"
                                          f"**Topic:** {stage_instance.topic}\n"
                                          f"**Public** {constants.DEFAULT_TICKS[stage_instance.is_public()]}\n"
                                          f"**Discoverable:** {constants.DEFAULT_TICKS[stage_instance.discoverable_disabled]}\n")
        embed.set_footer(text=f"Channel ID: {stage_instance.channel_id}")
        self.log(embed, guild=stage_instance.guild, send_to=self.send_to.voice)

    @commands.Cog.listener('on_stage_instance_delete')
    async def logger_on_stage_instance_delete(self, stage_instance: discord.StageInstance):
        if stage_instance.guild.id not in self.bot.log_channels or not self.bot.guild_loggings[stage_instance.guild.id].stage_close:
            return
        embed = discord.Embed(title='Stage closed', colour=discord.Colour.dark_teal(), timestamp=discord.utils.utcnow(),
                              description=f"**Channel** <#{stage_instance.channel_id}> ({stage_instance.channel_id})\n"
                                          f"**Topic:** {stage_instance.topic}\n")
        embed.set_footer(text=f"Channel ID: {stage_instance.channel_id}")
        self.log(embed, guild=stage_instance.guild, send_to=self.send_to.voice)

    @commands.Cog.listener('on_stage_instance_update')
    async def logger_on_stage_instance_update(self, before: discord.StageInstance, after: discord.StageInstance):
        pass
