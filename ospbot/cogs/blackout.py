import logging

import asyncpg
import discord.abc
import yaml
from discord.ext import commands, tasks


async def get_webhook(channel):
    hookslist = await channel.webhooks()
    if hookslist:
        for hook in hookslist:
            if hook.token:
                return hook
            else:
                continue
    hook = await channel.create_webhook(name="OSP-Bot ticket logging")
    return hook


class BlackoutMode(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        # ------------- YAML STUFF -------------#
        with open(r'files/config.yaml') as file:
            full_yaml = yaml.full_load(file)

        self.main_guild_id = full_yaml['guildID']
        self.verified_role = full_yaml['RulesVerRole']
        self.unverified_role = full_yaml['RulesUnvRole']
        self.ticket_staff_role = full_yaml['TicketStaffRole']
        self.blackout_role_id = full_yaml['BlackoutRole']
        self.ticket_log_channel = full_yaml['TicketLogChannel']
        self.blackout_channel_id = full_yaml['blackout_channel']

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        if channel.guild.id != self.main_guild_id: return
        await channel.set_permissions(channel.guild.get_role(self.blackout_role_id), view_channel=False,
                                      reason=f'automatic Blackout mode')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        owner = self.bot.get_user(349373972103561218) or await self.bot.fetch_user(349373972103561218)
        try:
            if getattr(payload.member, 'bot', True):
                return
            if payload.channel_id != self.blackout_channel_id:
                return
            if str(payload.emoji) != '⏹':
                return

            await owner.send(f'{payload.member.mention} reacted to {payload.emoji} in {payload.channel_id}')

            message = self.bot.get_channel(payload.channel_id).get_partial_message(payload.message_id)

            try:
                await message.remove_reaction(payload.emoji, payload.member)
            except Exception as e:
                logging.error('could not remove reaction: ' + str(e))
                await owner.send(f'could not remove reaction: {e}')

            db: asyncpg.Pool = self.bot.db
            if payload.member._roles.has(self.blackout_role_id):
                roles = await db.fetchval('DELETE FROM blackouts WHERE user_id = $1 RETURNING roles', payload.member.id)
                guild = self.bot.get_guild(self.main_guild_id)
                to_add = []
                for role_id in roles:
                    role = guild.get_role(role_id)
                    if role:
                        to_add.append(role)
                await payload.member.add_roles(*to_add, reason='Blackout mode ended')
                role = guild.get_role(self.blackout_role_id)
                if not role:
                    return
                await payload.member.remove_roles(role, reason='Blackout mode ended')

            else:
                to_remove = [r for r in payload.member.roles if r.is_assignable()]
                role = self.bot.get_guild(self.main_guild_id).get_role(self.blackout_role_id)
                if not role:
                    return await owner.send(f'Could not find Blackout role in {self.main_guild_id}')
                await db.execute('INSERT INTO blackouts (user_id, roles) VALUES ($1, $2) '
                                 'ON CONFLICT (user_id) DO UPDATE SET roles = $2', payload.member.id, [r.id for r in to_remove])
                try:
                    await payload.member.remove_roles(*to_remove, reason='Blackout mode')
                except Exception as e:
                    logging.error('could not remove roles: ' + str(e))
                    await owner.send(f'could not remove roles: {e}')
                try:
                    await payload.member.add_roles(role, reason='Blackout mode')
                except Exception as e:
                    logging.error('could not add role: ' + str(e))
                    await owner.send(f'could not add role: {e}')
        except Exception as e:
            logging.error('could not handle reaction: ' + str(e))
            await owner.send(f'could not handle reaction: {e}')

def setup(bot):
    bot.add_cog(BlackoutMode(bot))
