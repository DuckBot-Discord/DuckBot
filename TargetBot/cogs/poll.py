import json, random, typing, discord, asyncio, yaml
from discord.ext import commands

class info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.channel_id != 756677534627659826: return
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        print('event add triggered')
        if message.content.lower().endswith('closed!'):
            member = self.bot.get_guild(payload.guild_id).get_member(payload.user_id)
            await message.remove_reaction(payload.emoji, member)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.channel_id != 756677534627659826: return
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        print('event rem triggered')
        if message.content.lower().endswith('closed!'):
            member = self.bot.get_guild(payload.guild_id).get_member(payload.user_id)
            await member.send(f"""⚠ You cannot interact with this poll (if you already voted, your vote has been counted)""")
            await self.bot.get_channel(776996038808436767).send(f'some dumb fuck ({member}) tried to interact with a closed poll <a:facepalmslap:857426899017007154>')

    @commands.command(aliases = ['count'])
    @commands.is_owner()
    async def countvotes(self, ctx):
        message = await self.bot.get_channel(756677534627659826).fetch_message(857051549346824202)
        r1 = []
        async for user in message.reactions[0].users():
            r1.append(user.name)
        r1e = message.reactions[0].emoji
        r2 = []
        async for user in message.reactions[1].users():
            r2.append(user.name)
        r2e = message.reactions[1].emoji

        rtb = []
        rts = []
        rti = []

        if len(r1) >= len(r2):
            rcb = r1
            rcbe = r1e
            rcs = r2
            reb = r2e
        else:
            rcb = r2
            reb = r2e
            rcs = r1
            res = r1e

        for user in rcb:
            if not user in rcs:
                rtb.append(user)
            elif user in rcs:
                rti.append(user)

        for user in rcs:
            if not user in rcb:
                rts.append(user)

        embed = discord.Embed(description = f"""
**people who voted for {res} :** {len(rts)}
**people who voted for {reb} :** {len(rtb)}
**invalid (voted both) :** {len(rti)}
""", color = ctx.me.color)
        await ctx.send(embed = embed)
        return


def setup(bot):
    bot.add_cog(info(bot))
