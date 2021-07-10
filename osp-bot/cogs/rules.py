import discord, asyncio, typing, re, yaml, datetime, json, aiohttp
from discord.ext import commands

class help(commands.Cog):

    @commands.command()
    @commands.guild_only()
    async def rule(self, ctx, number: typing.Optional[int]):
        if number == None:
            await ctx.send(
embed = discord.Embed(color = 0x0066ff, description=
"""
Command Usage:
.rules [rule_number]
(example: .rule 4)
""")
)

        elif number == 1:
            await ctx.send(
embed = discord.Embed(color = 0x0066ff, description=
"""
**More info on Rule #1**
*(Per Discord terms, you must be 13 or older to be in this server)*
**¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤**
The Discord [Terms Of Service](https://discord.com/terms) states that you must be 13 years of age or older:

"*Welcome to Discord! These Terms of Service (“Terms”), which include and hereby incorporate the Privacy Policy at https://discord.com/privacy (“Privacy Policy”), are a legal agreement between Discord Inc. and its related companies (the “Company,” “us,” “our,” or "we") and you ("you" or “your”). By using or accessing the Discord application (the “App”) or the website located at https://discord.com (the "Site"), which are collectively referred to as the “Service,” you agree (i) that you are 13 years of age and the minimum age of digital consent in your country, (ii) if you are the age of majority in your jurisdiction or over, that you have read, understood, and accept to be bound by the Terms, and (iii) if you are between 13 (or the minimum age of digital consent, as applicable) and the age of majority in your jurisdiction, that your legal guardian has reviewed and agrees to these Terms.*"
""")
)

        elif number == 2:
            await ctx.send(
embed = discord.Embed(color = 0x0066ff, description=
"""
**More info on Rule #2**
*(You may not use an alt/secondary account of any kind, especially for evasion of punishments)*
**¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤**
You may only have one account on the server at a time. You may not **under any circumstances** join on another account if you are muted, warned, or have any other actions taken against you. This will result in a permanent ban against you.
""")
)

        elif number == 3:
            await ctx.send(
embed = discord.Embed(color = 0x0066ff, description=
"""
**More info on Rule #3**
*(Listen to the staff; DM me (<@860628692082491392>) if there is a major problem)*
**¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤**
You may also contact the staff by DM'ing them, but the most efficient way would be by DMing me, since that gets sent to the whole team. You may only ping the *OSP Admin Team* role if it's something that needs to be taken care of ASAP.

Otherwise, send me (<@860628692082491392>) a message and an admin will get back to you shortly.
""")
)

        elif number == 4:
            await ctx.send(
embed = discord.Embed(color = 0x0066ff, description=
"""
**More info on Rule #4**
*(Try not to find loopholes to justify bad behavior [Use common sense])*
**¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤**
The server rules list can never be completely exhaustive - any common sense rules also apply, as well as a common sense understanding of the listed rules.
""")
)

        elif number == 5:
            await ctx.send(
embed = discord.Embed(color = 0x0066ff, description=
"""
**More info on Rule #5**
*(Spamming messages or images is not allowed)*
**¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤**
This includes sending the same content repeatedly, or just sending many messages in a short time period.
""")
)

        elif number == 6:
            await ctx.send(
embed = discord.Embed(color = 0x0066ff, description=
"""
**More info on Rule #6**
*(No NSFW or use of slurs, regardless of context)*
**¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤**
This will almost always result in a ban.
""")
)

        elif number == 7:
            await ctx.send(
embed = discord.Embed(color = 0x0066ff, description=
"""
**More info on Rule #7**
*(Never post personal information. This includes information such as full name, address, etc.)*
**¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤**
You should always be careful posting any information that someone can use to identify you. Remember, this is a public server, so anyone who joins has access to anything you post here.
""")
)

        elif number == 8:
            await ctx.send(
embed = discord.Embed(color = 0x0066ff, description=
"""
**More info on Rule #8**
*(Make sure to direct content to their appropriate channels [e.g. bot use in #commands])*
**¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤**
If you send messages that don't belong in a channel, you will simply be asked to move to the appropriate channel. Most channels are named in a way that you can easily identify their purpose!
""")
)

        elif number == 9:
            await ctx.send(
embed = discord.Embed(color = 0x0066ff, description=
"""
**More info on Rule #9**
*(No advertising other Discord servers without explicit permission from <@326147079275675651>)*
**¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤**
This especially applies to large servers, but also even to small, personal ones. (If you find friends on the server and want to invite them to a friend group, just DM them!)
""")
)

        elif number == 10:
            await ctx.send(
embed = discord.Embed(color = 0x0066ff, description=
"""
**More info on Rule #10**
*(To contact our Admin Team, please only message me (<@860628692082491392>))*
**¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤**
You may also contact the staff by DM'ing them, but the most efficient way would be by DMing me, since that gets sent to the whole team. You may only ping the *OSP Admin Team* role if it's something that needs to be taken care of ASAP.

Otherwise, send me (<@860628692082491392>) a message and an admin will get back to you shortly.
""")
)

        elif number == 11:
            await ctx.send(
embed = discord.Embed(color = 0x0066ff, description=
"""
**More info on Rule #11**
*(Respect everyone)*
**¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤**
This applies even if you don't like someone; this is not the place for expressing that.
""")
)

        elif number == 12:
            await ctx.send(
embed = discord.Embed(color = 0x0066ff, description=
"""
**More info on Rule #12**
*(Do not make others feel uncomfortable)*
**¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤**
If someone directly asks you to stop talking about something because it makes them uncomfortable, please do.
""")
)

        elif number == 13:
            await ctx.send(
embed = discord.Embed(color = 0x0066ff, description=
"""
**More info on Rule #13**
*(Do not cause public drama)*
**¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤**
Whether it is drama from other servers or from this one, this is not the place to discuss it.
""")
)

        elif number == 14:
            await ctx.send(

embed = discord.Embed(color = 0x0066ff, description=
"""
**More info on Rule #14**
*(Publicly posting negative statements about other members on social media or other servers is strictly prohibited. If you see this type of targeted harassment happen, please report it to me (<@860628692082491392>) or a staff member.)*
**¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤**
This mainly applies to social media sites (Twitter, Instagram, etc.) or other Discord servers. If you see this type of targeted harassment happen, please report it to me (<@860628692082491392>) and we will try and get it under control.
""")
)

        elif number == 15:
            await ctx.send(

embed = discord.Embed(color = 0x0066ff, description=
"""
**More info on Rule #15**
*(Racism, sexism, transphobia, homophobia, FASCISM, or any other prejudice behavior is taken very seriously on this server.)*
**¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤**
Respect for other people has nothing to do with politics or opinion, and those who break this rule will be banned.
""")
)

        elif number == 69:
            await ctx.send(

embed = discord.Embed(color = 0x0066ff, description=
"""
**Nice.**
""")
)

        elif number == 420:
            await ctx.send(

embed = discord.Embed(color = 0x0066ff, description=
"""
**BLAZE IT**
""")
)

        elif number == 34:
            await ctx.send(

embed = discord.Embed(color = 0x0066ff, description=
"""
**No.**
""")
)

        elif number == 143:
            await ctx.send(

embed = discord.Embed(color = 0x0066ff, description=
"""
**Love you too :heart:**
""")
)

    # CAT ERROR CODES STUFF
        else:
            async with aiohttp.ClientSession() as cs:
                async with cs.get(f"https://http.cat/{number}") as cs:
                    if cs.status == 404 and number !=404:
                        await ctx.send(embed = discord.Embed(color = 0xeb4034, description= f"""
**¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤**
**ERROR**:
Rule {number} not found. Please only use numbers 1-15.
**¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤°¤━━━¤**
"""))
                    else:
                        embed = discord.Embed(color = 0xeb4034)
                        embed.set_image(url=f"https://http.cat/{number}")
                        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(help(bot))


# TEMPLATE WITH IMAGE(REMOVE # SIGNS)

#        elif number == 99:
#            discord.Embed(color = 0x0066ff,
#            description=
#"""
#YOUR TEXT HERE
#            """)
#            embed.set_image(url="image.link/hi")
#            await ctx.send(embed = embed)
