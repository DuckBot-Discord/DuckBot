import discord, asyncio, typing, aiohttp, random, json, yaml
from discord.ext import commands

class help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    def __init__(self, bot):
        self.bot = bot
    words = ['nothing', 'nothing']
    with open(r'files/banned-words.yaml') as file:
        words = yaml.full_load(file)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        banned_words = self.words['pogwords']
        if any(ele in message.content.lower() for ele in banned_words):
            await message.add_reaction('<:nopog:838102336944603186>')
            await message.add_reaction('😡')

    ##### .s command ####
    # resends the message as the bot

    @commands.command(aliases=['s', 'send', 'foo'])
    @commands.has_permissions(manage_messages=True)
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

    @commands.command(aliases = ['source', 'code'])
    async def sourcecode(self, ctx):
        embed=discord.Embed(title="", description="**[Here's my source code](https://github.com/LeoCx1000/discord-bots)**", color=ctx.me.color)
        await ctx.send(embed=embed)

    @commands.command()
    async def ping(self, ctx):
        embed = discord.Embed(title='', description="🏓 pong!", color=ctx.me.color)
        start = time.perf_counter()
        message = await ctx.send(embed=embed)
        end = time.perf_counter()
        await asyncio.sleep(0.7)
        duration = (end - start) * 1000
        embed = discord.Embed(title='', description=f'**websocket:** `{(self.bot.latency * 1000):.2f}ms` \n**message:** `{duration:.2f}ms`', color=ctx.me.color)
        await message.edit(embed=embed)

    @commands.command()
    async def uuid(self, ctx, *, argument: typing.Optional[str] = ''):
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f"https://api.mojang.com/users/profiles/minecraft/{argument}") as cs:
                embed = discord.Embed(color = ctx.me.color)
                if cs.status == 204:
                    embed.add_field(name='⚠ ERROR ⚠', value=f"`{argument}` is not a minecraft username!")

                elif cs.status == 400:
                    embed.add_field(name="⛔ ERROR ⛔", value="ERROR 400! Bad request.")
                else:
                    res = await cs.json()
                    user = res["name"]
                    uuid = res["id"]
                    embed.add_field(name=f'Minecraft username: `{user}`', value=f"**UUID:** `{uuid}`")

                await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(help(bot))
