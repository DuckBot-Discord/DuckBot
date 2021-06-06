import typing, discord, asyncio, random, datetime
from discord.ext import commands, tasks, timers
import datetime

class test(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # all the emoji are from the bots.gg discord server.
    # If your bot is in there, it'll be able to use them
    def get_user_badges(self, user):
        author_flags = user.public_flags
        flags = dict(author_flags)
        emoji_flags = ""
        if flags['staff'] is True:
            emoji_flags = f"{emoji_flags} <:staff:314068430787706880>"
        if flags['partner'] is True:
            emoji_flags = f"{emoji_flags} <:partnernew:754032603081998336>"
        if flags['hypesquad'] is True:
            emoji_flags = f"{emoji_flags} <:hypesquad:314068430854684672>"
        if flags['bug_hunter'] is True:
            emoji_flags = f"{emoji_flags} <:bughunter:585765206769139723>"
        if flags['hypesquad_bravery'] is True:
            emoji_flags = f"{emoji_flags} <:bravery:585763004218343426>"
        if flags['hypesquad_brilliance'] is True:
            emoji_flags = f"{emoji_flags} <:brilliance:585763004495298575>"
        if flags['hypesquad_balance'] is True:
            emoji_flags = f"{emoji_flags} <:balance:585763004574859273>"
        if flags['early_supporter'] is True:
            emoji_flags = f"{emoji_flags} <:supporter:585763690868113455>"
        if flags['bug_hunter_level_2'] is True:
            emoji_flags = f"{emoji_flags} <:bughunter_gold:850843414953984041>" #not from bots.gg
        if flags['verified_bot_developer'] is True:
            emoji_flags = f"{emoji_flags} <:earlybotdev:850843591756349450>" #not from bots.gg
        if emoji_flags == "": emoji_flags = None
        return emoji_flags

    @commands.command()
    async def uinfo(self, ctx, user: typing.Optional[discord.Member]):

        if not user: user = ctx.author

        badges = self.get_user_badges(user)
        if badges: badges = f"\n<:store_tag:658538492409806849>**Badges:** {badges}"
        else: badges = ''

        userid = f"\n<:greyTick:596576672900186113>**ID:** {user.id}"

        if user.nick: nick = f"\n<:nickname:850914031953903626>**Nickname:** {user.nick}"
        else: nick = ""

        date = user.joined_at.strftime("%b %-d %Y at %-H:%M")
        if user.joined_at: joined = f"\n<:joined:849392863557189633>**joined:** {date} UTC"
        else: joined = ""

        date = user.created_at.strftime("%b %-d %Y at %-H:%M")
        created = f"\n<:invite:658538493949116428>**Created:** {date} UTC"

        roles = ""
        for role in user.roles:
            if role is ctx.guild.default_role: continue
            roles = f"{roles} {role.mention}"
        if roles is not "":
            roles = f"\n<:role:808826577785716756>**roles:** {roles}"


        embed = discord.Embed(color=ctx.me.color, description=f"{badges}{userid}{nick}{joined}{created}{roles}")
        embed.set_author(name=user, icon_url=user.avatar_url)
        embed.set_thumbnail(url=user.avatar_url)

        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(test(bot))
