import logging

import asyncpg
import discord
from discord.ext import commands

from ._base import EventsBase


class BlackoutMode(EventsBase):

    BLACKOUT_ROLE_ID = 942886948626923540
    BLACKOUT_MESSAGE_ID = 942886805022330910
    BLACKOUT_GUILD_ID = 774561547930304536

    @commands.Cog.listener('on_raw_reaction_add')
    async def blackout_mode_add_handler(self, payload: discord.RawReactionActionEvent):
        if self.bot.user.id != 788278464474120202:
            return
        if getattr(payload.member, 'bot', True):
            return
        if payload.message_id != self.BLACKOUT_MESSAGE_ID:
            return
        if str(payload.emoji) != '\N{BLACK SQUARE FOR STOP}\N{VARIATION SELECTOR-16}':
            return
        if not payload.member:
            return  # This should never happen

        message = self.bot.get_channel(payload.channel_id).get_partial_message(payload.message_id)

        try:
            await message.remove_reaction(payload.emoji, payload.member)
        except discord.HTTPException:
            logging.error('could not remove reaction:', exc_info=True)

        db: asyncpg.Pool = self.bot.db
        if not (await db.fetchval('SELECT roles FROM blackout WHERE user_id = $1', payload.member.id)):
            to_remove = [r for r in payload.member.roles if r.is_assignable()]
            role = self.bot.get_guild(payload.guild_id).get_role(self.BLACKOUT_ROLE_ID)
            if not role:
                return
            await db.execute(
                'INSERT INTO blackout (user_id, roles) VALUES ($1, $2)', payload.member.id, [r.id for r in to_remove]
            )
            try:
                await payload.member.remove_roles(*to_remove, reason='Blackout mode')
            except discord.HTTPException:
                logging.error('could not remove roles', exc_info=True)
            try:
                await payload.member.add_roles(role, reason='Blackout mode')
            except Exception as e:
                logging.error('could not add role', exc_info=True)

        else:
            roles = (await db.fetchval('SELECT roles FROM blackout WHERE user_id = $1', payload.member.id)) or []
            guild = self.bot.get_guild(payload.guild_id)
            to_add = []
            for role_id in roles:
                role = guild.get_role(role_id)
                if role:
                    to_add.append(role)
            await payload.member.add_roles(*to_add, reason='Blackout mode ended')
            role = guild.get_role(self.BLACKOUT_ROLE_ID)
            if role:
                await payload.member.remove_roles(role, reason='Blackout mode ended')
            await db.execute('DELETE FROM blackout WHERE user_id = $1', payload.member.id)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        if channel.guild.id != self.BLACKOUT_GUILD_ID:
            return
        await channel.set_permissions(
            channel.guild.get_role(self.BLACKOUT_ROLE_ID), view_channel=False, reason=f'automatic Blackout mode'
        )
