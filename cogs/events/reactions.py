import re

import discord
from discord.ext import commands

from DuckBot.cogs.info import suggestions_channel
from ._base import EventsBase


class ReactionHandling(EventsBase):

    @commands.Cog.listener('on_raw_reaction_add')
    async def wastebasket(self, payload: discord.RawReactionActionEvent):
        if payload.channel_id == self.error_channel and await \
                self.bot.is_owner(payload.member) and str(payload.emoji == '🗑'):
            message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
            if not message.author == self.bot.user:
                return
            error = '```py\n' + '\n'.join(message.content.split('\n')[7:])
            await message.edit(content=f"{error}```fix\n✅ Marked as fixed by the developers.```")
            await message.clear_reactions()

        if payload.channel_id == suggestions_channel and await \
                self.bot.is_owner(payload.member) and str(payload.emoji) in ('🔼', '🔽'):

            message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
            if not message.author.bot or not message.embeds:
                return
            embed = message.embeds[0]

            sub = {
                'Suggestion ': 'suggestion',
                'suggestion ': 'suggestion',
                'Denied ': '',
                'Approved ': ''
            }

            if self.bot.user.id != 788278464474120202:
                return

            pattern = '|'.join(sorted(re.escape(k) for k in sub))
            title = re.sub(pattern, lambda m: sub.get(m.group(0).upper()), embed.title, flags=re.IGNORECASE)

            scheme = {
                '🔼': (0x6aed64, f'Approved suggestion {title}'),
                '🔽': (0xf25050, f'Denied suggestion {title}')
            }[str(payload.emoji)]

            embed.title = scheme[1]
            embed.colour = scheme[0]
            # noinspection PyBroadException
            try:
                user_id = int(embed.footer.text.replace("Sender ID: ", ""))
            except:
                user_id = None
            suggestion = embed.description

            if str(payload.emoji) == '🔼' and user_id:
                try:
                    user = (self.bot.get_user(user_id) or (await self.bot.fetch_user(user_id)))
                    user_embed = discord.Embed(title="🎉 Suggestion approved! 🎉",
                                               description=f"**Your suggestion has been approved! "
                                                           f"You suggested:**\n{suggestion}")
                    user_embed.set_footer(text='Reply to this DM if you want to stay in contact '
                                               'with us while we work on your suggestion!')
                    await user.send(embed=user_embed)
                    embed.set_footer(text=f"DM sent - ✅ - {user_id}")
                except (discord.Forbidden, discord.HTTPException):
                    embed.set_footer(text=f"DM sent - ❌ - {user_id}")
            else:
                embed.set_footer(text='Suggestion denied. No DM sent.')

            await message.edit(embed=embed)
            await message.clear_reactions()
