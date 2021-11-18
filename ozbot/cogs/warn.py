import asyncio

import discord
from discord.ext import commands

from ozbot import constants


class Events(commands.Cog):
    """events only, not much."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if not before.bot:
            return

        # skyblock
        if before.status is discord.Status.online and after.status is discord.Status.offline and before.id == 755309062555435070:
            print("Skyblock went offline")
            await asyncio.sleep(120)
            print("checking...")
            user = self.bot.get_guild(706624339595886683).get_member(755309062555435070)
            if user.status == discord.Status.online:
                return
            else:
                await self.bot.get_channel(799741426886901850).send(
                    "Skyblock has been offline for 2 minutes, y'all might want to check on that!")
                await self.bot.get_channel(755309358967029801).send(
                    "It seems like the server went down! I've notified the staff about it. They'll fix it soon")
                print("Skyblock is still offline")

        # creative
        if before.status is discord.Status.online and after.status is discord.Status.offline and before.id == 764623648132300811:
            print("Creative went offline")
            await asyncio.sleep(120)
            print("checking...")
            user = self.bot.get_guild(706624339595886683).get_member(764623648132300811)
            if user.status == discord.Status.online:
                return
            else:
                await self.bot.get_channel(799741426886901850).send(
                    "Creative has been offline for 2 minutes, y'all might want to check on that!")
                await self.bot.get_channel(764624072994062367).send(
                    "It seems like the server went down! I've notified the staff about it. They'll fix it soon")
                print("Creative is still offline")

        # lobby
        if before.status is discord.Status.online and after.status is discord.Status.offline and before.id == 755311461332418610:
            print("Lobby went offline")
            await asyncio.sleep(120)
            print("checking...")
            user = self.bot.get_guild(706624339595886683).get_member(755311461332418610)
            if user.status == discord.Status.online:
                return
            else:
                await self.bot.get_channel(799741426886901850).send(
                    "Lobby has been offline for 2 minutes, y'all might want to check on that!")
                await self.bot.get_channel(755311693042548806).send(
                    "It seems like the server went down! I've notified the staff about it. They'll fix it soon")
                print("Lobby is still offline")

                ##survival
        if before.status is discord.Status.online and after.status is discord.Status.offline and before.id == 799749818062077962:
            print("survival went offline")
            await asyncio.sleep(120)
            print("checking...")
            user = self.bot.get_guild(706624339595886683).get_member(799749818062077962)
            if user.status == discord.Status.online:
                return
            else:
                await self.bot.get_channel(799741426886901850).send(
                    "Survival has been offline for 2 minutes, y'all might want to check on that!")
                await self.bot.get_channel(799483071069945866).send(
                    "It seems like the server went down! I've notified the staff about it. They'll fix it soon")
                print("Survival is still offline")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot: return
        textchannel = self.bot.get_channel(851314198654484521)

        chids = [706624340170375471, 722999864719573083, 722999922869141534, 723000127404638249]
        staffchat = self.bot.get_channel(805819362467512377)

        if after.channel is not None:
            if after.channel.id in chids:
                if before.channel is not None:
                    if before.channel.id in chids: return
                await textchannel.send("""
!c tellraw @a ["",{"text":"[","bold":true,"color":"blue"},{"text":"discord","color":"aqua"},{"text":"] ","bold":true,"color":"blue"},{"text":"%s","color":"gold"},{"text":" joined VC","color":"yellow"}]
""" % member.display_name)
                channel = self.bot.get_channel(799483071069945866)
                hooks = await channel.webhooks()
                hook = hooks[0]
                await hook.send(username="VC bot",
                                content=f"{constants.JOINED_SERVER} **{member.display_name}** joined VC",
                                avatar_url="https://cdn.discordapp.com/emojis/860330111377866774.png?v=1")
            elif after.channel == staffchat and before.channel != staffchat:
                await textchannel.send(f"!c helpop {member.display_name} joined Staff-VC")

        if before.channel is not None:
            if before.channel.id in chids:
                if after.channel is not None:
                    if after.channel.id in chids: return
                await textchannel.send("""
!c tellraw @a ["",{"text":"[","bold":true,"color":"blue"},{"text":"discord","color":"aqua"},{"text":"] ","bold":true,"color":"blue"},{"text":"%s","color":"gold"},{"text":" left VC","color":"yellow"}]
""" % member.display_name)
                channel = self.bot.get_channel(799483071069945866)
                hooks = await channel.webhooks()
                hook = hooks[0]
                await hook.send(username="VC bot",
                                content=f"{constants.LEFT_SERVER} **{member.display_name}** left VC",
                                avatar_url="https://cdn.discordapp.com/emojis/860330111377866774.png?v=1")
            elif before.channel == staffchat and after.channel != staffchat:
                await textchannel.send(f"!c helpop {member.display_name} left Staff-VC")


def setup(bot):
    bot.add_cog(Events(bot))
