import discord
import typing
from discord.ext import commands

from DuckBot.__main__ import DuckBot
from DuckBot.helpers.context import CustomContext
from asyncdagpi import ImageFeatures as dtype


async def setup(bot):
    await bot.add_cog(ImageMan(bot))


class ImageMan(commands.Cog, name="Image"):
    """
    📸 Commands to alter user's avatars in funny ways.
    """

    def __init__(self, bot):
        self.bot: DuckBot = bot
        self.select_emoji = "📸"
        self.select_brief = "Image Manipulation Commands"

    @commands.command()
    async def pixelate(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
        pixel_size: typing.Optional[int] = 8,
    ):
        """Pixelates a member's avatar."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.mosiac(), pixels=pixel_size)
        embed = discord.Embed(color=member.color, title=f"Pixelated {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def colors(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Shows the top dominant colors of a member's avatar."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.colors())
        embed = discord.Embed(color=member.color, title=f"Top Colors of {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def america(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Adds a waving USA flag to a member's avatar."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.america())
        embed = discord.Embed(color=member.color, title=f"USA Flag of {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def communism(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Adds a waving Communist flag to a member's avatar."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.communism())
        embed = discord.Embed(color=member.color, title=f"Communism  Flag of {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def triggered(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Triggers a member."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.triggered())
        embed = discord.Embed(color=member.color, title=f"Triggered {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def expand(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Reveals the user from behind a circle."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.expand())
        embed = discord.Embed(color=member.color, title=f"Expanded {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def wasted(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Kills a member in GTA."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.wasted())
        embed = discord.Embed(color=member.color, title=f"Wasted {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def sketch(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Adds a sketch filter to the member's avatar."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.sketch())
        embed = discord.Embed(color=member.color, title=f"Sketched {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def spin(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Makes a member go spin."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.spin())
        embed = discord.Embed(color=member.color, title=f"Spinning {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def pet(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Pets a member."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.petpet())
        embed = discord.Embed(color=member.color, title=f"Petpet {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def bonk(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Bonks a member."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.bonk())
        embed = discord.Embed(color=member.color, title=f"Bonked {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def bomb(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Makes a member explode."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.bomb())
        embed = discord.Embed(color=member.color, title=f"Boom {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def dissolve(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Makes a member disappear."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.dissolve(), transparent=0)
        embed = discord.Embed(color=member.color, title=f"Dissolved {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def invert(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Inverts the colors of a member's avatar."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.invert())
        embed = discord.Embed(color=member.color, title=f"Inverted {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def sobel(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Adds a sobel filter to a member's avatar."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.sobel())
        embed = discord.Embed(color=member.color, title=f"Sobeled {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def hog(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Creates a Histogram of Oriented Gradients from a member's avatar."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.hog())
        embed = discord.Embed(color=member.color, title=f"Hogged {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def polygon(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Shows the polygons of a member's avatar."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.triangle())
        embed = discord.Embed(color=member.color, title=f"Polygoned {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def blur(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Blurs out a member's avatar."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.blur())
        embed = discord.Embed(color=member.color, title=f"Blurred {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def rgb(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Shows the RGB intensity for a member's avatar."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.rgb())
        embed = discord.Embed(color=member.color, title=f"RGBed {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command(name="delete?")
    async def delete_(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Should you delete a member?"""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.delete())
        embed = discord.Embed(color=member.color, title=f"Deleted {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def fedora(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """\*tips fedora\*"""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.fedora())
        embed = discord.Embed(color=member.color, title=f"Fedoraed {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def hitler(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Worse than Hitler?"""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.hitler())
        embed = discord.Embed(color=member.color, title=f"Top Text {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        embed.set_footer(text="bottom text")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def lego(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Turns a user's avatar into a lego-style image."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.lego())
        embed = discord.Embed(color=member.color, title=f"Legoed {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def wanted(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Makes a wanted poster from a member's avatar."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.wanted())
        embed = discord.Embed(color=member.color, title=f"Wanted Poster {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def strings(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Turns a user's avatar into strings."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.stringify())
        embed = discord.Embed(color=member.color, title=f"Stringified {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def thermal(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Shows a thermal-camera styled image off a member's avatar."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.burn())
        embed = discord.Embed(color=member.color, title=f"Thermal {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def freeze(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Freezes a member."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.freeze())
        embed = discord.Embed(color=member.color, title=f"Froze {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def earth(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """The green and blue of the earth..."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.earth())
        embed = discord.Embed(color=member.color, title=f"Earth {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def jail(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Puts a user in jail."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.jail())
        embed = discord.Embed(color=member.color, title=f"Jailed {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def shatter(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Shatters a member."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.shatter())
        embed = discord.Embed(color=member.color, title=f"Shattered {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    flags = typing.Literal[
        "Asexual",
        "Bisexual",
        "Gay",
        "Genderfluid",
        "Genderqueer",
        "Intersex",
        "Lesbian",
        "Nonbinary",
        "Progress",
        "Pan",
        "Trans",
        "asexual",
        "bisexual",
        "gay",
        "genderfluid",
        "genderqueer",
        "intersex",
        "lesbian",
        "nonbinary",
        "progress",
        "pan",
        "trans",
    ]

    @commands.command(usage="[member] [flag-style]")
    async def gay(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
        flag: typing.Optional[flags] = "gay",
    ):
        """Puts a pride flag in front of the member's avatar.

        Can be any of the following flags:
        `Asexual`, `Bisexual`, `Gay`, `Genderfluid`,
        `Genderqueer`, `Intersex`, `Lesbian`,
        `Nonbinary`, `Progress`, `Pan`, `Trans`
        _defaults to the Gay flag._
        """
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.pride(), flag=flag.lower())
        embed = discord.Embed(color=member.color, title=f"Applied {flag} flag to {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def trash(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Takes out the trash."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.trash())
        embed = discord.Embed(color=member.color, title=f"Trashed {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def deepfry(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Deep fries a user."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.deepfry())
        embed = discord.Embed(color=member.color, title=f"Deepfried {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def ascii(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """*(#@$#%>#%$@%}{:">?$@%@#%$*)@#($."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.ascii())
        embed = discord.Embed(color=member.color, title=f"ASCII-ified {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def charcoal(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Applies a charcoal filter to a user's avatar."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.charcoal())
        embed = discord.Embed(color=member.color, title=f"Charcoal-ified {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def poster(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Posterizes an image."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.poster())
        embed = discord.Embed(color=member.color, title=f"Posterized {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def sepia(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Adds a sepia filter to an image."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.sepia())
        embed = discord.Embed(color=member.color, title=f"Sepia-ified {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def swirl(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Swirls a member's avatar."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.swirl())
        embed = discord.Embed(color=member.color, title=f"Swirled {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")

    @commands.command()
    async def paint(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Adds a painted effect to a member's avatar."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.paint())
        embed = discord.Embed(color=member.color, title=f"Painted {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def night(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """De-saturates a member's avatar."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.night())
        embed = discord.Embed(color=member.color, title=f"Night-ified {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def rainbow(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Adds a rainbow effect to an image."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.rainbow())
        embed = discord.Embed(color=member.color, title=f"Rainbow-ified {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command()
    async def magik(
        self,
        ctx: CustomContext,
        member: typing.Optional[typing.Union[discord.Member, discord.User]],
    ):
        """Magiks an image."""
        member = member or ctx.referenced_user or ctx.author
        file = await ctx.dagpi(member, feature=dtype.magik())
        embed = discord.Embed(color=member.color, title=f"Magik-ified {member.display_name}")
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(file=file, embed=embed)

    @commands.command(name="5g1g")
    async def _g_g(
        self,
        ctx: CustomContext,
        guys: typing.Union[discord.Member, discord.User],
        girl: typing.Union[discord.Member, discord.User],
    ):
        """Five guys one girl meme."""
        file = await ctx.dagpi(guys, feature=dtype.five_guys_one_girl(), url2=girl.display_avatar.url)
        embed = discord.Embed(color=guys.color)
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(embed=embed, file=file)

    @commands.command(name="wayg", aliases=["why-are-you-gay", "why-gay"])
    async def why_are_g(
        self,
        ctx: CustomContext,
        interviewer: typing.Union[discord.Member, discord.User],
        person: typing.Union[discord.Member, discord.User],
    ):
        """Why are you gay meme."""
        file = await ctx.dagpi(interviewer, feature=dtype.why_are_you_gay(), url2=person.display_avatar.url)
        embed = discord.Embed(
            color=interviewer.color,
        )
        embed.set_image(url=f"attachment://{file.filename}")
        await ctx.send(embed=embed, file=file)
