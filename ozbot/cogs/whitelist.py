import contextlib
import logging

import asyncpg
import discord
from discord.ext import commands

from ozbot.__main__ import Ozbot


class Whitelist(commands.Cog):
    """📜 whitelisting and accepting the rules."""

    def __init__(self, bot):
        self.bot: Ozbot = bot
        self.denied_keywords = ['agree', 'i agree', 'yes', 'ok', 'agreed']

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.channel.id != 706825075516768297:
            return
        if message.channel.permissions_for(message.author).manage_messages:
            return await message.delete(delay=15)
        if message.content.lower() in self.denied_keywords:
            await message.delete(delay=0.2)
            return await message.channel.send("That's not how this works. 😖\nPlease read the rules again 😅",
                                              delete_after=10)
        await message.delete(delay=0.2)
        user = message.guild.get_member(799749818062077962)
        argument = message.content
        if argument is None:
            return await message.delete(delay=0)

        if await self.bot.db.fetchval('select user_id from whitelist where user_id = $1', message.author.id):
            await message.channel.send("You're already in the whitelist database. If this is a mistake, contact an admin.", delete_after=10)
            return await self.bot.get_channel(799741426886901850).send(f"{message.author.mention} tried to add themselves to the whitelist, but they're already in the database.")

        if message.guild.get_role(833843541872214056) in message.author.roles:
            return await message.channel.send("⚠ Sorry but you can't do that! you're already whitelisted.", delete_after=5)

        async with self.bot.session.get(f"https://api.mojang.com/users/profiles/minecraft/{argument}") as r:
            if r.status in (204, 400):
                await message.channel.send(f"❌ Sorry {message.author.mention} but **`{argument[0:100]}`** is not a valid **__Minecraft Java Edition__** username.", delete_after=20)

            elif r.status != 200:
                return await message.channel.send(f"❌ **Could not verify username!**\nMinecraft API failed with {r.status}! \n<@349373972103561218> fix this!")

            elif user.status == discord.Status.online:
                res = await r.json()
                user = res["name"]
                uuid = res["id"]

                try:
                    await self.bot.db.execute('insert into usernames (user_id, minecraft_id values ($1, $2)', message.author.id, uuid)
                except asyncpg.UniqueViolationError:
                    uuid = await self.bot.db.fetchval('select minecraft_id from usernames where user_id = $1', message.author.id)
                    if uuid:
                        await message.channel.send(f"Your minecraft name is already in the whitelist database. You will receive the roles."
                                                   f"\nIf you cannot log on, warn an admin.", delete_after=10)
                    else:
                        await message.channel.send(f"Your discord user is already in the whitelist database. You will receive the roles."
                                                   f"\nIf you cannot log on, warn an admin.", delete_after=10)

                    await message.author.add_roles(message.guild.get_role(833843541872214056),
                                                   message.guild.get_role(798698824738668605))
                    try:
                        await message.author.remove_roles(message.guild.get_role(851593341409820722))
                    except Exception as e:
                        logging.error(f'Could not remove role from {message.author}!', exc_info=e)
                    return

                channel = self.bot.get_channel(764631105097170974)
                await channel.send(f'whitelist add {user}')
                channel = self.bot.get_channel(799741426886901850)

                embed2 = discord.Embed(description=f"Automatically added user `{user}` to the whitelist",
                                       color=0x75AF54)
                embed2.set_footer(text=f'{uuid}\nrequested by: {message.author} | {message.author.id}')
                with contextlib.suppress(discord.HTTPException):
                    await channel.send(embed=embed2)
                embed = discord.Embed(color=0x75AF54)
                embed.add_field(name=f'✅ YOU HAVE ACCEPTED THE RULES AND YOU HAVE BEEN WHITELISTED',
                                value=f"Your username `{user}` has been automatically whitelisted. Welcome to OZ!")

                await message.author.add_roles(message.guild.get_role(833843541872214056),
                                               message.guild.get_role(798698824738668605))
                try:
                    await message.author.remove_roles(message.guild.get_role(851593341409820722))
                except Exception as e:
                    logging.error(f'Could not remove role from {message.author}!', exc_info=e)

            else:
                embed = discord.Embed(color=0x75AF54)
                embed.add_field(name=f'❌ Server is offline, try again in a few minutes',
                                value=f"Sorry but the server is offline. Wait a few minutes then try again.")

            await message.channel.send(embed=embed, delete_after=15)


def setup(bot):
    bot.add_cog(Whitelist(bot))
