import json, random, typing, discord, asyncio, yaml
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

def setup(bot):
    bot.add_cog(info(bot))
