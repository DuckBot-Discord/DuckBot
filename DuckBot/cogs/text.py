import typing, discord, asyncio, random, datetime, json, aiohttp, re
from discord.ext import commands, tasks, timers
from random import randint


class general(commands.Cog):
    """your general every-day commands"""
    def __init__(self, bot):
        self.bot = bot

    ##### .s <text> #####
    # resends the message as the bot

    @commands.command(aliases=['s', 'send'], usage="<text>", help="Speak as if you were me. # URLs/Invites not allowed!")
    async def say(self, ctx, *, msg: typing.Optional[str]):
        if msg==None:
            await ctx.send(f"Error! empty. do: `{ctx.prefix}{ctx.command} <text>`")

        results = re.findall("http[s]?:\/\/(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", msg) # HTTP/HTTPS URL regex
        results2 = re.findall("(?:https?:\/\/)?discord(?:app)?\.(?:com\/invite|gg)\/[a-zA-Z0-9]+\/?", msg) # Discord invite regex
        if results or results2:
            await ctx.send(f"`{ctx.prefix}{ctx.command}` can't be used to send invites or URLs, as it could bypass spam filters!", delete_after=5)
            try: await ctx.message.delete(delay=5)
            except: return
            return

        try:
            await ctx.message.delete()
        except:
            pass
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

    ##### .a <TextChannel> <text> ######
    #sends the message in a channel

    @commands.command(help="Echoes a message to another channel",aliases=['a', 'an', 'announce'], usage="<channel> <message>")
    @commands.check_any(commands.has_permissions(manage_messages=True), commands.is_owner())
    async def echo(self, ctx, channel: typing.Optional[discord.TextChannel] = None, *, msg: typing.Optional[str]):
        if channel == None:
            await ctx.send(f"""You must specify a channel
`{ctx.prefix}{ctx.command}{ctx.usage} [#channel] [message]`""")
            return
        if msg == None:
            await ctx.send(f"""You must type a message.
`{ctx.prefix}{ctx.command} [#channel] [message]`""")
            return
        if channel.permissions_for(ctx.author).mention_everyone:
            if ctx.message.reference:
                msg = ctx.message.reference.resolved.content
            await channel.send(msg)

        else:
            if ctx.message.reference:
                msg = ctx.message.reference.resolved.content
            await channel.send(msg, allowed_mentions = discord.AllowedMentions(everyone = False))

    @commands.command(  aliases=['e'],
                        usage="-reply- [new message] [--d|--s]",
                        help="Quote a bot message to edit it. # Append --s at the end to supress embeds and --d to delete the message")
    @commands.check_any(commands.has_permissions(manage_messages=True), commands.is_owner())
    async def edit(self, ctx, *, new_message : typing.Optional[str] = '--d'):
        new = new_message
        if ctx.message.reference:
            msg = ctx.message.reference.resolved
            try:
                if new.endswith("--s"): await msg.edit(content=f"{new[:-3]}", suppress=True)
                elif new.endswith('--d'): await msg.delete()
                else: await msg.edit(content=new, suppress=False)
                try: await ctx.message.delete()
                except discord.Forbidden:
                    return
            except: pass
        else:
            await ctx.message.add_reaction('⚠')
            await asyncio.sleep(3)
            try: await ctx.message.delete()
            except discord.Forbidden: return

    #### .jumbo <Emoji> ####
    # makes emoji go big

    @commands.command(  aliases=['jumbo', 'bigemoji', 'emojinfo'],
                        help="Makes an emoji bigger and shows it's formatting", usage="<emoji>")
    async def emoji(self, ctx, emoji: typing.Optional[discord.PartialEmoji]):
        if emoji == None: await ctx.send(embed = discord.Embed(description="Please specify a valid Custom Emoji", color=ctx.me.color))
        else:
            if emoji.animated: emojiformat = f"*`<`*`a:{emoji.name}:{emoji.id}>`"
            else: emojiformat = f"*`<`*`:{emoji.name}:{emoji.id}>`"
            embed = discord.Embed(description=f"{emojiformat}",color=ctx.me.color)
            embed.set_image(url = emoji.url)
            await ctx.send(embed=embed)

    #### .uuid <mcname> ####
    # gets user's UUID (minecraft)

    @commands.command(  help="Fetches the UUID of a minecraft user",
                        usage="<Minecraft username>")
    async def uuid(self, ctx, *, argument: typing.Optional[str] = None):
        if argument == None:
            embed = discord.Embed(description= "please specify a Minecraft Username to look up", color = ctx.me.color)
            await ctx.send(embed=embed)
            return
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
    bot.add_cog(general(bot))
