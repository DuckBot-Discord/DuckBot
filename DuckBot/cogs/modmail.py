import discord
from discord.errors import HTTPException
from discord.ext import commands
from discord.ext.commands.errors import UserNotFound

from DuckBot import errors
from DuckBot.__main__ import DuckBot
from DuckBot.helpers import constants
from DuckBot.helpers.context import CustomContext


def setup(bot):
    bot.add_cog(ModMail(bot))


async def get_webhook(channel) -> discord.Webhook:
    webhook_list = await channel.webhooks()
    if webhook_list:
        for hook in webhook_list:
            if hook.token:
                return hook
            else:
                continue
    hook = await channel.create_webhook(name="DuckBot ModMail")
    return hook


class ModMail(commands.Cog):
    """
    🤨 Functions to send and receive DuckBot's DMs.
    For internal purposes only, no commands found here.
    """

    def __init__(self, bot):
        self.bot: DuckBot = bot

    async def get_dm_hook(self, channel: discord.TextChannel) -> discord.Webhook:
        if url := self.bot.dm_webhooks.get(channel.id, None):
            return discord.Webhook.from_url(url, session=self.bot.session, bot_token=self.bot.http.token)
        wh = await get_webhook(channel)
        self.bot.dm_webhooks[channel.id] = wh.url
        return wh

    @commands.Cog.listener('on_message')
    async def on_mail(self, message: discord.Message):
        if message.guild or message.author == self.bot.user or self.bot.dev_mode is True:
            return

        if self.bot.blacklist.get(message.author.id, None):
            return await message.channel.send("Sorry but that message wasn't delivered! You are blacklisted.")

        category = self.bot.get_guild(774561547930304536).get_channel(878123261525901342)
        channel = discord.utils.get(category.channels, topic=str(message.author.id))
        if not channel:
            if not message.reference:
                await message.author.send(
                    "**Warning! This is DuckBot's ModMail thread.** \nThis conversation will be sent to the bot "
                    f"developers. \n_They will reply to you as soon as possible! 💞_\n\n**{constants.EDIT_NICKNAME} "
                    f"Message edits are not saved! {constants.EDIT_NICKNAME}**\nIf the message receives a ⚠ reaction, "
                    "there was an issue delivering the message.")
            channel = await category.create_text_channel(
                name=f"{message.author}",
                topic=str(message.author.id),
                position=0,
                reason="DuckBot ModMail"
            )
            discord.Guild.create_text_channel()

        wh = await self.get_dm_hook(channel)

        files = [await attachment.to_file(spoiler=attachment.is_spoiler()) for attachment in message.attachments if
                 attachment.size < 8388600]
        if not files and message.attachments:
            await message.author.send(
                embed=discord.Embed(description="Some files couldn't be sent because they were over 8mb",
                                    color=discord.Colour.red()))
        try:
            await wh.send(content=message.content,
                          username=message.author.name,
                          avatar_url=message.author.display_avatar.url,
                          files=files)
        except (discord.Forbidden, discord.HTTPException):
            return await message.add_reaction('⚠')

    @commands.Cog.listener('on_message')
    async def on_mail_reply(self, message: discord.Message):
        if not message.guild:
            return
        if any(
                (message.author.bot,
                 self.bot.dev_mode is True,
                 message.channel.category_id != 878123261525901342
                 )
        ):
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
        category = self.bot.get_guild(774561547930304536).get_channel(878123261525901342)
        channel = discord.utils.get(category.channels, topic=str(after.id))
        if channel:
            await channel.edit(
                name=str(after),
                reason=f"DuckBot ModMail Channel Update for {after.id}"
            )
            wh = await self.get_dm_hook(channel)
            embed = discord.Embed(title="ModMail user update!",
                                  color=discord.Colour.blurple(),
                                  timestamp=discord.utils.utcnow())
            embed.add_field(name="Before:",
                            value=str(before))
            embed.add_field(name="After:",
                            value=str(after))
            await wh.send(embed=embed, avatar_url=after.display_avatar.url)
