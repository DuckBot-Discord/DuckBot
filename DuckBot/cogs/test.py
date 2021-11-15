import random

import discord
from discord.ext import commands
import quickchart

from DuckBot.__main__ import DuckBot
from DuckBot.helpers.context import CustomContext


def setup(bot):
    bot.add_cog(Test(bot))


class Test(commands.Cog):
    """
    🧪 Test commands. 💀 These may not work, or not be what you think they will.
    Remember that these commands are all a work in progress, and they may or may not ever be released
    """

    def __init__(self, bot):
        self.bot: DuckBot = bot
        self.select_emoji = '🧪'
        self.select_brief = 'Beta Commands (WIP)'

    @commands.command()
    @commands.is_owner()
    async def chart(self, ctx):
        qc = quickchart.QuickChart()
        qc.width = 500
        qc.height = 300

        qc.config = {
            'type': 'line',
            'data': {
                'labels': [f'D{i}' for i in range(100)],
                'datasets': [{
                    'label': 'Online',
                    'data': [random.randint(i, i+5)-random.randint(i, i+5) for i in range(100)],
                    'fill': False,
                    'borderColor': 'rgb(57, 159, 89)',
                    'tension': 0.1
                },
                    {
                        'label': 'Idle',
                        'data': [random.randint(i+5, i+10)-random.randint(i+5, i+10) for i in range(100)],
                        'fill': False,
                        'borderColor': 'rgb(248, 167, 26)',
                        'tension': 0.1
                    },
                    {
                        'label': 'Dnd',
                        'data': [random.randint(i+10, i+15)-random.randint(i+10, i+15) for i in range(100)],
                        'fill': False,
                        'borderColor': 'rgb(237, 66, 69)',
                        'tension': 0.1
                    },
                    {
                        'label': 'Offline',
                        'data': [random.randint(i+15, i+20)-random.randint(i+15, i+20) for i in range(100)],
                        'fill': False,
                        'borderColor': 'rgb(114, 125, 139)',
                        'tension': 0.1
                    }
                ]
            },
        }
        embed = discord.Embed()
        embed.set_image(url=await self.bot.loop.run_in_executor(None, qc.get_short_url))
        await ctx.send(embed=embed)
