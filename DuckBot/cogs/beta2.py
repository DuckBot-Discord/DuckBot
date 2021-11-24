import asyncio
from collections import namedtuple

import discord
import typing
from discord.ext import commands, tasks

from DuckBot.__main__ import DuckBot
from DuckBot.helpers import constants

guild_channels = typing.Union[discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel, discord.TextChannel]
invalidated_webhook = 'https://canary.discord.com/api/webhooks/000000000000000000/_LQ1qItzrwhNj47TZEagmEgnjBJhCeLIIAE48M61S3XojN5bQuq8JM_kjv4cwCglYJlp'


def setup(bot):
    bot.add_cog(LoggingBackend(bot))


class LoggingBackend(commands.Cog):

    def __init__(self, bot):
        self.bot: DuckBot = bot
        self.deliver_logs.start()
        _nt_send_to = namedtuple('send_to', ['default', 'message', 'member', 'join_leave', 'voice', 'server'])
        self.send_to = _nt_send_to(default='default', message='message', member='member', join_leave='join_leave', server='server', voice='voice')

    def cog_unload(self) -> None:
        self.deliver_logs.cancel()

    def log(self, embed, *, guild: typing.Union[discord.Guild, int], send_to: str = 'default'):
        guild_id = getattr(guild, 'id', guild)
        if guild_id in self.bot.log_channels:
            self.bot.log_cache[guild_id][send_to].append(embed)

    @tasks.loop(seconds=3)
    async def deliver_logs(self):
        for guild_id, webhooks in self.bot.log_channels.items():
            for deliver_type, cache in self.bot.log_cache[guild_id].items():

                embeds = self.bot.log_cache[guild_id][deliver_type][:10]
                self.bot.log_cache[guild_id][deliver_type] = self.bot.log_cache[guild_id][deliver_type][10:]
                webhook_url = getattr(webhooks, deliver_type, None)
                if embeds:
                    if webhook_url:
                        webhook = discord.Webhook.from_url(webhook_url or invalidated_webhook, bot_token=self.bot.http.token, session=self.bot.session)
                        try:
                            await webhook.send(embeds=embeds)
                        except discord.NotFound:
                            self.bot.loop.create_task(self.create_and_deliver(embeds=embeds, deliver_type=deliver_type, guild_id=guild_id))
                            await asyncio.sleep(1)
                        except Exception as e:
                            print('Error during task!')
                            print(e)
                    else:
                        deliver_type = self.send_to.default
                        webhook_url = webhooks.default
                        webhook = discord.Webhook.from_url(webhook_url or invalidated_webhook, bot_token=self.bot.http.token, session=self.bot.session)
                        try:
                            await webhook.send(embeds=embeds)
                        except discord.NotFound:
                            self.bot.loop.create_task(self.create_and_deliver(embeds=embeds, deliver_type=deliver_type, guild_id=guild_id))
                            await asyncio.sleep(1)
                        except Exception as e:
                            print('Error during task!')
                            print(e)

    @deliver_logs.before_loop
    async def wait(self):
        await self.bot.wait_until_ready()

    async def create_and_deliver(self, embeds: typing.List[discord.Embed], deliver_type: str, guild_id: int):
        if deliver_type not in {'default', 'message', 'member', 'join_leave', 'voice', 'server'}:
            raise AttributeError('Improper delivery type passed')
        chennel_ids = await self.bot.db.fetchrow(f'SELECT * FROM log_channels WHERE guild_id = $1', guild_id)
        channel_id = chennel_ids[f"{deliver_type}_chid"]
        channel: discord.TextChannel = self.bot.get_channel(channel_id)
        if not channel and deliver_type != self.send_to.default:
            for e in embeds:
                e.footer.text = e.footer.text + f'\nCould not deliver to the {deliver_type} channel. Sent here instead!\n' \
                                                f'Please set or set the {deliver_type} channel. do `db.help log` for info.'
                self.log(e, guild=guild_id, send_to=self.send_to.default)
            return
        if channel.permissions_for(channel.guild.me).manage_webhooks:
            webhooks_list = await channel.webhooks()
            for w in webhooks_list:
                if w.user == self.bot.user:
                    webhook = w
                    break
            else:
                webhook = await channel.create_webhook(name='DuckBot Logging', avatar=await self.bot.user.avatar.read(), reason='DuckBot Logging channel')
            await self.bot.db.execute(f'UPDATE log_channels SET {deliver_type}_channel = $1', webhook.url)
            if deliver_type == 'default':
                self.bot.log_channels[channel.guild.id]._replace(default=webhook.url)
            elif deliver_type == 'message':
                self.bot.log_channels[channel.guild.id]._replace(message=webhook.url)
            elif deliver_type == 'member':
                self.bot.log_channels[channel.guild.id]._replace(member=webhook.url)
            elif deliver_type == 'join_leave':
                self.bot.log_channels[channel.guild.id]._replace(join_leave=webhook.url)
            elif deliver_type == 'voice':
                self.bot.log_channels[channel.guild.id]._replace(voice=webhook.url)
            elif deliver_type == 'server':
                self.bot.log_channels[channel.guild.id]._replace(server=webhook.url)
            await webhook.send(embeds=embeds)
        elif not deliver_type != self.send_to.default:
            for e in embeds:
                e.footer.text = e.footer.text + f'\nCould not deliver to the {deliver_type} channel. Sent here instead!\n' \
                                                f'Please give me manage_webhooks permissions in #{channel.name}.'
                self.log(e, guild=guild_id, send_to=self.send_to.default)
        else:
            await channel.send(f'An error occurred delivering the message to {channel.mention}!'
                               f'\nPlease check if I have the **Manage Webhook** permissions in all the log channels!'
                               f'\nAnd also check that {channel.mention} has less than 10 webhooks, **or** it already has one webhook owned by {channel.guild.me.mention}')

    @commands.Cog.listener('on_message_delete')
    async def logger_on_message_delete(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild or message.guild.id not in self.bot.log_channels or not self.bot.guild_loggings[message.guild.id].message_delete:
            return
        if message.guild.id in self.bot.log_channels:
            embed = discord.Embed(title=f'Message deleted in #{message.channel}',
                                  description=(message.content or '\u200b')[0:4000],
                                  colour=discord.Colour.red(), timestamp=discord.utils.utcnow())
            embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
            embed.set_footer(text=f"Channel: {message.channel.id}")
            if message.attachments:
                embed.add_field(name='Attachments:', value='\n'.join([a.filename for a in message.attachments]), inline=False)
            if message.stickers:
                embed.add_field(name='Stickers:', value='\n'.join([a.name for a in message.stickers]), inline=False)
            self.log(embed, guild=message.guild, send_to=self.send_to.message)

    @commands.Cog.listener('on_raw_bulk_message_delete')
    async def logger_on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        if not payload.guild_id or payload.guild_id not in self.bot.log_channels or not self.bot.guild_loggings[payload.guild_id].message_purge:
            return
        embed = discord.Embed(title=f'{len(payload.message_ids)} messages purged in #{self.bot.get_channel(payload.channel_id)}',
                              colour=discord.Colour.red(), timestamp=discord.utils.utcnow())
        msgs = []
        for message in payload.cached_messages:
            if message.author.bot:
                continue
            if message.attachments:
                attachment = f'{len(message.attachments)} attachments: ' + message.attachments[0].filename
            elif message.stickers:
                attachment = 'Sticker: ' + message.stickers[0].name
            else:
                attachment = None
            message = f"{discord.utils.remove_markdown(str(message.author))} > {message.content or attachment or '-'}"
            if len(message) > 200:
                message = message[0:200] + '...'
            msgs.append(message)
            if len('\n'.join(msgs)[0:4096]) > 4000:
                break
        embed.description = '\n'.join(msgs)[0:4000]
        embed.add_field(name='Showing: ', value=f"{len(msgs)}/{len(payload.message_ids)} messages.", inline=False)
        embed.set_footer(text=f'Channel: {payload.channel_id}')
        self.log(embed, guild=payload.guild_id, send_to=self.send_to.message)

    @commands.Cog.listener('on_message_edit')
    async def logger_on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.guild.id not in self.bot.log_channels or not self.bot.guild_loggings[after.guild.id].message_edit:
            return
        if not self.bot.guild_loggings[before.guild.id].message_edit:
            return
        if before.guild.id in self.bot.log_channels:
            if before.content == after.content and before.attachments == after.attachments and before.stickers == after.stickers:
                return
            embed = discord.Embed(title=f'Message edited in #{before.channel}',
                                  colour=discord.Colour.blurple(), timestamp=discord.utils.utcnow())
            embed.set_author(name=str(before.author), icon_url=before.author.display_avatar.url)
            embed.set_footer(text=f"Channel: {before.channel.id}")

            embed.add_field(name='**__Before:__**', value=before.content[0:1024], inline=False)
            embed.add_field(name='**__After:__**', value=after.content[0:1024], inline=False)
            if before.attachments and before.attachments != after.attachments:
                af = after.attachments
                attachments = []
                for a in before.attachments:
                    if a in af:
                        attachments.append(a.filename)
                    else:
                        attachments.append(f"[Removed] ~~{a.filename}~~")
                embed.add_field(name='Attachments:', value='\n'.join(attachments), inline=False)
            embed.add_field(name='Jump:', value=f'[[Jump to message]]({after.jump_url})', inline=False)
            self.log(embed, guild=before.guild, send_to=self.send_to.message)

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
                    embed.add_field(name=f'Updated {target}', value='\n'.join(updated_perms), inline=False)
            deliver = True
        if deliver:
            self.log(embed, guild=after.guild, send_to=self.send_to.server)

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
            deliver = True

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
