import contextlib
import logging
import typing

import asyncpg
import asyncpg.pgproto.pgproto
import discord
import emoji as unicode_emoji
from discord.ext import commands

from ozbot.__main__ import Ozbot


class UnicodeEmoji:
    @staticmethod
    async def convert(_, argument):
        if argument not in list(unicode_emoji.EMOJI_UNICODE_ENGLISH.values()):
            raise commands.BadArgument(f"failed to convert {argument} into a valid unicode emoji.")
        return argument


class MinecraftName:
    def __init__(self, name: str, uuid: str):
        self.name = name
        self.uuid = uuid

    @classmethod
    async def convert(cls, ctx: commands.Context, argument: str):
        async with ctx.bot.session.get(f"https://api.mojang.com/users/profiles/minecraft/{argument}") as r:
            if r.status in (204, 400, 404):
                raise commands.BadArgument(f'{argument[0:100]} is not a valid minecraft name.')

            elif r.status != 200:
                raise commands.BadArgument(f'{argument[0:100]} is not a valid minecraft name. (Status cde {r.status})')

            res = await r.json()
            user = res["name"]
            uuid = res["id"]

        return cls(name=user, uuid=uuid)


class Whitelist(commands.Cog):
    """📜 whitelisting and accepting the rules."""

    def __init__(self, bot):
        self.bot: Ozbot = bot
        self.denied_keywords = ['agree', 'i agree', 'yes', 'ok', 'agreed']

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        with contextlib.suppress(discord.HTTPException):
            if message.author.bot or message.channel.id != 706825075516768297:
                return
            if message.content.lower() in self.denied_keywords:
                await message.delete(delay=0.2)
                return await message.channel.send("That's not how this works. 😖\nPlease read the rules again 😅",
                                                  delete_after=10)
            user = message.guild.get_member(799749818062077962)
            argument = message.content
            if argument is None:
                return await message.delete(delay=0)

            if await self.bot.db.fetchval('select user_id from usernames where user_id = $1', message.author.id):
                if message.channel.permissions_for(message.author).manage_messages:
                    return await message.delete(delay=15)
                await message.channel.send(
                    "You're already in the whitelist database. If this is a mistake, contact an admin.",
                    delete_after=10)
                return await self.bot.get_channel(799741426886901850).send(
                    f"{message.author} tried to add themselves to the whitelist, but they're already in the database.")

            if message.guild.get_role(833843541872214056) in message.author.roles:
                return await message.channel.send("⚠ Sorry but you can't do that! you're already whitelisted.",
                                                  delete_after=5)
            await message.delete(delay=0.2)

        async with self.bot.session.get(f"https://api.mojang.com/users/profiles/minecraft/{argument}") as r:
            if r.status in (204, 400):
                return await message.channel.send(
                    f"❌ Sorry {message.author.mention} but **`{argument[0:100]}`** is not a valid **__Minecraft Java Edition__** username.",
                    delete_after=20)

            elif r.status != 200:
                return await message.channel.send(
                    f"❌ **Could not verify username!**\nMinecraft API failed with {r.status}! \n<@349373972103561218> fix this!")

            elif user.status == discord.Status.online:
                res = await r.json()
                user = res["name"]
                uuid = res["id"]

                try:
                    await self.bot.db.execute('insert into usernames (user_id, minecraft_id) values ($1, $2)',
                                              message.author.id, uuid)
                except asyncpg.UniqueViolationError:
                    uuid = await self.bot.db.fetchval('select minecraft_id from usernames where user_id = $1',
                                                      message.author.id)
                    if uuid:
                        await message.channel.send(
                            f"Your discord user id is already in the whitelist database. You will receive the roles."
                            f"\nIf you cannot log on, warn an admin.", delete_after=10)
                    else:
                        await message.channel.send(
                            f"Your minecraft user id is already in the whitelist database. You will receive the roles."
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

    @commands.has_any_role(706637341850206269, 799498278210109472)
    @commands.group()
    async def whitelist(self, ctx: commands.Context):
        if not ctx.message.content.endswith(ctx.invoked_with):
            return
        await ctx.send_help(ctx.command)

    @whitelist.command(name='add')
    async def whitelist_add(self, ctx, member: discord.Member, mc_user: MinecraftName):
        try:
            await self.bot.db.execute("INSERT INTO usernames (user_id, minecraft_id) VALUES ($1, $2)", member.id,
                                      mc_user.uuid)
        except asyncpg.UniqueViolationError:
            uuid = await self.bot.db.fetchval('select minecraft_id from usernames where user_id = $1', member.id)
            if uuid:
                await ctx.send(f"That minecraft name is already linked to an account with a UUID of {uuid}")
            else:
                dc_id = await self.bot.db.fetchval('select user_id from usernames where minecraft_id = $1',
                                                   mc_user.uuid)
                user = self.bot.get_user(dc_id)
                await ctx.send(f"That minecraft name is already saved by {user or dc_id}")
            return
        await ctx.send('Linked.')
        await member.add_roles(ctx.guild.get_role(833843541872214056),
                               ctx.guild.get_role(798698824738668605))
        await member.remove_roles(ctx.guild.get_role(851593341409820722))

    @whitelist.command(name='remove')
    async def whitelist_remove(self, ctx: commands.Context,
                               discord_or_minecraft_user: typing.Union[discord.Member, MinecraftName]):
        member = discord_or_minecraft_user
        if isinstance(member, discord.Member):
            q = await self.bot.db.execute("DELETE FROM usernames WHERE user_id = $1", member.id)
            await ctx.send(f'Done. `{q}`')
        elif isinstance(member, MinecraftName):
            q = await self.bot.db.execute("DELETE FROM usernames WHERE minecraft_id = $1", member.uuid)
            await ctx.send(f"Done. `{q}`")
        else:
            await ctx.send('something went wrong... idk why. <@349373972103561218> fix it.',
                           allowed_mentions=discord.AllowedMentions(everyone=False, users=True, roles=False,
                                                                    replied_user=False))

    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, add_reactions=True)
    @commands.command()
    async def react(self, ctx, message: discord.Message, *emojis: typing.Union[discord.Emoji, UnicodeEmoji]):
        with contextlib.suppress(discord.HTTPException):
            await ctx.message.add_reaction('🔃')
            for emoji in emojis:
                await message.add_reaction(emoji)
            await ctx.message.remove_reaction('🔃', self.bot.user)
            await ctx.message.add_reaction('✅')

    @commands.Cog.listener('on_member_remove')
    async def automatic_whitelist_remover(self, member: discord.Member):
        logs = self.bot.get_channel(799741426886901850)
        console = self.bot.get_channel(764631105097170974)
        uuid: asyncpg.pgproto.pgproto.UUID = await self.bot.db.fetchval(
            'select minecraft_id from usernames where user_id = $1', member.id)
        if not uuid:
            await logs.send(f'Member was not whitelisted.')
        req = await self.bot.session.get(f'https://api.mojang.com/user/profiles/{uuid}/names')
        if req.status != 200:
            return await logs.send(f'Could not get username for {uuid} - did not remove from whitelist.')
        try:
            json = await req.json()
            name = json[-1]['name']
        except (KeyError, IndexError):
            return await logs.send(f'Could not get username for {uuid} - did not remove from whitelist.')
        user = member.guild.get_member(799749818062077962)
        if user.status != discord.Status.online:
            return await logs.send(
                f'{user} is not online, so I cannot remove {member} ({name} / {uuid}) from the whitelist.')
        await console.send(f'whitelist remove {name}')
        await logs.send(f'Removed {member} ({name} / {uuid}) from the whitelist automatically.')
        from discord.http import Route
        route = Route('GET', '/users/@me/connections')


def setup(bot):
    bot.add_cog(Whitelist(bot))
