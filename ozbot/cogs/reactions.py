import typing, discord, asyncio, yaml
from discord.ext import commands

class nopog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
    words = ['nothing', 'nothing']
    with open(r'files/banned-words.yaml') as file:
        words = yaml.full_load(file)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        banned_words = self.words['pogwords']
        if any(ele in message.content.lower() for ele in banned_words):
            await message.add_reaction('<:nopog:838102336944603186>')
            await message.add_reaction('😡')



def setup(bot):
    bot.add_cog(nopog(bot))
