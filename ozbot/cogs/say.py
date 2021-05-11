import discord, asyncio, typing
from discord.ext import commands

class help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    ##### .s command ####
    # resends the message as the bot

    @commands.command(aliases=['s', 'send', 'foo'])
    async def say(self, ctx, *, msg):
        await ctx.message.delete()
        if ctx.channel.permissions_for(ctx.author).mention_everyone:
            if ctx.message.reference:
                reply = ctx.message.reference.resolved
                await reply.reply(msg)
            else:
                await ctx.send(msg)
        else:
            if ctx.message.reference:
                reply = ctx.message.reference.resolved
                await reply.reply(msg, allowed_mentions = discord.AllowedMentions(everyone = False))
            else:
                await ctx.send(msg, allowed_mentions = discord.AllowedMentions(everyone = False))

    @commands.command(aliases=['a', 'an'])
    @commands.has_permissions(manage_messages=True)
    async def announce(self, ctx, channel: typing.Optional[discord.TextChannel] = None, *, msg = "no content"):
        if channel == None:
            await ctx.send("""You must specify a channel
`.announce #channel/ID Message`""")
            return
        if channel.permissions_for(ctx.author).mention_everyone:
            if ctx.message.reference:
                msg = ctx.message.reference.resolved.content
            await channel.send(msg)

        else:
            if ctx.message.reference:
                msg = ctx.message.reference.resolved.content
            await channel.send(msg, allowed_mentions = discord.AllowedMentions(everyone = False))


    @commands.command(aliases=['e'])
    async def edit(self, ctx, *, new : typing.Optional[str] = '--d'):
            if ctx.author.guild_permissions.manage_messages == False:
                await ctx.message.add_reaction('🚫')
                await asyncio.sleep(3)
                try:
                    await ctx.message.delete()
                except discord.Forbidden:
                    return
                return
            if ctx.message.reference:
                msg = ctx.message.reference.resolved
                try:
                    if new.endswith("--s"): await msg.edit(content="{}".format(new[:-3]), suppress=True)
                    elif new.endswith('--d'): await msg.edit(content=None, suppress=True)
                    else: await msg.edit(content=new, suppress=False)
                    try: await ctx.message.delete()
                    except discord.Forbidden:
                        return
                except discord.Forbidden:
                    await ctx.message.add_reaction('🚫')
                    await asyncio.sleep(3)
                    try:
                        await ctx.message.delete()
                    except discord.Forbidden:
                        return
                    return
            else:
                await ctx.message.add_reaction('⚠')
                await asyncio.sleep(3)
                try:
                    await ctx.message.delete()
                except discord.Forbidden:
                    return

def setup(bot):
    bot.add_cog(help(bot))
