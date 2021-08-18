import typing, discord, asyncio, random, datetime
from discord.ext import commands, tasks, timers
import datetime

class test(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def error_message(self, ctx, message):
        embed = discord.Embed(color=ctx.me.color)
        embed.set_author(name=message, icon_url='https://i.imgur.com/OAmzSGF.png')
        await ctx.send(embed=embed, delete_after=5)
        try: await ctx.message.delete(delay = 5)
        except: pass


    @commands.command()
    @commands.is_owner()
    @commands.cooldown(1, 10.0, commands.BucketType.guild)
    async def move(self, ctx, amount: typing.Optional[int], channel: typing.Optional[discord.TextChannel]):

        # Limitation checking

        if channel == None:
            await self.error_message(ctx, 'you must specify a channel: .move <amount> <#channel>')
            ctx.command.reset_cooldown(ctx)
            return
        elif channel == ctx.channel:
            await self.error_message(ctx, "channel can't be this channel: .move <amount> <#channel>")
            ctx.command.reset_cooldown(ctx)
            return
        if not channel.permissions_for(ctx.guild.me).manage_webhooks and not ctx.channel.permissions_for(ctx.me).manage_messages:
            await self.error_message(ctx, 'missing necessary permissions')
            ctx.command.reset_cooldown(ctx)
            return
        if amount == None:
             await self.error_message(ctx, 'you must specify an amount: .move <amount> <#channel>')
             ctx.command.reset_cooldown(ctx)
             return
        elif amount > 15:
            await self.error_message(ctx, 'you can only move 15 messages!')
            ctx.command.reset_cooldown(ctx)
        else:
            try:
                await ctx.message.delete()
            except:
                await ctx.send('missing manage_messages permission', delete_after=5)
                ctx.command.reset_cooldown(ctx)
                return


        # Actual copying and pasting


        history = []
        async for message in ctx.channel.history(limit = amount):
            history.append(message)
            await asyncio.sleep(0.001)
        history.reverse()

        try:
            webhook = await channel.create_webhook(name = "DB-Move", reason = "created webhook for move command")
        except:
            await ctx.send(f"i'm missing manage_webhooks permission in {channel.mention}",delete_after=5)
            ctx.command.reset_cooldown(ctx)
            return
        await ctx.channel.purge(limit = amount)

        for message in history:
            if message.attachments:
                file = ctx.message.attachments[0]
                myfile = await file.to_file()
                if message.embeds:
                    embed = message.embeds[0]
                    await webhook.send(username = message.author.display_name, avatar_url = message.author.avatar.url, file = myfile, content = message.content, embed=embed)
                else:
                    await webhook.send(username = message.author.display_name, avatar_url = message.author.avatar.url, file = myfile, content = message.content)
            else:
                if message.embeds:
                    embed = message.embeds[0]
                    await webhook.send(username = message.author.display_name, avatar_url = message.author.avatar.url, content = message.content, embed=embed)
                else:
                    await webhook.send(username = message.author.display_name, avatar_url = message.author.avatar.url, content = message.content)
            await asyncio.sleep(0.5)

        await webhook.delete()
        await ctx.send(f'moved {amount} messages to {channel.mention}')


def setup(bot):
    bot.add_cog(test(bot))
