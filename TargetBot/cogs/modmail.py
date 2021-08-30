import discord
from discord.errors import HTTPException
from discord.ext import commands
from discord.ext.commands.errors import UserNotFound


def setup(bot):
    bot.add_cog(Events(bot))


async def get_webhook(channel):
    webhook_list = await channel.webhooks()
    if webhook_list:
        for hook in webhook_list:
            if hook.token:
                return hook
            else:
                continue
    hook = await channel.create_webhook(name="TargetBot ModMail")
    return hook


class Events(commands.Cog):
    """How did you get here 🤨"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener('on_message')
    async def on_mail(self, message):
        if message.guild or message.author == self.bot.user:
            return

        category = self.bot.get_guild(717140270789033984).get_channel(881734985244086342)
        channel = discord.utils.get(category.channels, topic=str(message.author.id))
        if not channel:
            await message.author.send(
                "Hello! Thanks for contacting the Stylized Resource Pack team. A staff member will help you soon."
                "\n⚠ The following actions will not be logged: **Editing messages**, **Deleting messages**")
            channel = await category.create_text_channel(
                name=f"{message.author}",
                topic=str(message.author.id),
                position=0,
                reason="DuckBot ModMail"
            )
        wh = await get_webhook(channel)

        files = [await attachment.to_file(spoiler=attachment.is_spoiler()) for attachment in message.attachments if
                 attachment.size < 8388600]
        if not files and message.attachments:
            await message.author.send("Some files couldn't be sent because they were over 8mb")

        try:
            await wh.send(content=message.content,
                          username=message.author.name,
                          avatar_url=message.author.display_avatar.url,
                          files=files)
        except (discord.Forbidden, discord.HTTPException):
            return await message.add_reaction('⚠')

    @commands.Cog.listener('on_message')
    async def on_mail_reply(self, message):
        if any((not message.guild, message.author.bot)):
            return
        if message.channel.category_id != 881734985244086342:
            return

        channel = message.channel
        try:
            user = self.bot.get_user(int(channel.topic)) or \
                   await self.bot.fetch_user(int(channel.topic))

        except (HTTPException, UserNotFound):
            return await channel.send("could not find user.")

        files = [await attachment.to_file(spoiler=attachment.is_spoiler()) for attachment in message.attachments if
                 attachment.size < 8388600]
        if not files and message.attachments:
            await message.author.send("Some files couldn't be sent because they were over 8mb")

        try:
            await user.send(content=message.content, files=files)
        except (discord.Forbidden, discord.HTTPException):
            return await message.add_reaction('⚠')

    @commands.Cog.listener('on_user_update')
    async def on_mail_username_change(self, before: discord.User, after: discord.User):
        if str(before) == str(after) or before.bot:
            return
        category = self.bot.get_guild(717140270789033984).get_channel(881734985244086342)
        channel = discord.utils.get(category.channels, topic=str(after.id))
        if channel:
            await channel.edit(
                name=str(after),
                reason=f"DuckBot ModMail Channel Update for {after.id}"
            )
            wh = await get_webhook(channel)
            embed = discord.Embed(title="ModMail user update!",
                                  color=discord.Colour.blurple(),
                                  timestamp=discord.utils.utcnow())
            embed.add_field(name="Before:",
                            value=str(before))
            embed.add_field(name="After:",
                            value=str(after))
            await wh.send(embed=embed)
