import discord

from utils import DuckCog
from discord import app_commands
from .._news_viewer import NewsViewer
from bot import DuckBot


class ApplicationNews(DuckCog):
    @app_commands.command(name='news')
    async def app_news(self, interaction: discord.Interaction[DuckBot]):
        """See what's new on DuckBot!"""

        news = await self.bot.pool.fetch("SELECT * FROM news ORDER BY news_id DESC")
        if not news:
            return await interaction.response.send_message("No news has been posted yet.")

        await NewsViewer.from_interaction(interaction, news=news)
