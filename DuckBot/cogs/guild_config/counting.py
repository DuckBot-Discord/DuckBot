import asyncio
from collections import deque

import asyncpg.exceptions
import discord
from discord.ext import commands

from DuckBot.__main__ import CustomContext
from DuckBot.cogs.management import UnicodeEmoji
from ._base import ConfigBase


class Counting(ConfigBase):
    async def update_rewards(
        self,
        *,
        guild: discord.Guild,
        reward_number: int,
        message: str = None,
        role: discord.Role = None,
        reaction: str = None,
    ):
        if not any([message, role, reaction]):
            await self.bot.db.execute(
                "DELETE FROM counting WHERE (guild_id, reward_number) = ($1, $2)", guild.id, reward_number
            )
            try:
                self.bot.counting_rewards[guild.id].remove(reward_number)
            except KeyError:
                pass
            return reward_number
        await self.bot.db.execute(
            'INSERT INTO counting (guild_id, reward_number, reward_message, '
            'role_to_grant, reaction_to_add) VALUES ($1, $2, $3, $4, $5) '
            'ON CONFLICT (guild_id, reward_number) DO UPDATE SET '
            'reward_message = $3, role_to_grant = $4, reaction_to_add = $5',
            guild.id,
            reward_number,
            message,
            getattr(role, 'id', None),
            reaction,
        )
        try:
            self.bot.counting_rewards[guild.id].add(reward_number)
        except KeyError:
            self.bot.counting_rewards[guild.id] = {reward_number}
        return reward_number

    @commands.group(aliases=['ct'])
    async def counting(self, ctx: CustomContext):
        """Base command for setting up counting"""
        if ctx.invoked_subcommand is None:
            p = ctx.clean_prefix
            embed = discord.Embed(
                title='How to set up counting',
                description='**__Counting is a fun game, where users count up in a channel.__**'
                '\nThis game can be as simple or complex as **you** want.'
                '\nIt has support for a **rewards system**, which will allow'
                '\nfor **special messages** when certain goals are achieved. Also'
                '\nsupport for adding **roles** to the user who reached that goal, or'
                '\nif that\'s too much for you, it can simply add a **reaction** to the'
                '\nmessage that reached the goal.'
                '\n'
                '\nHere are some configuration commands for setting up this game.'
                f'\n_PS: for more info do `{p}help counting`_'
                f'\n'
                f'\n`{p}ct set-channel <channel>`'
                f'\n`{p}ct unset-channel <channel>`'
                f'\n`{p}ct add-reward` *(interactive command)*'
                f'\n`{p}ct remove-reward <number>`'
                f'\n`{p}ct all-rewards`'
                f'\n`{p}ct check-reward <level>`'
                f'\n`{p}ct override-number <number>`',
            )
            embed.set_footer(text='All sub-commands require Manage Server permission')
            return await ctx.send(embed=embed)

    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_messages=True)
    @counting.command(name='set-channel')
    async def ct_set_channel(self, ctx: CustomContext, channel: discord.TextChannel):
        """Sets this server's count channel"""
        try:
            await ctx.trigger_typing()
        except (discord.Forbidden, discord.HTTPException):
            pass
        try:
            await self.bot.db.execute(
                'INSERT INTO prefixes (guild_id) VALUES ($1) ' 'ON CONFLICT (guild_id) DO NOTHING', ctx.guild.id
            )
            await self.bot.db.execute(
                'INSERT INTO count_settings (guild_id, channel_id) VALUES ($1, $2)', ctx.guild.id, channel.id
            )
            self.bot.counting_channels[ctx.guild.id] = {
                'channel': channel.id,
                'number': 0,
                'last_counter': None,
                'delete_messages': True,
                'reset': False,
                'last_message_id': None,
                'messages': deque(maxlen=100),
            }
            await ctx.send(f'✅ **|** Set the **counting channel** to {channel.mention}')
        except asyncpg.UniqueViolationError:
            if (
                ctx.guild.id in self.bot.counting_channels
                and self.bot.counting_channels[ctx.guild.id]['channel'] != channel.id
            ) or (ctx.guild.id not in self.bot.counting_channels):
                confirm = await ctx.confirm(
                    '⚠ **|** There is already a **counting channel**! Would you like to **update it** and reset the count number to **0**?',
                    return_message=True,
                )
                if confirm[0] is True:
                    await self.bot.db.execute(
                        'INSERT INTO prefixes (guild_id) VALUES ($1) ' 'ON CONFLICT (guild_id) DO NOTHING', ctx.guild.id
                    )
                    await self.bot.db.execute(
                        'INSERT INTO count_settings (guild_id, channel_id, current_number) VALUES ($1, $2, 1)'
                        'ON CONFLICT (guild_id) DO UPDATE SET channel_id = $2, current_number = 0',
                        ctx.guild.id,
                        channel.id,
                    )
                    try:
                        self.bot.counting_channels[ctx.guild.id]['channel'] = channel.id
                        self.bot.counting_channels[ctx.guild.id]['number'] = 0
                        self.bot.counting_channels[ctx.guild.id]['last_counter'] = None
                        self.bot.counting_channels[ctx.guild.id]['messages'] = deque(maxlen=100)
                    except KeyError:
                        self.bot.counting_channels[ctx.guild.id] = {
                            'channel': channel.id,
                            'number': 0,
                            'last_counter': None,
                            'delete_messages': True,
                            'reset': False,
                            'last_message_id': None,
                            'messages': deque(maxlen=100),
                        }
                    await confirm[1].edit(
                        content='✅ **|** Updated the **counting channel** and reset the current number to **0**', view=None
                    )
                else:
                    await confirm[1].edit(content='❌ **|** Cancelled!', view=None)
            else:
                await ctx.send(f'⚠ **|** {channel.mention} is already the **counting channel**!')

    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_messages=True)
    @counting.command(name='unset-channel')
    async def ct_unset_channel(self, ctx: CustomContext):
        """Unsets this server's counting channel"""
        if ctx.guild.id in self.bot.counting_channels:
            confirm = await ctx.confirm('⚠ **|** Are you sure you **unset** the **counting channel**?', return_message=True)
            if confirm[0] is True:
                self.bot.counting_channels.pop(ctx.guild.id)
                await self.bot.db.execute('DELETE FROM count_settings WHERE guild_id = $1', ctx.guild.id)
                await confirm[1].edit(content='✅ **|** **Unset** this server\'s **counting channel**!', view=None)
            else:
                await confirm[1].edit(content='❌ **|** Cancelled!', view=None)
        else:
            await ctx.send('⚠ **|** This server doesn\'t have a **counting channel**!')

    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_messages=True)
    @counting.command(name='add-reward')
    async def ct_add_reward(self, ctx: CustomContext):
        """An interactive way to add a reward to the counting game."""

        def check(m: discord.Message):
            return m.channel == ctx.channel and m.author == ctx.author

        def int_check(m: discord.Message):
            return m.channel == ctx.channel and m.author == ctx.author and m.content.isdigit()

        try:
            await ctx.send('1️⃣ **|** What **number** would this reward be assigned to?')
            number = int((await self.bot.wait_for('message', check=int_check, timeout=120)).content)

            await ctx.send(
                '2️⃣ **|** What **message** would you want to be sent to the channel when this number is reached?'
                '\nℹ **|** Type `skip` to skip, and `cancel` to cancel'
            )
            message = (await self.bot.wait_for('message', check=check, timeout=120)).content
            if message.lower() == 'cancel':
                return
            message = message if message.lower() != 'skip' else None

            await ctx.send(
                '3️⃣ **|** What **role** would you want to be assigned to the person who reached this number?'
                '\nℹ **|** Type `skip` to skip, and `cancel` to cancel'
            )
            role = False
            while role is False:
                role = (await self.bot.wait_for('message', check=check, timeout=120)).content
                if role.lower() == 'cancel':
                    return
                try:
                    role = await commands.RoleConverter().convert(ctx, role) if role.lower() != 'skip' else None
                except commands.RoleNotFound:
                    role = False

            await ctx.send(
                '4️⃣ **|** What **reaction** would you like to be added to the message?'
                '\nℹ **|** Type `skip` to skip, and `cancel` to cancel'
            )
            emoji = False
            while emoji is False:
                emoji = (await self.bot.wait_for('message', check=check, timeout=120)).content
                if emoji.lower() == 'cancel':
                    return
                try:
                    emoji = (
                        str(
                            (await UnicodeEmoji().convert(ctx, emoji))
                            or (await commands.EmojiConverter().convert(ctx, emoji))
                        )
                        if emoji.lower() != 'skip'
                        else None
                    )
                    if isinstance(emoji, discord.Emoji) and not emoji.is_usable():
                        emoji = None
                except commands.EmojiNotFound:
                    emoji = False

            try:
                if number in self.bot.counting_rewards[ctx.guild.id]:
                    confirm = await ctx.confirm(
                        f'⚠ **|** **{number} has already a reward associated with it, would you like to overwrite it?',
                        delete_after_confirm=True,
                        delete_after_timeout=False,
                        delete_after_cancel=False,
                    )
                    if confirm is False:
                        return
            except KeyError:
                pass

            await self.update_rewards(guild=ctx.guild, reward_number=number, message=message, role=role, reaction=emoji)
            await ctx.send(f'✅ **|** Added **reward** for number **{number}**')

        except asyncio.TimeoutError:
            return await ctx.send('⚠ **|** Timed out! Please try again.')

    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_messages=True)
    @counting.command(name='remove-reward')
    async def ct_remove_reward(self, ctx: CustomContext, number: int):
        """Removes one of the counting rewards"""
        if ctx.guild.id not in self.bot.counting_rewards:
            return await ctx.send('⚠ **|** This server doesn\'t have a **counting channel**!')
        if number in self.bot.counting_rewards[ctx.guild.id]:
            confirm = await ctx.confirm(
                f'⚠ **|** would you like to remove **{number}** from the rewards?', return_message=True
            )

            if confirm[0] is False:
                return await confirm[1].edit(content='❌ **|** Cancelled!', view=None)

            try:
                self.bot.counting_rewards[ctx.guild.id].remove(number)
            except KeyError:
                pass
            await self.bot.db.execute(
                'DELETE FROM counting WHERE (guild_id, reward_number) = ($1, $2)', ctx.guild.id, number
            )
        else:
            await ctx.send('⚠ **|** That is not one of the **counting rewards**!')

    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_messages=True)
    @counting.command(name='all-rewards')
    async def ct_all_rewards(self, ctx: CustomContext):
        """[TODO] Shows all the counting rewards"""
        await ctx.send('WIP - coming soon!')

    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_messages=True)
    @counting.command(name='check-reward')
    async def ct_check_reward(self, ctx: CustomContext, number: int):
        """[TODO] Checks a number to see if it is assigned to a reward"""
        number += 1
        await ctx.send('WIP - coming soon!')

    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(manage_messages=True)
    @counting.command(name='override-number')
    async def ct_override_number(self, ctx: CustomContext, number: int):
        """Sets this server's current count number in case it breaks somehow"""
        if ctx.guild.id in self.bot.counting_channels:
            if number < 0:
                raise commands.BadArgument('⚠ **|** **Number** must be greater or equal to **0**')
            confirm = await ctx.confirm(
                f'⚠ **|** Are you sure you **set** the **counting number** to **{number}**?', return_message=True
            )
            if confirm[0] is True:
                self.bot.counting_channels[ctx.guild.id]['number'] = number
                await self.bot.db.execute(
                    'UPDATE count_settings SET current_number = $2 WHERE guild_id = $1', ctx.guild.id, number
                )
                await confirm[1].edit(
                    content=f'✅ **|** Updated the **counting number** to **{number}**. '
                    f'\nℹ **|** The next number will be **{number + 1}**',
                    view=None,
                )
        else:
            await ctx.send('⚠ **|** This server doesn\'t have a **counting channel**!')
