import json, random, typing, discord, asyncio, yaml, datetime, random
from discord.ext import commands

class info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        #------------- YAML STUFF -------------#
        with open(r'files/config.yaml') as file:
            full_yaml = yaml.full_load(file)
            mguild = self.bot.get_guild(full_yaml['guildID'])
        self.mguild = mguild
        self.yaml_data = full_yaml
        self.verified = mguild.get_role(full_yaml['RulesVerRole'])
        self.unverified = mguild.get_role(full_yaml['RulesUnvRole'])
        self.STLbefore = None

        with open(r'files/triggers.yaml') as triggers:
            trigger_words = yaml.full_load(triggers)
        self.trigger_words = trigger_words

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.channel_id != self.mguild.rules_channel.id: return
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        mem = payload.member.id
        own = self.bot.get_guild(self.yaml_data['guildID']).owner_id

        if self.verified in payload.member.roles and mem != own and self.unverified not in payload.member.roles:
            await message.remove_reaction(payload.emoji, payload.member)
            return
        if mem != own:
            try: await message.remove_reaction(payload.emoji, payload.member)
            except: pass
            try: await payload.member.add_roles(self.verified)
            except:
                pass
            try: await payload.member.remove_roles(self.unverified)
            except:
                pass
        else:
            try: await payload.member.add_roles(self.verified)
            except: pass
            try: await payload.member.remove_roles(self.unverified)
            except: pass


    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != self.yaml_data['guildID']: return

        embed = discord.Embed(color = 0x0066ff,
                            description = f"""Welcome to the {member.guild.name}! You are the {sorted(member.guild.members, key=lambda user: member.joined_at).index(member) + 1} member. Please check out our <#860610050448031784> and agree to the {member.guild.rules_channel.mention} to gain access to the rest of the server. If you need anything, please message me, {self.bot.user.mention}, and our admin team will help you out! We hope you enjoy your time here.""",
                            timestamp = datetime.datetime.now(),
                            title = f"Welcome, {member}")

        embed.set_author(name = member.guild.name,
                        icon_url = member.guild.icon_url)

        embed.set_footer(text = "Member joined")

        await self.bot.get_channel(self.yaml_data['WelcomeChannel']).send(embed = embed)
        await self.bot.get_channel(self.yaml_data['JLLog']).send(f"""<:outgoingarrow:848312880679354368> **{member.name}#{member.discriminator}** joined **{member.guild.name}**!""")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.guild.id != self.yaml_data['guildID']: return
        await self.bot.get_channel(self.yaml_data['JLLog']).send(f"""<:incomingarrow:848312881070080001> **{member.name}#{member.discriminator}** left **{member.guild.name}**!""")


    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            channel = self.bot.get_channel(860633218829778954)
            underaged = before.guild.get_role(863187863038459924)
            overaged = before.guild.get_role(863187815340703755)
            if underaged in before.roles and overaged not in before.roles and overaged in after.roles and underaged not in after.roles:
                await channel.send(before.guild.owner.mention, embed=discord.Embed(
                color = 0xFF0000,
                description=f"""
<:suswell2:863246942853922836> **SUSPICIOUS MEMBER ACTIVITY NOTICED** <:maxwellsus2:863246342250692620>
*{before.mention} has changed their age status from {underaged.mention} to {overaged.mention}*
You might want to follow up on this.
"""
                ))
                self.STLbefore = before
                return

            elif overaged in before.roles and underaged not in before.roles and underaged in after.roles and overaged not in after.roles:
                await channel.send(before.guild.owner.mention, embed=discord.Embed(
                color = 0xFF0000,
                description=f"""
<:suswell2:863246942853922836> **SUSPICIOUS MEMBER ACTIVITY NOTICED** <:maxwellsus2:863246342250692620>
*{before.mention} has changed their age status from {overaged.mention} to {underaged.mention}*
You might want to follow up on this.
"""
))
                self.STLbefore = before
                return

            elif overaged in before.roles and underaged not in before.roles and underaged not in after.roles and overaged not in after.roles:
                self.STLbefore = before
                return

            elif overaged in before.roles and underaged not in before.roles and underaged not in after.roles and overaged not in after.roles:
                self.STLbefore = before
                return

            elif not self.STLbefore:
                self.STLbefore = before
                return

            if self.STLbefore.id != before.id:
                print('not the same person')
                self.STLbefore = before
                return


            if underaged in self.STLbefore.roles and overaged not in self.STLbefore.roles and overaged in after.roles and underaged not in after.roles:
                await channel.send(before.guild.owner.mention, embed=discord.Embed(
                color = 0xFF0000,
                description=f"""
<:suswell2:863246942853922836> **SUSPICIOUS MEMBER ACTIVITY NOTICED** <:maxwellsus2:863246342250692620>
*{before.mention} has changed their age status from {underaged.mention} to {overaged.mention}*
You might want to follow up on this.
"""
                ))
                self.STLbefore = before
                return

            if overaged in self.STLbefore.roles and underaged not in self.STLbefore.roles and underaged in after.roles and overaged not in after.roles:
                await channel.send(before.guild.owner.mention, embed=discord.Embed(
                color = 0xFF0000,
                description=f"""
<:suswell2:863246942853922836> **SUSPICIOUS MEMBER ACTIVITY NOTICED** <:maxwellsus2:863246342250692620>
*{before.mention} has changed their age status from {overaged.mention} to {underaged.mention}*
You might want to follow up on this.
"""
))
                self.STLbefore = before
                return
            print('nothing triggered lmao')

################################################################################

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        if message.channel.id in self.yaml_data['blackholes']:
            await message.delete()
            return
        ###DEPRESSION AND SUICIDAL EMBED DEFINITION###

        suicide_text = f"Hi, {message.author.mention}. If you need to talk to someone, please DM me and an admin will talk to you. Or, use a resource below. We all are here for you.:heart:"
        suicide_embed=discord.Embed(title="DEPRESSION AND SUICIDAL INTENTIONS", description="", color=0x0066ff)
        suicide_embed.add_field(name="National Suicide Prevention Lifeline", value="1-800-273-TALK (8255)", inline=False)
        suicide_embed.add_field(name="American Association of Suicidology", value="The [American Association of Suicidology](http://www.suicidology.org/) (AAS) promotes research, public awareness programs, public education and training for professionals and volunteers. AAS also serves as a national clearinghouse for information on suicide.", inline=False)
        suicide_embed.add_field(name="Depression Screening", value="The [Depression Screening](http://www.depression-screening.org/) website is sponsored by Mental Health America as part of the Campaign for America’s Mental Health. The mission of this website is to educate people about clinical depression, offer a confidential way for people to get screened for symptoms of depression and guide people toward appropriate professional help if necessary.", inline=False)
        suicide_embed.add_field(name="MoodGYM", value="[MoodGYM](http://www.moodgym.anu.edu.au/) has been evaluated in a scientific trial and found to be effective in relieving depression symptoms if people work through it systematically. This website uses cognitive behavioral therapy (CBT) methods to teach people to use ways of thinking that can help prevent depression.", inline=False)
        suicide_embed.add_field(name="Progressive Relaxation", value="[Download](http://www.hws.edu/studentlife/counseling_relax.aspx) two progressive relaxation tapes from the Hobart and William Smith Colleges website.", inline=False)
        suicide_embed.add_field(name="Suicide Prevention Resource Center", value="[The Suicide Prevention Resource Center](http://www.sprc.org/) has fact sheets on suicide by state and by population characteristics, as well as on many other subjects.", inline=False)

        ###NONSUICIDAL SELF-INJURY EMBED DEFINITION###

        self_injury_text = f"Hi, {message.author.mention}. If you need to talk to someone, please DM me and an admin will talk to you. Or, use a resource below. We all are here for you.:heart:"
        self_injury_embed=discord.Embed(title="NONSUICIDAL SELF-INJURY", description="", color=0x0066ff)
        self_injury_embed.add_field(name="Focus Adolescent Services", value="The [Focus Adolescent Services](http://www.focusas.com/) website is designed for parents and covers a wide range of mental health problems, including a section on self-injury.", inline=False)
        self_injury_embed.add_field(name="S.A.F.E. Alternatives (Self-Abuse Finally Ends)", value="[S.A.F.E. Alternatives](http://www.selfinjury.com/) is a residential treatment program for people who engage in self-injury. The website includes information about self-injury and about starting treatment. S.A.F.E information line: (Phone Word Acronym is a TW) ||1-800-DONT-CUT|| (1-800-366-8288)", inline=False)

        if "help" in message.content.lower() and self.bot.user in message.mentions:
            await message.channel.send(f"hello, {message.author.mention}! If you need assistance, please DM me and an admin will assist you!")


        #####  TRIGGERS.YAML STUFF #####

        # Triggers if any of the suicide_triggers in the triggers.yaml is said
        elif any(word in message.content.lower() for word in self.trigger_words['suicide_triggers']):
            # sends the suicide_embed defined above, with the suicide_text as the content
            await message.channel.send(suicide_text, embed=suicide_embed)

        # Triggers if any of the non_sudoku_triggers in the triggers.yaml is said
        elif any(word in message.content.lower() for word in self.trigger_words['non_sudoku_triggers']):
            # sends the self_injury_embed defined above, with the self_injury_text as the content
            await message.channel.send(self_injury_text, embed=self_injury_embed)

        # Triggers if the bot is pinged without context OR if the bot is quoted, and the message is less than 22 characters long.
        elif self.bot.user in message.mentions and message and len(message.content) <= 22:
            # gets the response from the list no_context_responses in triggers.yaml
            response = random.choice(self.trigger_words['no_context_responses'])
            response = response.replace('%PING_USER%', f'{message.author.mention}')
            await message.channel.send(response)

        # Triggers if the bot is pinged with context
        elif self.bot.user in message.mentions:
            # gets the response from the list context_responses in triggers.yaml
            response = random.choice(self.trigger_words['context_responses'])
            response = response.replace('%PING_USER%', f'{message.author.mention}')
            await message.channel.send(response)



                ##  HELP COMMAND\/  ##

    @commands.command()
    async def help(self, ctx:commands.Context):
        embed=discord.Embed(title="Help", description="my prefix is \".\"", color=0xff0000)
        embed.add_field(name="DM me", value="DM me to get in contact with the OSP Admin Team!", inline=False)
        embed.add_field(name=".Rule [rule number]", value="Gives you more information of a specific rule. E.G.: **.Rule 3** would give you more information about Rule number 3.", inline=False)
        embed.add_field(name="Message that mentions me with no other content", value="A randomized message will appear!", inline=False)
        embed.add_field(name="Message that mentions me with other content", value="A randomized response reccomending a DM will appear!", inline=False)
        embed.add_field(name="Says specific trigger word", value="We will send over respective help resources. If there is a missing trigger word you find, message me and we will add it to our database!", inline=False)
        await ctx.send("Here's my help guide! ```Note: only the messages that start with \".\" are actual commands. Others are response triggers.```DM me if you have questions!", embed=embed)

def setup(bot):
    bot.add_cog(info(bot))
