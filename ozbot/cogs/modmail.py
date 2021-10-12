import discord
import yaml
from discord.errors import HTTPException
from discord.ext import commands
from discord.ext.commands.errors import UserNotFound

import constants


async def get_webhook(channel):
    hookslist = await channel.webhooks()
    if hookslist:
        for hook in hookslist:
            if hook.token:
                return hook
            else:
                continue
    hook = await channel.create_webhook(name="DuckBot ModMail")
    return hook

class modmail(commands.Cog):
    """🎫 Dm the bot for help!"""
    def __init__(self, bot):
        self.bot = bot
        #------------- YAML STUFF -------------#
        with open(r'files/config.yaml') as file:
            full_yaml = yaml.full_load(file)
            staff_roles = []
            for roleid in full_yaml['StaffRoles']:
                staff_roles.append(self.bot.get_guild(full_yaml['guildID']).get_role(roleid))
        self.staff_roles = staff_roles
        self.yaml_data = full_yaml

    @commands.Cog.listener('on_message')
    async def modmail(self, message):
        if message.guild or message.author == self.bot.user:
            return

        category = self.bot.get_guild(706624339595886683).get_channel(879414245052284958)
        channel = discord.utils.get(category.channels, name=str(message.author.id))
        if not channel:
            channel = await category.create_text_channel(
                name=str(message.author.id),
                topic=f"{message.author}'s DMs",
                position=0,
                reason="OzBot ModMail"
        )
        wh = await get_webhook(channel)

        files = []
        if message.attachments:
            for attachment in message.attachments:
                if attachment.size > 8388600:
                    await message.author.send('Sent message without attachment! File size greater than 8 MB.')
                    continue
                files.append(await attachment.to_file(spoiler=attachment.is_spoiler()))

        try:
            await wh.send(content=message.content, username=message.author.name, avatar_url=message.author.display_avatar.url,
                          files=files)
        except:
            return await message.add_reaction('⚠')

    @commands.Cog.listener('on_message')
    async def modmail_reply(self, message):
        if any((not message.guild, message.author.bot, message.channel.category_id != 879414245052284958)):
            return

        channel = message.channel

        try:
            user = self.bot.get_user(int(channel.name)) or (await self.bot.fetch_user(int(channel.name)))
        except (HTTPException, UserNotFound):
            return await channel.send("could not find user.")

        files = []
        if message.attachments:
            for attachment in message.attachments:
                if attachment.size > 8388600:
                    await message.author.send('Sent message without attachment! File size greater than 8 MB.')
                    continue
                files.append(await attachment.to_file(spoiler=attachment.is_spoiler()))

        try:
            await user.send(content=message.content, files=files)
        except:
            return await message.add_reaction('⚠')

    @commands.command(aliases=['pm', 'message', 'direct'])
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def dm(self, ctx, member: discord.Member, *, message = None):
        if ctx.channel.category_id == 879414245052284958: return

        if not any(role in self.staff_roles for role in ctx.author.roles):
            raise discord.MissingPermissions('staff_role')

        category = self.bot.get_guild(706624339595886683).get_channel(879414245052284958)
        channel = discord.utils.get(category.channels, name=str(member.id))
        if not channel:
            channel = await category.create_text_channel(
                name=str(member.id),
                topic=f"{member}'s DMs",
                position=0,
                reason="OzBot ModMail"
        )

        wh = await get_webhook(channel)

        files = []
        if ctx.message.attachments:
            for attachment in ctx.message.attachments:
                if attachment.size > 8388600:
                    await ctx.send('Sent message without attachment! File size greater than 8 MB.')
                    continue
                files.append(await attachment.to_file(spoiler=attachment.is_spoiler()))

        try:
            await member.send(content=message, files=files)
            try:
                await ctx.message.delete()
            except:
                pass
        except:
            return await ctx.message.add_reaction('⚠')

        try:
            await wh.send(content=message, username=ctx.author.name, avatar_url=ctx.author.display_avatar.url,
                          files=files)
        except:
            pass




    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != 706624339595886683: return
        if not member.bot: await self.bot.get_channel(706624465378738217).send(f"""{member.mention}, Welcome to {member.guild.name}! Make sure to read and agree to the <#706825075516768297> to get access to the rest of {member.guild.name}.""")
        await self.bot.get_channel(708316690638700607).send(f"""{constants.JOINED_SERVER} **{member.name}#{member.discriminator}** joined **{member.guild.name}**!""")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.guild.id != 706624339595886683: return
        await self.bot.get_channel(708316690638700607).send(f"""{constants.LEFT_SERVER} **{member.name}#{member.discriminator}** left **{member.guild.name}**!""")

def setup(bot):
    bot.add_cog(modmail(bot))
