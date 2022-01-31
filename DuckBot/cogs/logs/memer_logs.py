import asyncio

import discord
from discord.ext import commands

from ._base import LoggingBase


class MemberLogs(LoggingBase):

    @commands.Cog.listener('on_member_update')
    async def logger_on_member_update(self, before: discord.Member, after: discord.Member):
        if before.guild.id not in self.bot.log_channels or not self.bot.guild_loggings[after.guild.id].member_update:
            return
        await asyncio.sleep(1)
        embed = discord.Embed(title='Member Updated', colour=discord.Colour.blurple(), timestamp=discord.utils.utcnow())
        embed.set_author(name=str(after), icon_url=after.display_avatar.url)
        embed.set_footer(text=f'User ID: {after.id}')
        deliver = False
        if before.avatar != after.avatar:
            if after.avatar is not None:
                embed.add_field(name='Server Avatar updated:', inline=False,
                                value=f'Member {"updated" if before.avatar else "set"} their avatar.')
                embed.set_thumbnail(url=after.guild_avatar.url)
            else:
                embed.add_field(name='Server Avatar updated:', inline=False,
                                value='Member removed their avatar.')
                embed.set_thumbnail(url=after.default_avatar.url)
            deliver = True
        if before.roles != after.roles:
            added = set(after.roles) - set(before.roles)
            removed = set(before.roles) - set(after.roles)
            add = False
            if added:
                added = f"**Added:**" + ', '.join([r.mention for r in added])
                add = True
            else:
                added = ''
            if removed:
                removed = f"**Removed:**" + ', '.join([r.mention for r in removed])
                add = True
            else:
                removed = ''
            if add:
                embed.add_field(name='Roles updated:', inline=False,
                                value=f"{added}\n{removed}")
            deliver = True
        if before.nick != after.nick:
            embed.add_field(name='Nickname updated:', inline=False,
                            value=f"**Before:** {discord.utils.escape_markdown(str(before.nick))}"
                                  f"\n**After:** {discord.utils.escape_markdown(str(after.nick))}")
            deliver = True
        if deliver:
            self.log(embed, guild=after.guild, send_to=self.send_to.member)

    @commands.Cog.listener('on_user_update')
    async def logger_on_user_update(self, before: discord.User, after: discord.User):
        if after.id == self.bot.user.id:
            return
        guilds = [g.id for g in before.mutual_guilds if g.id in self.bot.log_channels]
        if not guilds:
            return
        deliver = False
        embed = discord.Embed(title='User Updated', colour=discord.Colour.blurple(), timestamp=discord.utils.utcnow())
        embed.set_author(name=str(after), icon_url=after.display_avatar.url)
        embed.set_footer(text=f'User ID: {after.id}')
        if before.avatar != after.avatar:
            if after.avatar is not None:
                embed.add_field(name='Avatar updated:', inline=False,
                                value=f'Member {"updated" if before.avatar else "set"} their avatar.')
                embed.set_thumbnail(url=after.display_avatar.url)
            else:
                embed.add_field(name='Avatar updated:', inline=False,
                                value='Member removed their avatar.')
                embed.set_thumbnail(url=after.default_avatar.url)
            deliver = True

        if before.name != after.name:
            embed.add_field(name='Changed Names:', inline=False,
                            value=f'**Before:** {discord.utils.escape_markdown(before.name)}\n'
                                  f'**After:** {discord.utils.escape_markdown(after.name)}')
            deliver = True
        if before.discriminator != after.discriminator:
            embed.add_field(name='Changed Discriminator:', inline=False,
                            value=f'**Before:** {before.discriminator}\n**After:** {after.discriminator}')
            deliver = True
        if deliver:
            for g in guilds:
                if self.bot.guild_loggings[g].member_update:
                    self.log(embed, guild=g, send_to=self.send_to.member)

    @commands.Cog.listener('on_member_ban')
    async def logger_on_member_ban(self, guild: discord.Guild, user: discord.User):
        if guild.id not in self.bot.log_channels or not self.bot.guild_loggings[guild.id].user_ban:
            return
        embed = discord.Embed(title='User Banned', colour=discord.Colour.red(), timestamp=discord.utils.utcnow(),
                              description=f"**Account Created:** {discord.utils.format_dt(user.created_at)} ({discord.utils.format_dt(user.created_at, style='R')})")
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id}")
        self.log(embed, guild=guild, send_to=self.send_to.member)

    @commands.Cog.listener('on_member_unban')
    async def logger_on_member_unban(self, guild: discord.Guild, user: discord.User):
        if guild.id not in self.bot.log_channels or not self.bot.guild_loggings[guild.id].user_unban:
            return
        embed = discord.Embed(title='User Unbanned', colour=discord.Colour.blurple(), timestamp=discord.utils.utcnow(),
                              description=f"**Account Created:** {discord.utils.format_dt(user.created_at)} ({discord.utils.format_dt(user.created_at, style='R')})")
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id}")
        self.log(embed, guild=guild, send_to=self.send_to.member)
