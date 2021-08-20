from discord.ext import commands, menus, tasks
from discord.ext.menus.views import ViewMenuPages
import asyncio
import datetime
import discord
import re
import os
import humanize
import typing
import yaml

class AllEmbed(menus.ListPageSource):
    def __init__(self, data, per_page=20):
        super().__init__(data, per_page=per_page)

    async def format_page(self, menu, entries):
        embed = discord.Embed(title=f"All birth dates",
                              description="\n".join(entries))
        return embed


class verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_task.start()
        self.counters.start()
        self._members = 0
        self._creators = 0
        self._storytellers = 0

        #------------- YAML STUFF -------------#
        with open(r'files/config.yaml') as file:
            full_yaml = yaml.full_load(file)
            staff_roles = []
            for roleid in full_yaml['StaffRoles']:
                staff_roles.append(self.bot.get_guild(full_yaml['guildID']).get_role(roleid))
        self.staff_roles = staff_roles
        self.yaml_data = full_yaml
        self.underaged = self.bot.get_guild(full_yaml['guildID']).get_role(full_yaml['Underage'])
        self.overaged = self.bot.get_guild(full_yaml['guildID']).get_role(full_yaml['Overage'])
        self.verified = self.bot.get_guild(full_yaml['guildID']).get_role(full_yaml['RulesVerRole'])
        self.unverified = self.bot.get_guild(full_yaml['guildID']).get_role(full_yaml['RulesUnvRole'])
        self.tosrole = self.bot.get_guild(full_yaml['guildID']).get_role(full_yaml['TosRole'])


    def cog_unload(self):
        self.daily_task.cancel()
        self.second_daily_task.cancel()
        self.counters.cancel()

    @tasks.loop(minutes=10)
    async def counters(self):
        maguild = self.bot.get_guild(self.yaml_data['guildID'])
        storytellers = maguild.get_role(self.yaml_data['_storytellers'])
        creators = maguild.get_role(self.yaml_data['_creators'])

        ch_members = maguild.get_channel(self.yaml_data['ch_members'])
        ch_storytellers = maguild.get_channel(self.yaml_data['ch_storytellers'])
        ch_creators = maguild.get_channel(self.yaml_data['ch_creators'])

        mc_members = len([x for x in maguild.members if not x.bot])
        if mc_members != self._members:
            self._members = mc_members
            await ch_members.edit(name=f"MEMBERS: {mc_members}")

        mc_storytellers = len([x for x in storytellers.members if not x.bot])
        if mc_storytellers != self._storytellers:
            self._storytellers = mc_storytellers
            await ch_storytellers.edit(name=f"STORYTELLERS: {mc_storytellers}")

        mc_creators = len([x for x in creators.members if not x.bot])
        if mc_creators != self._creators:
            self._creators = mc_creators
            await ch_creators.edit(name=f"CREATORS: {mc_creators}")



    @tasks.loop(hours=24)
    async def daily_task(self):
        query = """SELECT * FROM userinfo
                   WHERE EXTRACT(day from birthdate) = date_part('day' , CURRENT_DATE)
                   AND EXTRACT(month from birthdate) = date_part('month', CURRENT_DATE)
                """

        query_tmr = """SELECT * FROM userinfo
                   WHERE EXTRACT(day from birthdate) = date_part('day' , current_date - INTEGER '1')
                   AND EXTRACT(month from birthdate) = date_part('month', current_date - INTEGER '1')
                """
        ids_tmr = await self.bot.db.fetch(query_tmr)


        ids_today = await self.bot.db.fetch(query)

        if len(ids_today) == 0 and len(ids_tmr) == 0: return

        now = discord.utils.utcnow().date()

        if len(ids_today) != 0:
            for entry in ids_today:
                delta = now - entry['birthdate']
                age = int(delta.days / 365.2425)
                OverageChannel = self.bot.get_channel(self.yaml_data['OverageBdayChannel'])
                UnderageChannel = self.bot.get_channel(self.yaml_data['UnderageBdayChannel'])
                BdayRoles = UnderageChannel.guild.get_role(self.yaml_data['BdayRole'])

                if age >= 18:

                    role_user = UnderageChannel.guild.get_member(entry['user_id'])
                    if role_user:
                        try: await role_user.add_roles(BdayRoles)
                        except: pass
                        embed=discord.Embed(title=f"Today is {role_user}'s birthday!", description="Don't forget to wish them a happy birthday below!", color=0x0066ff)
                        embed.set_author(name=role_user, icon_url=role_user.avatar.url)
                        embed.set_thumbnail(url="https://i.pinimg.com/originals/4f/b9/96/4fb996524beabfa60c7ca4394057bbc9.gif")

                        try: await OverageChannel.send(f"🎉 {role_user.mention} 🎉", embed=embed)
                        except: pass

                        if self.overaged not in role_user.roles:

                            try: await role_user.add_roles(self.overaged)
                            except: pass

                        if self.underaged in role_user.roles:
                            try: await role_user.remove_roles(self.underaged)
                            except: pass

                        if age == 18:
                            try: await role_user.send("Happy birthday! 🎉 You have been moved to the 18+ categories")
                            except: pass

                    else:
                        try: await self.bot.get_channel(self.yaml_data['JLLog']).send(f"could not resolve database entry **{entry['user_id']}** into a user! not sending birthday message.")
                        except: pass

                else:

                    role_user = UnderageChannel.guild.get_member(entry['user_id'])

                    if role_user:
                        try: await role_user.add_roles(BdayRoles)
                        except: pass
                        embed=discord.Embed(title=f"Today is {ctx.author}'s birthday!", description="Don't forget to wish them a happy birthday below!", color=0x0066ff)
                        embed.set_author(name=role_user, icon_url=role_user.avatar.url)
                        embed.set_thumbnail(url="https://i.pinimg.com/originals/4f/b9/96/4fb996524beabfa60c7ca4394057bbc9.gif")

                        try: await UnderageChannel.send(f"🎉 {role_user.mention} 🎉", embed=embed)
                        except: pass

                        if self.overaged in role_user.roles:
                            try: await role_user.remove_roles(self.overaged)
                            except: pass

                        if self.underaged not in role_user.roles:
                            try: await role_user.add_roles(self.underaged)
                            except: pass

                    else:
                        try: await self.bot.get_channel(self.yaml_data['JLLog']).send(f"could not resolve database entry **{entry['user_id']}** into a user! not sending birthday message.")
                        except: pass
                await asyncio.sleep(1)
        if len(ids_tmr) != 0:
            for entry in ids_tmr:

                UnderageChannel = self.bot.get_channel(self.yaml_data['UnderageBdayChannel'])
                BdayRoles = UnderageChannel.guild.get_role(self.yaml_data['BdayRole'])
                role_user = UnderageChannel.guild.get_member(entry['user_id'])

                if role_user:
                    try:
                        await role_user.remove_roles(BdayRoles)
                        print(f"{role_user} got their bday role removed.")
                    except: pass

    @daily_task.before_loop
    async def wait_until_7am(self):
        await self.bot.wait_until_ready()
        now = datetime.datetime.now().astimezone()
        next_run = now.replace(hour=4, minute=0, second=0)

        if next_run < now:
            next_run += datetime.timedelta(days=1)

        await discord.utils.sleep_until(next_run)


    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        if message.channel.id != self.bot.get_guild(self.yaml_data['guildID']).rules_channel.id: return

        try: await message.delete(delay=0.5)
        except: pass

        try:
            new_birthday = datetime.datetime.strptime(message.content, "%m-%d-%Y").date()
            now = datetime.datetime.now().date()
        except:
            await message.channel.send(f"`{message.content}` does not match date format: **MM-DD-YYYY**\n_month**-**day**-**year. E.G: (`09-24-2001`)", delete_after=10)
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
        overage = self.overaged
        underage = self.underaged
        tosrole = self.tosrole
        if not overage or not underage:
            await delmessage.edit(content=f"Sorry, something went wrong getting the roles.")

        current_birthday = await self.bot.db.fetchval('SELECT birthdate FROM userinfo WHERE user_id = $1', message.author.id)

        if current_birthday:
            await delmessage.edit(content=f"Sorry {message.author.mention}, but you previously verified with date: **{current_birthday.strftime('%B %d, %Y')}**\n\n If you think this is an error, please DM me ({message.guild.me.mention}) to get in contact with an admin.\n_this message will delete in 60 seconds_\n_ _", delete_after=60)
            age = int((now - current_birthday).days /365.2425)
        else:
            await self.bot.db.execute('INSERT INTO userinfo(user_id, birthdate) VALUES ($1, $2)', message.author.id, new_birthday)

        if age >=18:
            await message.author.add_roles(overage, self.verified)
            await message.author.remove_roles(underage, self.unverified)
        elif age >= 13:
            await message.author.add_roles(underage, self.verified)
            await message.author.remove_roles(overage, self.unverified)
        else:
            await message.author.remove_roles(underage, overage, self.verified)
            await message.author.add_roles(tosrole, self.unverified)

        if age >= 13:
            if not current_birthday:
                await delmessage.edit(content=f"{message.author.mention}, you have been verified with date: **{new_birthday.strftime('%B %d, %Y')}**", delete_after=15)
                return
            else:
                await message.channel.send(f"{message.author.mention} i gave you the corresponding roles according to the age you had registered before.", delete_after=15)
        else:
            if not current_birthday:
                await delmessage.edit(content=f"{message.author.mention}, Your age has been updated. Unfortunately, you cannot verify since you are under 13 years of age. For more information, read Discord's Terms Of Service: http://discord.com/terms. \n_If this is an error, please message me to have ({message.guild.me.mention}) our admin team assist you._\n_this message will delete in 60 seconds_", delete_after=60)
            else:
                await message.channel.send(f"{message.author.mention}, Your age has been updated. Unfortunately, you cannot verify since you are under 13 years of age. For more information, read Discord's Terms Of Service: http://discord.com/terms. \n_If this is an error, please message me to have ({message.guild.me.mention}) our admin team assist you._\n_this message will delete in 60 seconds_", delete_after=60)
########################################################################################################
#################################### DATABASE MANAGEMENT CMD ###########################################
########################################################################################################

    @commands.group(help="Command group to manage the birth date verification database #Admin Only", aliases=['bd', 'birthdate', 'birthday'], hidden=True)
    @commands.has_permissions(administrator=True)
    async def bday(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @bday.command(name="set", help="Sets a user's birthday")
    async def bday_set(self, ctx, member: discord.User, *, bday: str):
        try:
            new_birthday = datetime.datetime.strptime(bday, "%m-%d-%Y").date()
            now = datetime.datetime.now().date()
        except:
            await ctx.send(f"`{bday}` does not match date format: **MM-DD-YYYY**", delete_after=10)
            return
        formatted = new_birthday.strftime('%B %d, %Y')
        delta = now - new_birthday
        age = int(delta.days / 365.2425)

        current_birthday = await self.bot.db.fetchval('SELECT birthdate FROM userinfo WHERE user_id = $1', member.id)

        if current_birthday:
            await self.bot.db.execute('UPDATE userinfo SET birthdate = $1 WHERE user_id = $2', new_birthday, member.id)
            deltabd = now - current_birthday
            await ctx.send(f"Birth day updated for {member}: \n`{current_birthday.strftime('%B %d, %Y')} ({int(deltabd.days / 365.2425)} Y/O)` ➡ `{formatted} ({age} Y/O)` \n*remember to update their roles*")
        else:
            mess = await ctx.send(f"{member} doesn't have their birthday set yet. Are you sure you want to set if for them?")
            await mess.add_reaction("✅")
            await mess.add_reaction("❌")
            def reaction_check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ['✅', '❌', '❓'] and reaction.message.id == mess.id
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=reaction_check)

            except asyncio.TimeoutError:
                await mess.edit(content="**Failed to confirm in time**")
                return
            else:
                if str(reaction.emoji) == '❌':
                    await mess.edit(content="**Ok, did not update their birt date!**")
                    return
            await self.bot.db.execute('INSERT INTO userinfo(user_id, birthdate) VALUES ($1, $2)', member.id, new_birthday)
            await mess.edit(content=f"Birth day updated for {member} to `{formatted} ({age} Y/O)` \n*remember to update their roles*")

    @bday.command(name='all', help="Gives a list of all birthdays sorted by ASC/DESC date")
    async def bday_all(self, ctx, sort = 'ASC/DESC'):
        if sort.upper() not in ['ASC', 'DESC']: sort = 'DESC'
        if sort.lower() == 'asc':
            dates = await self.bot.db.fetch("SELECT * FROM userinfo ORDER BY birthdate ASC")
        else:
            dates = await self.bot.db.fetch("SELECT * FROM userinfo ORDER BY birthdate DESC")
        lr = []
        for r in dates:
            lr.append(f"<@{r['user_id']}> `{r['birthdate'].strftime('%B %d, %Y')} ({int((datetime.datetime.now().date() - r['birthdate']).days / 365.2425)} Y/O)`")
        pages = ViewMenuPages(source=AllEmbed(lr), delete_message_after=True)
        await pages.start(ctx)
        return

    @bday.command(help="Deletes a birthday if found", name="del", aliases=['rem'])
    async def _del(self, ctx, member: discord.User):
        current_birthday = await self.bot.db.fetchval('SELECT birthdate FROM userinfo WHERE user_id = $1', member.id)
        if current_birthday:
            mess = await ctx.send(f"Are you sure you want to delete **{member}**'s birthday from the database?")
            await mess.add_reaction("✅")
            await mess.add_reaction("❌")
            def reaction_check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ['✅', '❌', '❓'] and reaction.message.id == mess.id

            try: reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=reaction_check)
            except asyncio.TimeoutError: return await mess.edit(content="**Failed to confirm in time**")
            else:
                if str(reaction.emoji) == '❌': return await mess.edit(content="**Ok, did not delete their birt date!**")
            await self.bot.db.execute("DELETE FROM userinfo WHERE user_id = $1", member.id)
            await mess.edit(content=f"birthday for **{member}** deleted!")
        else: return await ctx.send(f"{member} is not in the database!")

    @bday.command(name="delid", help="deletes a birthday without checking if the ID exists", aliases=['remid'])
    async def bday_del_id(self, ctx, id: int):
        if re.fullmatch("^\d{18}$", str(id)):
            current_birthday = await self.bot.db.fetchval('SELECT birthdate FROM userinfo WHERE user_id = $1', id)
            if current_birthday:
                def reaction_check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) in ['✅', '❌', '❓'] and reaction.message.id == mess.id
                mess = await ctx.send(f"Are you sure you want to delete **{id}**'s birthday from the database?")
                await mess.add_reaction("✅")
                await mess.add_reaction("❌")
                try: reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=reaction_check)
                except asyncio.TimeoutError: return await mess.edit(content="**Failed to confirm in time**")
                else:
                    if str(reaction.emoji) == '❌': return await mess.edit(content="**Ok, did not delete their birt date!**")
                await self.bot.db.execute("DELETE FROM userinfo WHERE user_id = $1", id)
                return await mess.edit(content=f"birthday for **{id}** deleted!")
            else: return await ctx.send(f"{id} is not in the database!")
        else:
            await ctx.send("That's not a valid discord ID!")

    @bday.command(help="Tries to fetch user information from a given ID", name="find", aliases=['get', 'lookup'])
    async def bday_user(self, ctx, member: discord.User):
        current_birthday = await self.bot.db.fetchval('SELECT birthdate FROM userinfo WHERE user_id = $1', member.id)
        if current_birthday:
            embed=discord.Embed(color = ctx.me.color, title=f"Birthday: {current_birthday.strftime('%B %d, %Y')} ({int((datetime.datetime.now().date() - current_birthday).days / 365.2425)} Y/O)")
        else:
            embed=discord.Embed(color = ctx.me.color, title=f"Birthday: not found...")
        embed.set_author(name=member, icon_url=member.avatar.url)
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(verification(bot))
