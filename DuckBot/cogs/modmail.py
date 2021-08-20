import discord, asyncio, typing
from discord.ext import commands

class events(commands.Cog):
    """How did you get here 🤨"""
    def __init__(self, bot):
        self.bot = bot

    async def get_webhook(self, channel):
        hookslist = await channel.webhooks()
        if hookslist:
            for hook in hookslist:
                if hook.token:
                    return hook
                else: continue
        hook = await channel.create_webhook(name="DuckBot ModMail")
        return hook

    @commands.Cog.listener('on_message')
    async def modmail(self, message):
        if message.guild: return
        if message.author == self.bot.user: return
        category = self.bot.get_guild(774561547930304536).get_channel(878123261525901342)
        channel = discord.utils.get(category.channels, name=str(message.author.id))
        if not channel:
            await message.author.send("**Warning! This is DuckBot's modmail thread.** \nThis conversation will be sent to the bot developers. \n_They will reply to you as soon as possible! 💞_\n\n**<:nickname:850914031953903626> Message edits are not saved! <:nickname:850914031953903626>**\nIf the message recieves a ⚠ reaction, there was an issue delivering the message.")
            channel = await category.create_text_channel(name=str(message.author.id), position=0, reason="DuckBot ModMail")
        wh = await self.get_webhook(channel)

        files = []
        for attachment in message.attachments:
            if attachment.size > 8388600:
                await message.author.send('Sent message without attachment! File size greater than 8 MB.')
                continue
            files.append(await attachment.to_file(spoiler=attachment.is_spoiler()))

        try:
            await wh.send(content=message.content, username=message.author.name, avatar_url=message.author.avatar.url, files=files)
        except: return await message.add_reaction('⚠')

    @commands.Cog.listener('on_message')
    async def modmail_reply(self, message):
        if not message.guild: return
        if message.author.bot: return
        if message.channel.category_id != 878123261525901342: return

        user = self.bot.get_user(int(message.channel.name))
        if not user or not user.mutual_guilds:
            return await message.channel.send("could not find user.")

        files = []
        for attachment in message.attachments:
            if attachment.size > 8388600:
                await message.author.send('Sent message without attachment! File size greater than 8 MB.')
                continue
            files.append(await attachment.to_file(spoiler=attachment.is_spoiler()))

        try:
            await user.send(content=message.content, files=files)
        except: return await message.add_reaction('⚠')

def setup(bot):
    bot.add_cog(events(bot))
