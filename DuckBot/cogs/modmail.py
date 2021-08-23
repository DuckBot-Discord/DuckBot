import discord, asyncio, typing
from discord.errors import HTTPException
from discord.ext import commands
from discord.ext.commands.errors import UserNotFound


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


class Events(commands.Cog):
    """How did you get here 🤨"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener('on_message')
    async def modmail(self, message):
        if message.guild or message.author == self.bot.user:
            return

        category = self.bot.get_guild(774561547930304536).get_channel(878123261525901342)
        channel = discord.utils.get(category.channels, name=str(message.author.id))
        if not channel:
            await message.author.send(
                "**Warning! This is DuckBot's modmail thread.** \nThis conversation will be sent to the bot "
                "developers. \n_They will reply to you as soon as possible! 💞_\n\n**<:nickname:850914031953903626> "
                "Message edits are not saved! <:nickname:850914031953903626>**\nIf the message recieves a ⚠ reaction, "
                "there was an issue delivering the message.")
            channel = await category.create_text_channel(
                name=str(message.author.id),
                topic=f"{message.author}'s DMs",
                position=0,
                reason="DuckBot ModMail"
        )
        wh = await get_webhook(channel)

        files = []
        for attachment in message.attachments:
            if attachment.size > 8388600:
                await message.author.send('Sent message without attachment! File size greater than 8 MB.')
                continue
            files.append(await attachment.to_file(spoiler=attachment.is_spoiler()))

        try:
            await wh.send(content=message.content, username=message.author.name, avatar_url=message.author.avatar.url,
                          files=files)
        except:
            return await message.add_reaction('⚠')

    @commands.Cog.listener('on_message')
    async def modmail_reply(self, message):
        if any((not message.guild, message.author.bot, message.channel.category_id != 878123261525901342)):
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


def setup(bot):
    bot.add_cog(Events(bot))
