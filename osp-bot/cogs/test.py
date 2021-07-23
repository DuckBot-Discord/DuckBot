import json, random, typing, discord, asyncio, yaml, datetime, random
from discord.ext import commands

class events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        #------------- YAML STUFF -------------#
        with open(r'files/config.yaml') as file:
            full_yaml = yaml.full_load(file)
            mguild = self.bot.get_guild(full_yaml['guildID'])
        self.mguild = mguild
        self.yaml_data = full_yaml
        self.verified = mguild.get_role(full_yaml['RulesVerRole'])
        self.unverified = mguild.get_role(full_yaml['RulesUnvRole'])
        self.STLbefore = None
        self.ticket_staff = mguild.get_role(self.yaml_data['TicketStaffRole'])
        self.blackout = mguild.get_role(self.yaml_data['BlackoutRole'])
        self.ticket_log = self.bot.get_channel(full_yaml['TicketLogChannel'])

        with open(r'files/triggers.yaml') as triggers:
            trigger_words = yaml.full_load(triggers)
        self.trigger_words = trigger_words

    async def get_webhook(self, channel):
        hookslist = await channel.webhooks()
        if hookslist:
            for hook in hookslist:
                if hook.token:
                    return hook
                else: continue
        hook = await channel.create_webhook(name="OSP-Bot ticket logging")
        return hook

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if channel.guild.id != self.mguild.id: return
        await channel.set_permissions(self.blackout, view_channel = False, reason=f'automatic Blackout mode')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member.bot: return
        if payload.channel_id == self.yaml_data['blackout_channel']:
            message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
            try: await message.remove_reaction(payload.emoji, payload.member)
            except: pass

            underaged = self.mguild.get_role(863187863038459924)
            overaged = self.mguild.get_role(863187815340703755)

            if self.verified in payload.member.roles:
                try: await payload.member.add_roles(self.blackout)
                except: pass
                try: await payload.member.remove_roles(self.verified, underaged, overaged)
                except: pass
            elif self.blackout in payload.member.roles:
                try: await payload.member.remove_roles(self.blackout)
                except: pass

                ages = await self.bot.get_channel(860610324020592689).fetch_message(863198786443935744)

                async for user in ages.reactions[0].users():
                    if payload.member.id == user.id:
                        if str(ages.reactions[0].emoji) == "➖":
                            try: await payload.member.add_roles(underaged, self.verified)
                            except: pass
                            return
                        elif str(ages.reactions[0].emoji) == "➕":
                            try: await payload.member.add_roles(overaged, self.verified)
                            except: pass
                            return
                    if payload.member.id == user.id:
                        if str(ages.reactions[1].emoji) == "➖":
                            try: await payload.member.add_roles(underaged, self.verified)
                            except: pass
                            return
                        elif str(ages.reactions[1].emoji) == "➕":
                            try: await payload.member.add_roles(overaged, self.verified)
                            except: pass
                            return

def setup(bot):
    bot.add_cog(events(bot))
