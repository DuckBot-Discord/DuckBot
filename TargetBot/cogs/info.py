import json, random, typing, discord, asyncio
from discord.ext import commands

class info(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases = ['help'])
    async def guide(self, ctx):
        embed=discord.Embed(title="Please follow the guide!", description="To make sure that your resource pack is set up correctly, please follow [this guide](https://www.stylizedresourcepack.com/guide). Make sure to enable POM (parallax occlusion mapping) to get the 3D effect", color=ctx.me.color)
        embed.add_field(name="Which shaders does the guide cover?", value="The goes in depth into settings for [BSL shaders](https://bitslablab.com/bslshaders/#download) and [SEUS renewed](https://sonicether.com/shaders/download/renewed-v1-0-1/) shaders.", inline=False)
        embed.add_field(name="Help! I have square artifacts on my blocks.", value="For SEUS renewed, make sure to set the parallax resolution correctly to avoid the blocks having artifacts that look like a grid.", inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases = ['jvm', 'moreram'])
    async def ram(self, ctx):
        embed=discord.Embed(title="", description="**[How to allocate more ram](https://www.online-tech-tips.com/gaming/how-to-allocate-more-ram-to-minecraft/)** (keep it between 6-8GB)", color=ctx.me.color)
        await ctx.send(embed=embed)

    @commands.command(aliases = ['shaders'])
    async def links(self, ctx):
        embed=discord.Embed(title="", description="**download links for: [optifine](https://optifine.net/downloads), [BSL shaders](https://bitslablab.com/bslshaders/#download) and [SEUS renewed shaders](https://www.sonicether.com/seus/#downloads)**", color=ctx.me.color)
        await ctx.send(embed=embed)

    @commands.command()
    async def bsl(self, ctx):
        embed=discord.Embed(title="", description="**[download BSL shaders](https://bitslablab.com/bslshaders/#download)** \n **[BitsLab discord server](https://discord.com/invite/ZJd7jjA)**", color=ctx.me.color)
        await ctx.send(embed=embed)

    @commands.command()
    async def seus(self, ctx):
        embed=discord.Embed(title="", description="**[download SEUS renewed shaders](https://www.sonicether.com/seus/#downloads)**", color=ctx.me.color)
        await ctx.send(embed=embed)

    @commands.command(aliases = ['of'])
    async def optifine(self, ctx):
        embed=discord.Embed(title="", description="**[download optifine](https://optifine.net/downloads)** \n **[optifine's discord](https://optifine.net/discord)**", color=ctx.me.color)
        await ctx.send(embed=embed)

    @commands.command(aliases = ['download', 'dchannel'])
    async def downloads(self, ctx):
        embed=discord.Embed(title="", description="""To access the download channel you need to have a role <@&717144765690282015> or higher, and you don't appear to have it.
If you already purchased a <@&717144765690282015> or higher subscription, link your discord to patreon. Check [this article](https://support.patreon.com/hc/en-us/articles/212052266-Get-my-Discord-role#:~:text=Step%201%3A%20Log%20in%20to,role%20tied%20to%20your%20Tier!) for more info.
In case that your discord is already linked, un-link and re-link it.
If you don't already have a <@&717144765690282015> or higher subscription, you can get one here: [patreon.com/stylized](https://www.patreon.com/Stylized).""", color=ctx.me.color)
        await ctx.send(embed=embed)

    @commands.command()
    async def radeon(self, ctx):
        embed=discord.Embed(title="", description="""**__Regarding shaders and AMD Radeon Drivers__**
Certain AMD driver versions are known to cause crashes when using certain shaders. Your mileage may vary with these driver versions.
I have tested every version since 20.4.2 up to 21.2.3, and the latest reliable/stable driver with shaders is 20.4.2. All later versions are known to cause crashes.
I have also tested Radeon Pro drivers 20.Q3 and 20.Q4 and neither are stable.
*To receive support from shader developers and other members of the community, please use Radeon Driver version 20.4.2*, available from the link at the bottom of this message.

__Regarding Continuum RT and SEUS PTGI__
**Continuum RT** and **SEUS PTGI HRR2** both need newer versions of the driver to correctly function. I recommend **20.11.2**. For these shaders, try this driver version if the above doesn't work.

You may have some success with later drivers, but **if you face problems you must downgrade to 20.4.2 before you'll be helped.**
This applies to any AMD GPU supported by their drivers, starting with the Radeon HD 7700-7900 Series through to the RX 6000 series released in November 2020.
I have a Radeon RX 5700 XT, on a B450 Motherboard with a 3700X
**Download link: https://www.amd.com/en/support/kb/release-notes/rn-rad-win-20-4-2**

*psst, if you want to use a later driver, like if you want to run CRT or HRR2, if you have a shaderpack that crashes, switch to `internal` shaders before loading it. This has to be done every time you load it, so F3 + R (to reload shader) will still crash*
Also, starting with 21.2.3, some packs will refuse to load, such as Chocapic V9, while others have improved stability.""", color=ctx.me.color)
        embed.set_author(name="Copied straight from optifine's support channel", icon_url="https://i.imgur.com/uZsxgEf.png")
        await ctx.send(embed=embed)

    @commands.command(aliases = ['oldversions', '1.12'])
    async def unsupported(self, ctx):
        embed=discord.Embed(title="Can i use this pack with an older version of minecraft?", description="""You technically can, but this pack is only made for versions that are 1.13 and higher.
Older versions of minecraft use a different file structure for their resource packs and/or different names for some of the textures.
There seems to be some conversion tools out there that can change a texture pack to work in one of these older versions of the game but this is not supported by us, and you will not recieve the same support that you would get using a newer version of minecraft.
Another way is, if you have the time, changing it manually to the old file structure.""", color=ctx.me.color)
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(info(bot))
