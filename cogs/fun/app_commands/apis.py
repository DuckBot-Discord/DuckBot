import random

import discord
from discord import app_commands

from utils import DuckCog


class ApplicationApis(DuckCog):
    @app_commands.command(name="duck")
    async def app_duck(self, interaction: discord.Interaction) -> None:
        """Sends a random duck image from random-d.uk"""

        await interaction.response.defer()
        followup: discord.Webhook = interaction.followup  # type: ignore

        try:
            async with self.bot.session.get('https://random-d.uk/api/random?format=json') as r:
                if r.status != 200:
                    raise Exception('Something went wrong while trying to access random-d.uk')  # type: ignore
                res = await r.json()
        except Exception as e:
            await followup.send("Apologies! The service for this command is down.")
            return await interaction.client.exceptions.add_error(error=e)  # type: ignore

        embed = discord.Embed(title="Here is a duck!", color=random.randint(0, 0xFFFFFF))
        embed.set_image(url=res["url"])
        embed.set_footer(text='by random-d.uk', icon_url='https://avatars2.githubusercontent.com/u/38426912')
        await followup.send(embed=embed)
