import discord

import typing
from discord.ext import commands

from DuckBot.helpers import constants
from ._base import LoggingBase, guild_channels



class ServerLogs(LoggingBase):

    @commands.Cog.listener('on_guild_channel_delete')
    async def logger_on_guild_channel_delete(self, channel: guild_channels):
        if not channel.guild or channel.guild.id not in self.bot.log_channels or not self.bot.guild_loggings[channel.guild.id].channel_delete:
            return

        embed = discord.Embed(title=f'{channel.type} channel deleted.'.title(),
                              description=f"**Name:** #{channel.name}"
                                          f"\n**Category:** {channel.category}"
                                          f"\n**Topic:** {discord.utils.remove_markdown(channel.topic) if hasattr(channel, 'topic') and channel.topic else 'None'}"
                                          f"\n**Created at:** {discord.utils.format_dt(channel.created_at)}",
                              colour=discord.Colour.red(), timestamp=discord.utils.utcnow())
        embed.set_footer(text=f'Channel ID: {channel.id}')
        self.log(embed, guild=channel.guild, send_to=self.send_to.server)

    @commands.Cog.listener('on_guild_channel_create')
    async def logger_on_guild_channel_create(self, channel: guild_channels):
        if channel.guild.id not in self.bot.log_channels:
            return
        embed = discord.Embed(title=f'{channel.type} channel Created'.title(),
                              description=f"**Name:** #{channel.name}"
                                          f"\n**Category:** {channel.category}"
                                          f"\n**Topic:** {discord.utils.remove_markdown(str(channel.topic)) if hasattr(channel, 'topic') and channel.topic else 'None'}",
                              colour=discord.Colour.green(), timestamp=discord.utils.utcnow())
        for target, over in channel.overwrites.items():
            perms = []
            for perm, value in dict(over).items():
                if value is not None:
                    perms.append(f"{str(perm).replace('guild', 'server').replace('_', ' ').title()} {constants.DEFAULT_TICKS[value]}")
            if perms:
                embed.add_field(name=f'Permissions for {target}', value='\n'.join(perms), inline=False)
        embed.set_footer(text=f'Channel ID: {channel.id}')
        self.log(embed, guild=channel.guild, send_to=self.send_to.server)

    @commands.Cog.listener('on_guild_channel_update')
    async def logger_on_guild_channel_update(self, before: guild_channels, after: guild_channels):
        if before.guild.id not in self.bot.log_channels or not self.bot.guild_loggings[after.guild.id].channel_delete:
            return
        deliver = False
        embed = discord.Embed(title=f'{before.type} channel updated'.title(), description=f'**Name:** #{after.name}\n**Category:** {getattr(after.category, "name", "no category")}',
                              colour=discord.Colour.blurple(), timestamp=discord.utils.utcnow())
        embed.set_footer(text=f'Channel ID: {after.id}')
        if before.name != after.name:
            embed.add_field(name='Name updated:', value=f"**From:** {discord.utils.escape_markdown(before.name)}"
                                                        f"\n**To:** {discord.utils.escape_markdown(after.name)}",
                            inline=False)
            deliver = True
        if hasattr(before, 'topic') and hasattr(after, 'topic') and before.topic != after.topic:
            embed.add_field(name='Topic updated', value=f'**Before:** {discord.utils.remove_markdown(str(before.topic))}'
                                                        f'\n**After:** {discord.utils.remove_markdown(str(after.topic))}',
                            inline=False)
            deliver = True
        if before.overwrites != after.overwrites:
            targets = set.union(set(before.overwrites.keys()), set(after.overwrites.keys()))
            for target in targets:
                updated_perms = []
                b_o = dict(before.overwrites_for(target))
                a_o = dict(after.overwrites_for(target))
                for perm, value in b_o.items():
                    if value != a_o[perm]:
                        updated_perms.append(f"{str(perm).replace('server', 'guild').replace('_', ' ').title()}: {constants.SQUARE_TICKS[value]} ➜ {constants.SQUARE_TICKS[a_o[perm]]}")
                if updated_perms:
                    perm_emb = discord.Embed(title=f'Permissions for {target} updated', colour=discord.Colour.blurple(), timestamp=discord.utils.utcnow(),
                                             description='\n'.join(updated_perms))
                    perm_emb.set_footer(text=f'Object ID: {target.id}\nChannel ID: {after.id}')
                    self.log(perm_emb, guild=after.guild, send_to=self.send_to.server)
        if deliver:
            self.log(embed, guild=after.guild, send_to=self.send_to.server)

    @commands.Cog.listener('on_guild_update')
    async def logger_on_guild_update(self, before: discord.Guild, after: discord.Guild):
        if before.id not in self.bot.log_channels or not self.bot.guild_loggings[after.id].server_update:
            return
        if before.icon != after.icon:
            if after.icon and before.icon:
                embed = discord.Embed(title='Server icon updated to:', timestamp=discord.utils.utcnow(), colour=discord.Colour.blue())
                embed.set_footer(text=f'Server ID: {after.id}')
                embed.set_image(url=after.icon.url)
            elif after.icon and not before.icon:
                embed = discord.Embed(title='Server icon set:', timestamp=discord.utils.utcnow(), colour=discord.Colour.green())
                embed.set_footer(text=f'Server ID: {after.id}')
                embed.set_image(url=after.icon.url)
            else:
                embed = discord.Embed(title='Server icon removed', timestamp=discord.utils.utcnow(), colour=discord.Colour.red())
                embed.set_footer(text=f'Server ID: {after.id}')
            self.log(embed, guild=after, send_to=self.send_to.server)
        if before.name != after.name:
            embed = discord.Embed(title='Server Name Updated', timestamp=discord.utils.utcnow(), colour=discord.Colour.blurple(),
                                  description=f"**Before:** {discord.utils.remove_markdown(before.name)}\n"
                                              f"**After:** {discord.utils.escape_markdown(after.name)}")
            embed.set_footer(text=f'Server id: {after.id}')
            self.log(embed, guild=after, send_to=self.send_to.server)
        if before.owner != after.owner:
            embed = discord.Embed(title='Server Owner Updated!', colour=discord.Colour.purple(), timestamp=discord.utils.utcnow(),
                                  description=f"**From:** {discord.utils.escape_markdown(str(before.owner))}\n"
                                              f"**To:** {discord.utils.escape_markdown(str(after.owner))}")
            self.log(embed, guild=after, send_to=self.send_to.server)

    @commands.Cog.listener('on_guild_role_create')
    async def logger_on_guild_role_create(self, role: discord.Role):
        if role.guild.id not in self.bot.log_channels or not self.bot.guild_loggings[role.guild.id].role_create:
            return
        embed = discord.Embed(title='New Role Created', timestamp=discord.utils.utcnow(), colour=discord.Colour.green(),
                              description=f"**Name:** {role.name}\n"
                                          f"**Show Separately:** {constants.DEFAULT_TICKS[role.hoist]} • **Color:** {role.color}\n"
                                          f"**Mentionable:** {constants.DEFAULT_TICKS[role.mentionable]} • **Position:** {role.position}\n")
        enabled = ', '.join([str(name).replace('guild', 'server').replace('_', ' ').title() for name, value in set(role.permissions) if value is True])
        embed.add_field(name='Permissions enabled:', value=enabled, inline=False)
        embed.set_footer(text=f'Role ID: {role.id}')
        self.log(embed, guild=role.guild, send_to=self.send_to.server)

    @commands.Cog.listener('on_guild_role_delete')
    async def logger_on_guild_role_delete(self, role: discord.Role):
        if role.guild.id not in self.bot.log_channels or not self.bot.guild_loggings[role.guild.id].role_delete:
            return
        embed = discord.Embed(title='Role Deleted', timestamp=discord.utils.utcnow(), colour=discord.Colour.red(),
                              description=f"**Name:** {role.name}\n"
                                          f"**Show Separately:** {constants.DEFAULT_TICKS[role.hoist]} • **Color:** {role.color}\n"
                                          f"**Mentionable:** {constants.DEFAULT_TICKS[role.mentionable]} • **Position:** {role.position}\n"
                                          f"**Created At:** {discord.utils.format_dt(role.created_at)} ({discord.utils.format_dt(role.created_at, style='R')})\n"
                                          f"**Amount of Members:** {len(role.members)}")
        enabled = ', '.join([str(name).replace('guild', 'server').replace('_', ' ').title() for name, value in set(role.permissions) if value is True])
        embed.add_field(name='Permissions enabled:', value=enabled, inline=False)
        embed.set_footer(text=f'Role ID: {role.id}')
        self.log(embed, guild=role.guild, send_to=self.send_to.server)

    @commands.Cog.listener('on_guild_role_update')
    async def logger_on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if before.guild.id not in self.bot.log_channels or not self.bot.guild_loggings[after.guild.id].role_edit:
            return
        embed = discord.Embed(title='Role Updated', timestamp=discord.utils.utcnow(), colour=discord.Colour.blurple())
        deliver = False

        if before.permissions != after.permissions:
            before_true = [str(name).replace('guild', 'server').replace('_', ' ').title() for name, value in set(before.permissions) if value is True]
            before_false = [str(name).replace('guild', 'server').replace('_', ' ').title() for name, value in set(before.permissions) if value is False]
            after_true = [str(name).replace('guild', 'server').replace('_', ' ').title() for name, value in set(after.permissions) if value is True]
            after_false = [str(name).replace('guild', 'server').replace('_', ' ').title() for name, value in set(after.permissions) if value is False]
            added = ''
            if before_true != after_true:
                added = set(after_true) - set(before_true)
                if added:
                    added = f"**Added:** {', '.join(added)}\n"
                else:
                    added = ''
            removed = ''
            if after_false != before_false:
                removed = set(after_false) - set(before_false)
                if removed:
                    removed = f"**Removed:** {', '.join(removed)}"
                else:
                    removed = ''
            embed.add_field(name='Permissions Updated:', value=added+removed, inline=False)
            deliver = True

        hoist_update = ''
        if before.hoist != after.hoist:
            hoist_update = f"\n**Show Separately:** {constants.DEFAULT_TICKS[before.hoist]} ➜ {constants.DEFAULT_TICKS[after.hoist]}"
            deliver = True

        ping_update = ''
        if before.mentionable != after.mentionable:
            ping_update = f"\n**Mentionable:** {constants.DEFAULT_TICKS[before.mentionable]} ➜ {constants.DEFAULT_TICKS[after.mentionable]}"
            deliver = True

        role_update = f'**Name:** {after.name}'
        if before.name != after.name:
            role_update = f"**Name:**\n**Before:** {discord.utils.remove_markdown(before.name)}" \
                          f"\n**After:** {discord.utils.remove_markdown(after.name)}"
            deliver = True

        color_update = ''
        if before.color != after.color:
            color_update = f"\n**Updated Color:** `{before.color}` ➜ `{after.color}`"
            deliver = True

        position_update = ''
        if before.position != after.position:
            position_update = f"\n**Updated Position:** `{before.position}` ➜ `{after.position}`"
            # Added just in case, but we don't set deliver to True, so it will only
            # be sent to the logs if other attributes of the role have changed

        embed.description = role_update + hoist_update + ping_update + color_update + position_update
        if deliver:
            self.log(embed, guild=after.guild, send_to=self.send_to.server)

    @commands.Cog.listener('on_guild_emojis_update')
    async def logger_on_guild_emojis_update(self, guild: discord.Guild, before: typing.Sequence[discord.Emoji], after: typing.Sequence[discord.Emoji]):
        if guild.id not in self.bot.log_channels:
            return
        added = [e for e in after if e not in before]
        removed = [e for e in before if e not in after]
        for emoji in added:
            if not self.bot.guild_loggings[guild.id].emoji_create:
                break
            embed = discord.Embed(title='Emoji Created', colour=discord.Colour.green(), timestamp=discord.utils.utcnow(),
                                  description=f"{emoji} - [{emoji.name}]({emoji.url})")
            embed.set_footer(text=f"Emoji ID: {emoji.id}")
            self.log(embed, guild=guild, send_to=self.send_to.server)
        for emoji in removed:
            if not self.bot.guild_loggings[guild.id].emoji_delete:
                break
            embed = discord.Embed(title='Emoji Deleted', colour=discord.Colour.red(), timestamp=discord.utils.utcnow(),
                                  description=f"{emoji.name}"
                                              f"\n**Created at:** {discord.utils.format_dt(emoji.created_at)} ({discord.utils.format_dt(emoji.created_at, style='R')})")
            embed.set_footer(text=f"Emoji ID: {emoji.id}")
            self.log(embed, guild=guild, send_to=self.send_to.server)

        existant = set.union(set(after) - set(added), set(before) - set(removed))
        for emoji in existant:
            if not self.bot.guild_loggings[guild.id].emoji_update:
                break
            before_emoji = discord.utils.get(before, id=emoji.id)
            after_emoji = emoji
            if before_emoji and after_emoji:
                self.emoji_update(guild, before_emoji, after_emoji)

    def emoji_update(self, guild: discord.Guild, before: discord.Emoji, after: discord.Emoji):
        if before.name == after.name and before.roles == after.roles:
            return
        if not self.bot.guild_loggings[guild.id].emoji_update:
            return
        embed = discord.Embed(title='Emoji Updated', colour=discord.Colour.blurple(), timestamp=discord.utils.utcnow(), description=f'{str(after)} | [{after.name}]({after.url})')
        embed.set_footer(text=f"Emoji ID: {after.id}")
        if before.name != after.name:
            embed.add_field(name='Name updated:', inline=False,
                            value=f"**Before:** {before.name}\n**After:** {after.name}")
        if before.roles != after.roles:
            added = set(after.roles) - set(before.roles)
            removed = set(before.roles) - set(after.roles)
            added_roles = ''
            if added:
                added_roles = f"**Added:** {', '.join([r.mention for r in added])}"
            removed_roles = ''
            if removed:
                removed_roles = f"\n**Removed:** {', '.join([r.mention for r in removed])}"
            embed.add_field(name='Roles updated', inline=False,
                            value=added_roles+removed_roles)
        self.log(embed, guild=guild, send_to=self.send_to.server)

    @commands.Cog.listener('on_guild_stickers_update')
    async def logger_on_guild_stickers_update(self, guild: discord.Guild, before: typing.Sequence[discord.Sticker], after: typing.Sequence[discord.Sticker]):
        if guild.id not in self.bot.log_channels:
            return
        added = [s for s in after if s not in before]
        removed = [s for s in before if s not in after]
        for sticker in added:
            if not self.bot.guild_loggings[guild.id].sticker_create:
                break
            embed = discord.Embed(title='Sticker Created', colour=discord.Colour.green(), timestamp=discord.utils.utcnow(),
                                  description=f"[{sticker.name}]({sticker.url})")
            if sticker.description:
                embed.add_field(name='Description:', value=sticker.description, inline=False)
            embed.set_footer(text=f"Sticker ID: {sticker.id}")
            self.log(embed, guild=guild, send_to=self.send_to.server)
        for sticker in removed:
            if not self.bot.guild_loggings[guild.id].sticker_delete:
                break
            embed = discord.Embed(title='Sticker Deleted', colour=discord.Colour.red(), timestamp=discord.utils.utcnow(),
                                  description=f"{sticker.name}"
                                              f"\n**Created at:** {discord.utils.format_dt(sticker.created_at)} ({discord.utils.format_dt(sticker.created_at, style='R')})")
            if sticker.description:
                embed.add_field(name='Description:', value=sticker.description, inline=False)
            embed.set_footer(text=f"Sticker ID: {sticker.id}")
            self.log(embed, guild=guild, send_to=self.send_to.server)

        existant = set.union(set(after) - set(added), set(before) - set(removed))
        for sticker in existant:
            if not self.bot.guild_loggings[guild.id].sticker_update:
                break
            before_sticker = discord.utils.get(before, id=sticker.id)
            after_sticker = sticker
            if before_sticker and after_sticker:
                self.sticker_update(guild, before_sticker, after_sticker)

    def sticker_update(self, guild: discord.Guild, before: discord.Sticker, after: discord.Sticker):
        if before.description == after.description and before.name == after.name:
            return
        if not self.bot.guild_loggings[guild.id].sticker_update:
            return
        embed = discord.Embed(title='Sticker Updated', colour=discord.Colour.blurple(), timestamp=discord.utils.utcnow(),
                              description=f"[{after.name}]({after.url})")
        if before.name != after.name:
            embed.add_field(name='Name updated:', inline=False,
                            value=f"**Before:** {before.name}\n**After:** {after.name}")
        if before.description != after.description:
            embed.add_field(name='Name updated:', inline=False,
                            value=f"**Before:** {before.description}\n**After:** {after.description}")
        self.log(embed, guild=guild, send_to=self.send_to.server)
