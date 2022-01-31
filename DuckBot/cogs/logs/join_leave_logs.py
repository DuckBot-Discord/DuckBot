import discord
import typing
from discord.ext import commands

from DuckBot.helpers import constants
from ._base import LoggingBase


class JoinLeaveLogs(LoggingBase):

    @commands.Cog.listener('on_invite_update')
    async def logger_on_member_join(self, member: discord.Member, invite: typing.Optional[discord.Invite]):
        if member.guild.id not in self.bot.log_channels or not self.bot.guild_loggings[member.guild.id].member_join:
            return
        embed = discord.Embed(title='Member joined', colour=discord.Colour.green(), timestamp=discord.utils.utcnow(),
                              description=f'{member.mention} | {member.guild.member_count} to join.'
                                          f'\n**Created:** {discord.utils.format_dt(member.created_at)} ({discord.utils.format_dt(member.created_at, style="R")})')
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        if invite:
            embed.add_field(name='Invited by: ',
                            value=f"{discord.utils.escape_markdown(str(invite.inviter))} ({invite.inviter.mention})"
                                  f"\n**Using invite code:** [{invite.code}]({invite.url})"
                                  f"\n**Expires:** {discord.utils.format_dt(invite.expires_at) if invite.expires_at else 'Never'}"
                                  f"\n**Uses:** {invite.uses}/{invite.max_uses if invite.max_uses > 0 else 'unlimited'}", inline=False)
        self.log(embed, guild=member.guild, send_to=self.send_to.join_leave)

    @commands.Cog.listener('on_member_remove')
    async def logger_on_member_remove(self, member: discord.Member):
        if member.guild.id not in self.bot.log_channels or not self.bot.guild_loggings[member.guild.id].member_leave:
            return
        embed = discord.Embed(color=discord.Colour(0xF4D58C), title='Member left',
                              description=f"**Created at:** {discord.utils.format_dt(member.created_at)} ({discord.utils.format_dt(member.created_at, 'R')})"
                                          f"\n**Joined at:** {discord.utils.format_dt(member.joined_at) if member.joined_at else 'N/A'} "
                                          f"({discord.utils.format_dt(member.joined_at, 'R') if member.joined_at else 'N/A'})"
                                          f"\n**Nickname:** {member.nick}")
        embed.set_author(name=str(member), icon_url=(member.avatar or member.default_avatar).url)
        roles = [r for r in member.roles if not r.is_default()]
        if roles:
            embed.add_field(name='Roles', value=', '.join([r.mention for r in roles]), inline=True)
        self.log(embed, guild=member.guild, send_to=self.send_to.join_leave)

    @commands.Cog.listener('on_invite_create')
    async def logger_on_invite_create(self, invite: discord.Invite):
        if invite.guild.id not in self.bot.log_channels or not self.bot.guild_loggings[invite.guild.id].invite_create:
            return
        embed = discord.Embed(title='Invite Created', colour=discord.Colour.fuchsia(), timestamp=discord.utils.utcnow(),
                              description=f"**Inviter:** {invite.inviter}{f' ({invite.inviter.id})' if invite.inviter else ''}\n"
                                          f"**Invite Code:** [{invite.code}]({invite.url})\n"
                                          f"**Expires:** {discord.utils.format_dt(invite.expires_at, style='R') if invite.expires_at else 'Never'}\n"
                                          f"**Max Uses:** {invite.max_uses if invite.max_uses > 0 else 'Unlimited'}\n"
                                          f"**Channel:** {invite.channel}\n"
                                          f"**Grants Temporary Membership:** {constants.DEFAULT_TICKS[invite.temporary]}")
        if invite.inviter:
            embed.set_author(icon_url=invite.inviter.display_avatar.url, name=str(invite.inviter))
        embed.set_footer(text=f"Invite ID: {invite.id}")
        self.log(embed, guild=invite.guild, send_to=self.send_to.join_leave)

    @commands.Cog.listener('on_invite_delete')
    async def logger_on_invite_delete(self, invite: discord.Invite):
        if invite.guild.id not in self.bot.log_channels or not self.bot.guild_loggings[invite.guild.id].invite_delete:
            return
        embed = discord.Embed(title='Invite Deleted', colour=discord.Colour.fuchsia(), timestamp=discord.utils.utcnow(),
                              description=f"**Inviter:** {invite.inviter}{f' ({invite.inviter.id})' if invite.inviter else ''}\n"
                                          f"**Invite Code:** [{invite.code}]({invite.url})\n"
                                          f"**Channel:** {invite.channel}\n"
                                          f"**Grants Temporary Membership:** {constants.DEFAULT_TICKS[invite.temporary]}")
        if invite.inviter:
            embed.set_author(icon_url=invite.inviter.display_avatar.url, name=str(invite.inviter))
        embed.set_footer(text=f"Invite ID: {invite.id}")
        self.log(embed, guild=invite.guild, send_to=self.send_to.join_leave)
