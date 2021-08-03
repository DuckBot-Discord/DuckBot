from discord.ext import commands
import asyncio
import datetime
import discord
import re
import os
import humanize

class verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        if message.channel.id != 871770060736307230: return

        try: await message.delete(delay=0.5)
        except: pass

        try:
            new_birthday = datetime.datetime.strptime(message.content, "%m-%d-%Y").date()
            now = datetime.datetime.now().date()
        except:
            await message.channel.send(f"`{message.content}` does not match date format: **MM-DD-YYYY**", delete_after=10)
            return
        formatted = new_birthday.strftime('%B %d, %Y')
        delta = now - new_birthday
        age = int(delta.days / 365.2425)

        def reaction_check(reaction, user):
            return user == message.author and str(reaction.emoji) in ['✅', '❌', '❓'] and reaction.message.id == mess.id

        mess = await message.channel.send(f"recognized: **{formatted}**\n are you **{age}** years old?")
        await mess.add_reaction("✅")
        await mess.add_reaction("❌")

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=120.0, check=reaction_check)

        except asyncio.TimeoutError:
            await message.channel.send("**Failed to confirm in time**", delete_after=10)
            try: await mess.delete()
            except: pass
            return
        else:
            if str(reaction.emoji) == '❌':
                await message.channel.send("**Ok, please try again!**", delete_after=10)
                try: await mess.delete()
                except: pass
                return
            if age <= 0:
                await message.channel.send(f"**{message.author.mention}, age must be greater than 0!**", delete_after=10)
                try: await mess.delete()
                except: pass
                return

        delmessage = await message.channel.send(f"<a:loading:864708067496296468> Please wait while i verify you, {message.author.mention}...")

        try: await mess.delete()
        except: pass
        overage = message.guild.get_role(871812629411291196)
        underage = message.guild.get_role(871812586688090172)
        if not overage or not underage:
            await delmessage.edit(content=f"Sorry, something went wrong getting the roles.")

        current_birthday = await self.bot.db.fetchval('SELECT birthdate FROM userinfo WHERE user_id = $1', message.author.id)

        if current_birthday != None:
            await delmessage.edit(content=f"Sorry {message.author.mention}, but you are already verified with date: **{current_birthday.strftime('%B %d, %Y')}**", delete_after=10)
            return

        await self.bot.db.execute('INSERT INTO userinfo(user_id, birthdate) VALUES ($1, $2)', message.author.id, new_birthday)

        if age >=18:
            await message.author.add_roles(overage)
            await message.author.remove_roles(underage)
        elif age >= 13:
            await message.author.add_roles(underage)
            await message.author.remove_roles(overage)
        else:
            await message.author.remove_roles(underage)
            await message.author.remove_roles(overage)

        if age >= 13:
            await delmessage.edit(content=f"{message.author.mention}, you have been verified with date: **{new_birthday.strftime('%B %d, %Y')}**", delete_after=10)
            return
        else:
            await delmessage.edit(content=f"{message.author.mention}, Your age has been updated. Unfortunately, you cannot verify since you are under 13 years of age. For more information, read Discord's [TOS](http://discord.com/terms). If this is an error, please message me to have our admin team assist you.", delete_after=25)


    @commands.command(name="set")
    @commands.has_permissions(administrator=True)
    async def bday_set(self, ctx, user: discord.User, *, bday: str):
        try:
            new_birthday = datetime.datetime.strptime(bday, "%m-%d-%Y").date()
            now = datetime.datetime.now().date()
        except:
            await message.channel.send(f"`{bday}` does not match date format: **MM-DD-YYYY**", delete_after=10)
            return
        formatted = new_birthday.strftime('%B %d, %Y')
        delta = now - new_birthday
        age = int(delta.days / 365.2425)

        current_birthday = await self.bot.db.fetchval('SELECT birthdate FROM userinfo WHERE user_id = $1', user.id)

        if current_birthday:
            await self.bot.db.execute('UPDATE userinfo SET birthdate = $1 WHERE user_id = $2', new_birthday, user.id)
            deltabd = now - current_birthday
            await ctx.send(f"Birth day updated for {user}: \n`{current_birthday.strftime('%B %d, %Y')} ({int(deltabd.days / 365.2425)} Y/O)` ➡ `{formatted} ({age} Y/O)` \n*remember to update their roles*")
        else:
            mess = await message.channel.send(f"This user doesn't have their birthday set yet. Are you sure you want to set if for them?")
            await mess.add_reaction("✅")
            await mess.add_reaction("❌")
            def reaction_check(reaction, user):
                return user == message.author and str(reaction.emoji) in ['✅', '❌', '❓'] and reaction.message.id == mess.id
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=120.0, check=reaction_check)

            except asyncio.TimeoutError:
                await mess.edit(content="**Failed to confirm in time**")
                return
            else:
                if str(reaction.emoji) == '❌':
                    await mess.edit(content="**Ok, did not update their birt date!**")
                    return
            await self.bot.db.execute('INSERT INTO userinfo(user_id, birthdate) VALUES ($1, $2)', user.id, new_birthday)
            await mess.edit(content=f"Birth day updated for {user} to `{formatted} ({age} Y/O)` \n*remember to update their roles*")

    @commands.command()
    async def allbds(self, ctx):
        dates = await self.bot.db.fetch("TABLE userinfo")
        lr = []
        for r in dates:
            lr.append(f"<@{r['user_id']}> {r['birthdate'].strftime('%B %d, %Y')}")
        bds = "\n".join(lr)
        await ctx.send(embed=discord.Embed(description=bds))



def setup(bot):
    bot.add_cog(verification(bot))
