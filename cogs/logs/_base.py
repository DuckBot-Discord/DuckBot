import asyncio
import logging
from collections import namedtuple

import discord
import typing
from discord.ext import commands, tasks

from DuckBot.__main__ import DuckBot

guild_channels = typing.Union[discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel, discord.TextChannel]
invalidated_webhook = 'https://canary.discord.com/api/webhooks/000000000000000000/_LQ1qItzrwhNj47TZEagmEgnjBJhCeLIIAE48M61S3XojN5bQuq8JM_kjv4cwCglYJlp'


class LoggingBase(commands.Cog):
    def __init__(self, bot):
        self.bot: DuckBot = bot
        self.deliver_logs.start()
        _nt_send_to = namedtuple('send_to', ['default', 'message', 'member', 'join_leave', 'voice', 'server'])
        self.send_to = _nt_send_to(default='default', message='message', member='member', join_leave='join_leave',
                                   server='server', voice='voice')

    def cog_unload(self) -> None:
        self.deliver_logs.cancel()

    def log(self, embed, *, guild: typing.Union[discord.Guild, int], send_to: str = 'default'):
        guild_id = getattr(guild, 'id', guild)
        if guild_id in self.bot.log_channels:
            self.bot.log_cache[guild_id][send_to].append(embed)

    @tasks.loop(seconds=3)
    async def deliver_logs(self):
        try:
            for guild_id, webhooks in self.bot.log_channels.items():
                for deliver_type, cache in self.bot.log_cache[guild_id].items():

                    embeds = self.bot.log_cache[guild_id][deliver_type][:10]
                    self.bot.log_cache[guild_id][deliver_type] = self.bot.log_cache[guild_id][deliver_type][10:]
                    webhook_url = getattr(webhooks, deliver_type, None)
                    if embeds:
                        if webhook_url:
                            webhook = discord.Webhook.from_url(webhook_url or invalidated_webhook,
                                                               bot_token=self.bot.http.token, session=self.bot.session)
                            try:
                                await webhook.send(embeds=embeds)
                            except discord.NotFound:
                                self.bot.loop.create_task(
                                    self.create_and_deliver(embeds=embeds, deliver_type=deliver_type,
                                                            guild_id=guild_id))
                                await asyncio.sleep(1)
                            except Exception as e:
                                print('Error during task!')
                                print(e)
                        else:
                            deliver_type = self.send_to.default
                            webhook_url = webhooks.default
                            webhook = discord.Webhook.from_url(webhook_url or invalidated_webhook,
                                                               bot_token=self.bot.http.token, session=self.bot.session)
                            try:
                                await webhook.send(embeds=embeds)
                            except discord.NotFound:
                                self.bot.loop.create_task(
                                    self.create_and_deliver(embeds=embeds, deliver_type=deliver_type,
                                                            guild_id=guild_id))
                                await asyncio.sleep(1)
                            except Exception as e:
                                print('Error during task!')
                                print(e)
        except Exception as e:  # noqa
            try:
                await self.bot.on_error('channel_logs')
            except Exception as e:
                logging.error('something happened while task was running', exc_info=e)

    @deliver_logs.before_loop
    async def wait(self):
        await self.bot.wait_until_ready()

    # noinspection PyProtectedMember
    async def create_and_deliver(self, embeds: typing.List[discord.Embed], deliver_type: str, guild_id: int):
        if deliver_type not in {'default', 'message', 'member', 'join_leave', 'voice', 'server'}:
            raise AttributeError('Improper delivery type passed')
        chennel_ids = await self.bot.db.fetchrow(f'SELECT * FROM log_channels WHERE guild_id = $1', guild_id)
        channel_id: int = chennel_ids[f"{deliver_type}_chid"]
        channel: discord.TextChannel = self.bot.get_channel(channel_id)  # type: ignore
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
                webhook = await channel.create_webhook(name='DuckBot Logging', avatar=await self.bot.user.avatar.read(),
                                                       reason='DuckBot Logging channel')
            # noinspection SqlResolve
            await self.bot.db.execute(f"UPDATE log_channels SET {deliver_type}_channel = $1", webhook.url)
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
