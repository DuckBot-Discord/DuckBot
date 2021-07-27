import discord, asyncio, typing, aiohttp, random, json, yaml, re
from discord.ext import commands, menus

class tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @commands.max_concurrency(1, per=commands.BucketType.user, wait=False)
    async def test(self, ctx):

        embed=discord.Embed(color = 0x47B781, description="1️⃣ **STEP ONE: Title**")
        embed.add_field(name="What do you want your embed title to be?", value="send `skip` to skip.")
        embed.set_footer(text="all prompts expire in 5 minutes! Send \"cancel\" to cancel")
        message = await ctx.send(ctx.author.mention, embed=embed)

        announcement_embed = discord.Embed(title="Announcement visualization")
        announcement = await ctx.send(embed=announcement_embed)

        # Message check
        def check(m: discord.Message):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

        try:
            msg = await self.bot.wait_for(event = 'message', check = check, timeout = 600.0)
        except asyncio.TimeoutError:
            err=discord.Embed(color=0xD7342A, description=f"**Sorry, you didn't respond in time**")
            await message.edit(content=ctx.author.mention, embed=err)
            return
        else:
            if msg.content == "skip":
                    try: await msg.delete()
                    except: pass
                    announcement_embed.title=None
            elif msg.content == "cancel":
                await message.edit(embed=discord.Embed(color=0xD7342A, title="Cancelled"))
                return
            else:
                try: await msg.delete()
                except: pass
                announcement_embed.title=msg.content
                EmTitle = msg.content
                await announcement.edit(embed=announcement_embed)

        embed.clear_fields()
        embed.description="2️⃣ **STEP TWO: description**"
        embed.add_field(name="What do you want your embed description to be?", value="send `skip` to skip. you can use __**`markdown`**__ here")
        await message.edit(content=ctx.author.mention, embed=embed)

        iter=0
        while iter==0:
            try:
                msg = await self.bot.wait_for(event = 'message', check = check, timeout = 600.0)
            except asyncio.TimeoutError:
                err=discord.Embed(color=0xD7342A, description=f"**Sorry, you didn't respond in time**")
                await message.edit(content=ctx.author.mention, embed=err)
                return
            else:
                if msg.content == "skip":
                        if announcement_embed.title == None:
                            try: await msg.delete()
                            except: pass
                            await ctx.send("Title already skipped. you can't skip the description.", delete_after=5)
                        else:
                            try: await msg.delete()
                            except: pass
                            announcement_embed.description=None
                            iter=1

                elif msg.content == "cancel":
                    await message.edit(embed=discord.Embed(color=0xD7342A, title="Cancelled"))
                    return
                else:
                    try: await msg.delete()
                    except: pass
                    announcement_embed.description=msg.content
                    await announcement.edit(embed=announcement_embed)
                    iter=1




        embed.clear_fields()
        embed.description="3️⃣ **STEP THREE: Color**"
        embed.add_field(name="What color of embed you want?", value="send `skip` to leave it as default. [COLOR PICKER](https://www.google.com/search?q=Color+picker)")
        await message.edit(content=ctx.author.mention, embed=embed)

        iter = 0
        while iter==0:
            try:
                msg = await self.bot.wait_for(event = 'message', check = check, timeout = 600.0)
            except asyncio.TimeoutError:
                err=discord.Embed(color=0xD7342A, description=f"**Sorry, you didn't respond in time**")
                await message.edit(content=ctx.author.mention, embed=err)
                return
            else:
                if msg.content == "skip":
                        try: await msg.delete()
                        except: pass
                        iter=1
                elif msg.content == "cancel":
                    await message.edit(embed=discord.Embed(color=0xD7342A, title="Cancelled"))
                    return
                elif re.match("^#?(?:[0-9a-fA-F]{3}){1,2}$", msg.content):
                    try: await msg.delete()
                    except: pass
                    color = msg.content.replace("#", "")
                    color = int(color, 16)
                    announcement_embed.color=color
                    await announcement.edit(embed=announcement_embed)
                    iter=1
                else:
                    try: await msg.delete()
                    except: pass
                    await ctx.send("that's not a valid hex code!", delete_after=5)


        embed.clear_fields()
        embed.description="4️⃣ **STEP FOUR: fields**"
        embed.add_field(name="What do you want your fields to be?", value="send `skip` to skip, send `done` to finish adding fields. \n format: `NAME ~ VALUE ~ in-line(yes/no)`\nNAME: max characters = 256 \nVALUE: max characters = 1024", inline=False)
        embed.add_field(name="_ _", value="_ _", inline=False)
        embed.add_field(name="NAME - this is an in-line field", value="VALUE - this is an example value for an in-line field", inline=True)
        embed.add_field(name="NAME - this is an in-line field", value="VALUE - this is an example value for an in-line field", inline=True)
        embed.add_field(name="NAME - this is a not in-line field", value="VALUE - this is an example value for a field in-line that is not in-line, as you can see they are made in a new line.", inline=False)
        embed.add_field(name="_ _", value="_ _", inline=False)
        await message.edit(content=ctx.author.mention, embed=embed)

        iter=0
        while iter==0:
            try:
                msg = await self.bot.wait_for(event = 'message', check = check, timeout = 600.0)
            except asyncio.TimeoutError:
                err=discord.Embed(color=0xD7342A, description=f"**Sorry, you didn't respond in time**")
                await message.edit(content=ctx.author.mention, embed=err)
                return
            else:
                if msg.content == "skip" or msg.content == "done":
                    try: await msg.delete()
                    except: pass
                    iter=1

                elif msg.content == "cancel":
                    await message.edit(embed=discord.Embed(color=0xD7342A, title="Cancelled"))
                    return

                elif re.match("^(((?s).{1,256})~((?s).{1,1024})~(yes|no| yes| no))$", msg.content.replace("\n", " ")):
                    try: await msg.delete()
                    except: pass
                    if msg.content.split("~")[2].replace(" ", "") == "yes":
                        inl = True
                    else: inl = False
                    announcement_embed.add_field(name=msg.content.split("~")[0], value=msg.content.split("~")[1], inline=inl)
                    await announcement.edit(embed=announcement_embed)
                    if len(announcement_embed.fields) >= 25:
                        await ctx.send("max amount of fields reached!", delete_after=5)
                        iter=1
                else:
                    try: await msg.delete(delay=20)
                    except: pass
                    embed.description="4️⃣ **STEP FOUR: fields** \n\nsomething went wrong! remember to add the `~` to separate the values. \nformat: `NAME ~ VALUE ~ in-line(yes/no)`\nYou must format your field like: ```\nName (max: 1024 characters) ~ Value (max: 1024 characters) ~ inline(yes/no)``` \n**example:**```\nI'm a name ~ I'm  a value ~ yes```"
                    embed.clear_fields()
                    await message.edit(content=ctx.author.mention, embed=embed)


        embed.clear_fields()
        embed.description="5️⃣ **STEP FIVE: footer**"
        embed.add_field(name="What color of embed you want?", value="send `skip` to leave it as default. [COLOR PICKER](https://www.google.com/search?q=Color+picker)")
        await message.edit(content=ctx.author.mention, embed=embed)

        iter = 0
        while iter==0:
            try:
                msg = await self.bot.wait_for(event = 'message', check = check, timeout = 600.0)
            except asyncio.TimeoutError:
                err=discord.Embed(color=0xD7342A, description=f"**Sorry, you didn't respond in time**")
                await message.edit(content=ctx.author.mention, embed=err)
                return
            else:
                if msg.content == "skip":
                        try: await msg.delete()
                        except: pass
                        iter=1
                elif msg.content == "cancel":
                    await message.edit(embed=discord.Embed(color=0xD7342A, title="Cancelled"))
                    return
                elif re.match("^#?(?:[0-9a-fA-F]{3}){1,2}$", msg.content):
                    try: await msg.delete()
                    except: pass
                    color = msg.content.replace("#", "")
                    color = int(color, 16)
                    announcement_embed.color=color
                    await announcement.edit(embed=announcement_embed)
                    iter=1
                else:
                    try: await msg.delete()
                    except: pass
                    await ctx.send("that's not a valid hex code!", delete_after=5)




def setup(bot):
    bot.add_cog(tickets(bot))
