import discord, asyncio, typing, aiohttp, random, json, yaml
from discord.ext import commands

class help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def sendembed(self, ctx, *, data):
        try:
            dictionary = json.loads(data)
        except:
            await ctx.send("json data malformed")
            return
        embed = discord.Embed().from_dict(dictionary)
        try:
            await ctx.send(embed=embed)
        except:
            await ctx.send("json data malformed")
            return
        await ctx.message.delete()

    @commands.command()
    async def addemb(self, ctx, *, data):
        if ctx.message.reference:
            msg = ctx.message.reference.resolved
            try:
                dictionary = json.loads(data)
            except:
                await ctx.send("json data malformed", delete_after=3)
                return
            embed = discord.Embed().from_dict(dictionary)
            try:
                await msg.edit(content = msg.content, embed=embed)
            except:
                await ctx.send("json data malformed", delete_after=3)
                return
            await ctx.message.delete()
        else:
            await ctx.message.add_reaction('⚠')
            await asyncio.sleep(3)
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                return

    @commands.command()
    async def test(self, ctx): # waiting for message here
        await ctx.send(f"**{ctx.author}**, send anything in 60 seconds!")

        def check(m: discord.Message):  # m = discord.Message.
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
            # checking author and channel, you could add a line to check the content.
            # and m.content == "xxx"
            # he check won't become True until it detects (in the example case): xxx
            # but that's not what we want here.

        try:
            #                        event = on_message without on_
            msg = await self.bot.wait_for(event = 'message', check = check, timeout = 30.0)
            # msg = discord.Message
        except asyncio.TimeoutError:
            # at this point, the check didn't become True, let's handle it.
            await ctx.send(f"**{ctx.author}**, you didn't send any message that meets the check in this channel for 60 seconds..")
            return
        else:
            # at this point, the check has become True and the wait_for has done its work, now we can do ours.
            # we could also do things based on the message content here , ike so
            # if msg.content == "this is cool":
            #    return await ctx.send("wait_for is indeed a cool method")

            await ctx.send(f"**{ctx.author}**, you responded with {msg.content}!")
            return

    # invoke: [p]messagecheck


def setup(bot):
    bot.add_cog(help(bot))
