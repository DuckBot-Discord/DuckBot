import random
from typing import Optional

import discord
from discord import TextChannel
from discord.ext import commands

from ._base import EventsBase


class WelcomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji='🗑', custom_id='delete_joining_message')
    async def delete(self, interaction: discord.Interaction, _):
        await interaction.message.delete()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            return False
        member = interaction.guild.get_member(interaction.user.id)
        channel = interaction.channel
        if member and channel.permissions_for(member).manage_messages:
            return True
        await interaction.response.defer()
        return False


class ArrivalAndCleanup(EventsBase):
    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        await self.bot.db.execute('DELETE FROM prefixes WHERE guild_id = $1', guild.id)
        await self.bot.db.execute('DELETE FROM temporary_mutes WHERE guild_id = $1', guild.id)
        for channel in guild.text_channels:
            await self.bot.db.execute('DELETE FROM suggestions WHERE channel_id = $1', channel.id)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.bot.db.execute('DELETE FROM prefixes WHERE guild_id = $1', guild.id)
        await self.bot.db.execute('DELETE FROM temporary_mutes WHERE guild_id = $1', guild.id)
        for channel in guild.text_channels:
            await self.bot.db.execute('DELETE FROM suggestions WHERE channel_id = $1', channel.id)

    @staticmethod
    def get_delivery_channel(guild: discord.Guild) -> Optional[TextChannel]:
        channels = [c for c in guild.text_channels if c.permissions_for(guild.me).send_messages]
        if not channels:
            return None
        channel = (
            discord.utils.get(channels, name='general')
            or discord.utils.find(lambda c: 'general' in c.name, channels)
            or discord.utils.find(lambda c: c == guild.system_channel, channels)
        )
        if not channel:
            public_channels = [c for c in channels if c.permissions_for(guild.default_role).send_messages]
            return random.choice(public_channels) or random.choice(channels)
        return channel

    @commands.Cog.listener("on_guild_join")
    async def on_bot_added(self, guild: discord.Guild):
        channel = self.get_delivery_channel(guild)
        if not channel:
            return
        embed = discord.Embed(
            timestamp=discord.utils.utcnow(),
            color=0xF8DA94,
            description="Thanks for adding me to your server!"
            "\n**My default prefix is `db.`**, but you can"
            "\nchange it by running the command"
            "\n`db.prefix add <prefix>`. I can have"
            "\nmultiple prefixes, for convenience."
            "\n\n**For help, simply do `db.help`.**"
            "\nA list of all my commmands is [here](https://github.com/leoCx1000/discord-bots/#readme)"
            "\n\n**For suggestions, run the `db.suggest`"
            "\ncommand, and for other issues, DM"
            "\nme or join my support server!**"
            "\n\n⭐ **Tip:** Set up logging!"
            "\ndo `db.log auto-setup`"
            "\n⭐ **Tip:** Vote! `db.vote`",
        )
        embed.set_author(name='Thanks for adding me!', icon_url=self.bot.user.display_avatar.url)
        embed.set_footer(icon_url='https://cdn.discordapp.com/emojis/907399757146767371.png?size=44', text='thank you!')
        await channel.send(embed=embed, view=WelcomeView())

    @commands.Cog.listener('on_ready')
    async def register_view(self):
        if not hasattr(self.bot, 'welcome_button_added'):
            self.bot.add_view(WelcomeView())
            self.bot.welcome_button_added = True
