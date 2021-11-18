import aiohttp
import asyncio
import discord
from discord.ext import commands


class whitelist(commands.Cog):
    """📜 whitelisting and accepting the rules."""
    def __init__(self, bot):
        self.bot = bot
        self.denied_keywords = ['agree', 'i agree', 'yes', 'ok', 'agreed']

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.channel.id != 706825075516768297: return
        if message.channel.permissions_for(message.author).manage_messages:
            await asyncio.sleep(15)
            await message.delete()
            return
        if message.content.lower() in self.denied_keywords:
            await message.delete(delay=0.2)
            await message.channel.send("That's not how you do it 😖\nPlease read the rules again 😅", delete_after=10)
            return
        await message.delete(delay=0.2)
        user = message.guild.get_member(799749818062077962)
        argument = message.content
        if argument == None:
            await message.delete()
            return
        if message.guild.get_role(833843541872214056) in message.author.roles:
            await message.channel.send("⚠ Sorry but you can't do that! you're already whitelisted.", delete_after=5)
            return
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f"https://api.mojang.com/users/profiles/minecraft/{argument}") as cs:
                if cs.status == 204:
                    embed = discord.Embed(color = 0xFF2014)
                    embed.add_field(name='Could not whitelist user. Please try again', value=f"`{argument}` is not a valid Minecraft username!")

                    embed2=discord.Embed(title="Whoops! You seem to have sent an invalid username in the rules channel.", description=f"""Our system noticed that the username you specified (`{argument}`) is not an existing minecraft JAVA account.
> Make sure to ONLY type your username, and not any extra characters like emojis, periods, exc.
> Type the username AS IT IS. __doesn't matter if it becomes italics, bold, or any other formatting.__
If you still have trouble,
Here's some extra information about Minecraft usernames, accounts and how to find your account's username 😊:""", color=0xeb3636)
                    embed2.set_thumbnail(url="https://i.imgur.com/GTttbJW.png")
                    embed2.add_field(name="First off, make sure you have the correct version of Minecraft", value="Make sure you have Minecraft's [JAVA edition](https://www.minecraft.net/store/minecraft-java-edition) version of the game", inline=False)
                    embed2.add_field(name="After confirming that, make sure you have premium/paid Minecraft account.", value="Here is an [article on Minecraft's forum](https://help.minecraft.net/hc/en-us/articles/360034636712-Minecraft-Usernames) that goes into details on Minecraft usernames and how to find yours. You will not be able to accept the rules if you do not own a legit version of Minecraft.", inline=False)
                    embed2.add_field(name="After all of this, try again!", value="Head to the <#706825075516768297> channel and type in your newly found Minecraft username", inline=False)
                    embed2.set_footer(text="This is an automated action, if you are still having trouble whitelisting yourself, contact staff by replying to this Direct Message. An available staff member will respond to you as soon as possible.")
                    try: await message.author.send(embed=embed2)
                    except: pass
                    await message.channel.send(f"❌ `{argument}` doesn't seem to be a JAVA EDITION account. Just sent you a DM some info on how to find it :smile:", delete_after=20)

                elif cs.status == 400:
                    embed = discord.Embed(color = 0xFF2014)
                    embed.add_field(name='Could not whitelist user. Please try again', value=f"`{argument}` is not a valid Minecraft username!")

                    embed2=discord.Embed(title="Whoops! You seem to have sent an invalid username in the rules channel.", description=f"""Our system noticed that the username you specified (`{argument}`) is not an existing minecraft JAVA account.
> Make sure to ONLY type your username, and not any extra characters like emojis, periods, exc.
> Type the username AS IT IS. __doesn't matter if it becomes italics, bold, or any other formatting.__
If you still have trouble,
Here's some extra information about Minecraft usernames, accounts and how to find your account's username 😊:""", color=0xeb3636)
                    embed2.set_thumbnail(url="https://i.imgur.com/GTttbJW.png")
                    embed2.add_field(name="First off, make sure you have the correct version of Minecraft", value="Make sure you have Minecraft's [JAVA edition](https://www.minecraft.net/store/minecraft-java-edition) version of the game", inline=False)
                    embed2.add_field(name="After confirming that, make sure you have premium/paid Minecraft account.", value="Here is an [article on Minecraft's forum](https://help.minecraft.net/hc/en-us/articles/360034636712-Minecraft-Usernames) that goes into details on Minecraft usernames and how to find yours. You will not be able to accept the rules if you do not own a legit version of Minecraft.", inline=False)
                    embed2.add_field(name="After all of this, try again!", value="Head to the <#706825075516768297> channel and type in your newly found Minecraft username", inline=False)
                    embed2.set_footer(text="This is an automated action, if you are still having trouble whitelisting yourself, contact staff by replying to this Direct Message. An available staff member will respond to you as soon as possible.")
                    try: await message.author.send(embed=embed2)
                    except: pass
                    await message.channel.send(f"❌ `{argument}` doesn't seem to be a JAVA EDITION account. Just sent you a DM some info on how to find it :smile:", delete_after=20)

                elif cs.status != 200: return await message.channel.send(f"{cs.status} - something went wrong...")

                elif user.status == discord.Status.online:
                    await message.author.add_roles(message.guild.get_role(833843541872214056),message.guild.get_role(798698824738668605))
                    try: await message.author.remove_roles(message.guild.get_role(851593341409820722))
                    except: pass
                    res = await cs.json()
                    user = res["name"]
                    uuid = res["id"]
                    channel = self.bot.get_channel(764631105097170974)
                    await channel.send(f'whitelist add {user}')
                    channel = self.bot.get_channel(799741426886901850)
                    embed2 = discord.Embed(title='', description=f"Automatically added user `{user}` to the whitelist", color = 0x75AF54)
                    embed2.set_footer(text=f'''{uuid}
requested by: {message.author.name}#{message.author.discriminator} | {message.author.id}''')
                    await channel.send(embed=embed2)
                    embed = discord.Embed(color = 0x75AF54)
                    embed.add_field(name=f'✅ YOU HAVE ACCEPTED THE RULES AND YOU HAVE BEEN WHITELISTED', value=f"Your username `{user}` has been automatically whitelisted. Welcome to OZ!")

                    userembed=discord.Embed(title=f"Welcome to the OZ SMP community!", description=f"""You have been whitelisted on our servers, and are free to join. All the information needed to join, like IP adress, can be found in the information channel in our discord server.
Our systems have automatically added the username that you sent to the rules channel (`{user}`) to our whitelist.
_ _
```Please note that if that is NOT your minecraft username but it got accepted, that means that that you may have made a typo and that username belongs to someone else. if that's the case, Reply to this message and a staff member will respond to you trough this Direct message thread```""", color=0x75AF54)
                    userembed.set_footer(text="Having issues? Reply to this Direct Message to get in contact with our staff team!")
                    try: await message.author.send(embed=userembed)
                    except: pass

                else:
                    embed = discord.Embed(color = 0x75AF54)
                    embed.add_field(name=f'''❌ Server is offline, try again in a few minutes''', value=f"Sorry but the server is offline. Wait a few minutes then try again.")
                await message.channel.send(embed=embed, delete_after=15)

def setup(bot):
    bot.add_cog(whitelist(bot))
