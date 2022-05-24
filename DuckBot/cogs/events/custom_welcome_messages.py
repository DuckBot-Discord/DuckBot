import discord
from discord.ext import commands

from ._base import EventsBase


class WelcomeMessages(EventsBase):
    @commands.Cog.listener('on_message')
    async def on_count_receive(self, message: discord.Message):
        if (
            message.author.bot
            or not message.guild
            or message.guild.id not in self.bot.counting_channels
            or message.channel.id != self.bot.counting_channels[message.guild.id]['channel']
        ):
            return
        if not message.content.isdigit() or message.content != str(
            self.bot.counting_channels[message.guild.id]['number'] + 1
        ):
            if message.author.id == self.bot.counting_channels[message.guild.id]['last_counter']:
                return await message.delete(delay=0)
            if self.bot.counting_channels[message.guild.id]['delete_messages'] is True:
                return await message.delete(delay=0)
            elif self.bot.counting_channels[message.guild.id]['reset'] is True:
                self.bot.counting_channels[message.guild.id]['number'] = 0
                await message.reply(f'{message.author.mention} just put the **wrong number**! Start again from **0**')
                await self.bot.db.execute(
                    'UPDATE count_settings SET current_number = $2 WHERE guild_id = $1', message.guild.id, 0
                )
                return
        if message.author.id == self.bot.counting_channels[message.guild.id]['last_counter']:
            return await message.delete(delay=0)
        self.bot.counting_channels[message.guild.id]['number'] += 1
        self.bot.counting_channels[message.guild.id]['last_counter'] = message.author.id
        self.bot.counting_channels[message.guild.id]['last_message_id'] = message.id
        self.bot.counting_channels[message.guild.id]['messages'].append(message)
        await self.bot.db.execute(
            'UPDATE count_settings SET current_number = $2 WHERE guild_id = $1',
            message.guild.id,
            self.bot.counting_channels[message.guild.id]['number'],
        )
        if (
            message.guild.id not in self.bot.counting_rewards
            or int(message.content) not in self.bot.counting_rewards[message.guild.id]
        ):
            return
        reward = await self.bot.db.fetchrow(
            "SELECT * FROM counting WHERE (guild_id, reward_number) = ($1, $2)",
            message.guild.id,
            self.bot.counting_channels[message.guild.id]['number'],
        )
        if not reward:
            return
        msg = reward['reward_message']
        if msg:
            try:
                m = await message.channel.send(msg)
                self.bot.saved_messages[message.id] = m
            except (discord.Forbidden, discord.HTTPException):
                pass
        role = reward['role_to_grant']
        if role:
            role = message.guild.get_role(role)
            if role:
                try:
                    await message.author.add_roles(role)
                except (discord.Forbidden, discord.HTTPException):
                    pass
        reaction = reward['reaction_to_add']
        if reaction:
            try:
                try:
                    await message.add_reaction(reaction)
                except (discord.NotFound, discord.InvalidArgument):
                    await message.add_reaction('🎉')
            except (discord.Forbidden, discord.HTTPException):
                pass

    @commands.Cog.listener('on_raw_message_delete')
    async def on_counting_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if not payload.guild_id or payload.guild_id not in self.bot.counting_channels:
            return
        if payload.message_id == self.bot.counting_channels[payload.guild_id]['last_message_id']:
            self.bot.counting_channels[payload.guild_id]['messages'].pop()
            self.bot.counting_channels[payload.guild_id]['number'] -= 1
            try:
                message = self.bot.counting_channels[payload.guild_id]['messages'][-1]
                self.bot.counting_channels[payload.guild_id]['number'] = int(message.content)
                self.bot.counting_channels[payload.guild_id]['last_message_id'] = message.id
                self.bot.counting_channels[payload.guild_id]['last_counter'] = message.author.id
            except (KeyError, IndexError):
                self.bot.counting_channels[payload.guild_id]['last_message_id'] = None
                self.bot.counting_channels[payload.guild_id]['last_counter'] = None
            await self.bot.db.execute(
                'UPDATE count_settings SET current_number = $2 WHERE guild_id = $1',
                payload.guild_id,
                self.bot.counting_channels[payload.guild_id]['number'],
            )
        else:
            try:
                message = [
                    m for m in list(self.bot.counting_channels[payload.guild_id]['messages']) if m.id == payload.message_id
                ][0]
                self.bot.counting_channels[payload.guild_id]['messages'].remove(message)
            except (KeyError, IndexError):
                pass

        if payload.message_id in self.bot.saved_messages:
            m = self.bot.saved_messages.pop(payload.message_id)
            await m.delete(delay=0)
