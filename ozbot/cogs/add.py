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

    with open('files/banned-words.yaml','r') as yamlfile:
        cur_yaml = yaml.safe_load(yamlfile) # Note the safe_load
        cur_yaml['bugs_tree'].update(new_yaml_data_dict)

    if cur_yaml:
        with open('bugs.yaml','w') as yamlfile:
            yaml.safe_dump(cur_yaml, yamlfile) # Also note the safe_dump


def setup(bot):
    bot.add_cog(nopog(bot))
