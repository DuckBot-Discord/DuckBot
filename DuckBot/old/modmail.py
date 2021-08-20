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
        hook = await channel.create_webhook(name="OSP-Bot ticket logging")
        return hook

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == 349373972103561218: return
        if message.guild: return
        if message.author == self.bot.user: return
        if message.content.startswith('.'):
            await message.channel.send('⚠ messages starting with `.` will not be sent ⚠', delete_after=5)
            return
        pattern = '^([0-9]{4})'

        channel = self.bot.get_channel(830991980850446366)

        embed = discord.Embed(color=0xD7342A)
        if message.content:
            embed.add_field(name=f'<:incomingarrow:848312881070080001> **{message.author}**', value=f'{message.content}')
        else:
            embed.add_field(name=f'<:incomingarrow:848312881070080001> **{message.author}**', value=f'_ _')
        embed.set_footer(text=f'.dm {message.author.id}')
        if message.attachments:
            file = message.attachments[0]
            spoiler = file.is_spoiler()
            if not spoiler and file.url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
                embed.set_image(url=file.url)
            elif spoiler:
                embed.add_field(name='Attachment', value=f'||[{file.filename}]({file.url})||', inline=False)
            else:
                embed.add_field(name='Attachment', value=f'[{file.filename}]({file.url})', inline=False)
        await channel.send(embed=embed)
        await message.add_reaction('📬')
        await asyncio.sleep(2.5)
        await message.remove_reaction('📬', self.bot.user)

def setup(bot):
    bot.add_cog(events(bot))
