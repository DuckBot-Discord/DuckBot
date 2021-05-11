import json, random, discord, aiohttp, typing, asyncio
from random import randint
from discord.ext import commands


class help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.channel.id != 706825075516768297:
            return
        await asyncio.sleep(0.1)
        await message.delete()
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

                    embed2=discord.Embed(title="Whoops! You seem to have sent an invalid username in the rules channel.", description="Our system noticed that you did not type your Minecraft username correctly in the rules channel. Here's some extra information about Minecraft usernames, accounts and how to find your account's username.", color=0xeb3636)
                    embed2.set_thumbnail(url="https://i.imgur.com/GTttbJW.png")
                    embed2.add_field(name="First off, make sure you have the correct version of Minecraft", value="Make sure you have Minecraft's [JAVA edition](https://www.minecraft.net/store/minecraft-java-edition) version of the game, and **__NOT__** Minecraft BEDROCK edition, which includes: [windows 10 edition](https://www.minecraft.net/store/minecraft-windows10), [android](https://www.minecraft.net/es-es/store/minecraft-android), [iOS/iPadOS](https://www.minecraft.net/store/minecraft-ios), Xbox [one](https://www.minecraft.net/store/minecraft-xbox-one)/[360](https://www.minecraft.net/store/minecraft-xbox-360), Play Station [4](https://www.minecraft.net/store/minecraft-ps4)/[3](https://www.minecraft.net/store/minecraft-ps3)/[vita](https://www.minecraft.net/store/minecraft-ps-vita), Nintendo [switch](https://www.minecraft.net/store/minecraft-switch)/[Wii U](https://www.minecraft.net/store/minecraft-wii-u)/[3DS](https://www.minecraft.net/store/minecraft-3ds), Amazon [kindle fire](https://www.minecraft.net/store/minecraft-kindle-fire)/[fire TV](https://www.minecraft.net/store/minecraft-fire-tv) and others", inline=False)
                    embed2.add_field(name="After confirming that, make sure you have premium/paid Minecraft account.", value="Here is an [article on Minecraft's forum](https://help.minecraft.net/hc/en-us/articles/360034636712-Minecraft-Usernames) that goes into details on Minecraft usernames and how to find yours. You will not be able to accept the rules if you do not own a legit version of Minecraft.", inline=False)
                    embed2.add_field(name="After all of this, try again!", value="Head to the <#706825075516768297> channel and type in your newly found Minecraft username", inline=False)
                    embed2.set_footer(text="This is an automated action, if you are still having trouble whitelisting yourself, contact staff by replying to this Direct Message. An available staff member will respond to you as soon as possible.")
                    await message.author.send(embed=embed2)

                elif cs.status == 400:
                    embed = discord.Embed(color = 0xFF2014)
                    embed.add_field(name='Could not whitelist user. Please try again', value=f"`{argument}` is not a valid Minecraft username!")

                    embed2=discord.Embed(title="Whoops! You seem to have sent an invalid username in the rules channel.", description="Our system noticed that you did not type your Minecraft username correctly in the rules channel. Here's some extra information about Minecraft usernames, accounts and how to find your account's username.", color=0xeb3636)
                    embed2.set_thumbnail(url="https://i.imgur.com/GTttbJW.png")
                    embed2.add_field(name="First off, make sure you have the correct version of Minecraft", value="Make sure you have Minecraft's [JAVA edition](https://www.minecraft.net/store/minecraft-java-edition) version of the game, and **__NOT__** Minecraft BEDROCK edition, which includes: [windows 10 edition](https://www.minecraft.net/store/minecraft-windows10), [android](https://www.minecraft.net/es-es/store/minecraft-android), [iOS/iPadOS](https://www.minecraft.net/store/minecraft-ios), Xbox [one](https://www.minecraft.net/store/minecraft-xbox-one)/[360](https://www.minecraft.net/store/minecraft-xbox-360), Play Station [4](https://www.minecraft.net/store/minecraft-ps4)/[3](https://www.minecraft.net/store/minecraft-ps3)/[vita](https://www.minecraft.net/store/minecraft-ps-vita), Nintendo [switch](https://www.minecraft.net/store/minecraft-switch)/[Wii U](https://www.minecraft.net/store/minecraft-wii-u)/[3DS](https://www.minecraft.net/store/minecraft-3ds), Amazon [kindle fire](https://www.minecraft.net/store/minecraft-kindle-fire)/[fire TV](https://www.minecraft.net/store/minecraft-fire-tv) and others", inline=False)
                    embed2.add_field(name="After confirming that, make sure you have premium/paid Minecraft account.", value="Here is an [article on Minecraft's forum](https://help.minecraft.net/hc/en-us/articles/360034636712-Minecraft-Usernames) that goes into details on Minecraft usernames and how to find yours. You will not be able to accept the rules if you do not own a legit version of Minecraft.", inline=False)
                    embed2.add_field(name="After all of this, try again!", value="Head to the <#706825075516768297> channel and type in your newly found Minecraft username", inline=False)
                    embed2.set_footer(text="This is an automated action, if you are still having trouble whitelisting yourself, contact staff by replying to this Direct Message. An available staff member will respond to you as soon as possible.")
                    await message.author.send(embed=embed2)

                elif user.status == discord.Status.online:
                    await message.author.add_roles(message.guild.get_role(833843541872214056),message.guild.get_role(798698824738668605))
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


                else:
                    embed = discord.Embed(color = 0x75AF54)
                    embed.add_field(name=f'''❌ Server is offline, try again in a few minutes''', value=f"Sorry but the server is offline. Wait a few minutes then try again.")
                await message.channel.send(embed=embed, delete_after=10)

def setup(bot):
    bot.add_cog(help(bot))
