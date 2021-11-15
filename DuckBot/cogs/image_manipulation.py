import discord
import typing
from discord.ext import commands

from DuckBot.__main__ import DuckBot
from DuckBot.helpers.context import CustomContext
from asyncdagpi import ImageFeatures as dtype


def setup(bot):
    bot.add_cog(ImageMan(bot))


class ImageMan(commands.Cog, name='Image'):
    """
    📸 Commands to alter user's avatars in funny ways.
    """

    def __init__(self, bot):
        self.bot: DuckBot = bot
        self.select_emoji = '📸'
        self.select_brief = 'Image Manipulation Commands'

    @commands.command()
    async def pixelate(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]], pixel_size: typing.Optional[int] = 8):
        """ Pixelates a member's avatar. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.mosiac(), pixels=pixel_size))

    @commands.command()
    async def colors(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Shows the top dominant colors of a member's avatar. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.colors()))

    @commands.command()
    async def america(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Adds a waving USA flag to a member's avatar. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.america()))

    @commands.command()
    async def communism(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Adds a waving Communist flag to a member's avatar. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.communism()))

    @commands.command()
    async def triggered(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Triggers a member. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.triggered()))

    @commands.command()
    async def expand(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Reveals the user from behind a circle. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.expand()))

    @commands.command()
    async def wasted(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Kills a member in GTA. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.wasted()))

    @commands.command()
    async def sketch(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Adds a sketch filter to the member's avatar. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.sketch()))

    @commands.command()
    async def spin(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Makes a member go spin. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.spin()))

    @commands.command()
    async def pet(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Pets a member. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.petpet()))

    @commands.command()
    async def bonk(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Bonks a member. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.bonk()))

    @commands.command()
    async def bomb(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Makes a member explode. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.bomb()))

    @commands.command()
    async def dissolve(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Makes a member disappear. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.dissolve(), transparent=0))

    @commands.command()
    async def invert(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Inverts the colors of a member's avatar. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.invert()))

    @commands.command()
    async def sobel(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Adds a sobel filter to a member's avatar. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.sobel()))

    @commands.command()
    async def hog(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Creates a Histogram of Oriented Gradients from a member's avatar. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.hog()))

    @commands.command()
    async def polygon(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Shows the polygons of a member's avatar. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.triangle()))

    @commands.command()
    async def blur(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Blurs out a member's avatar. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.blur()))

    @commands.command()
    async def rgb(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Shows the RGB intensity for a member's avatar. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.rgb()))

    @commands.command(name='delete?')
    async def delete_(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Should you delete a member? """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.delete()))

    @commands.command()
    async def fedora(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ \*tips fedora\* """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.fedora()))

    @commands.command()
    async def hitler(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Worse than Hitler? """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.hitler()))

    @commands.command()
    async def lego(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Turns a user's avatar into a lego-style image. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.lego()))

    @commands.command()
    async def wanted(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Makes a wanted poster from a member's avatar. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.wanted()))

    @commands.command()
    async def strings(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Turns a user's avatar into strings. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.stringify()))

    @commands.command()
    async def thermal(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Shows a thermal-camera styled image off a member's avatar. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.burn()))

    @commands.command()
    async def freeze(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Freezes a member. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.freeze()))

    @commands.command()
    async def earth(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ The green and blue of the earth... """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.earth()))

    @commands.command()
    async def jail(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Puts a user in jail. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.jail()))

    @commands.command()
    async def shatter(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Shatters a member. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.shatter()))

    flags = typing.Literal['Asexual', 'Bisexual', 'Gay', 'Genderfluid', 'Genderqueer', 'Intersex', 'Lesbian', 'Nonbinary', 'Progress', 'Pan', 'Trans',
                           'asexual', 'bisexual', 'gay', 'genderfluid', 'genderqueer', 'intersex', 'lesbian', 'nonbinary', 'progress', 'pan', 'trans']

    @commands.command(usage="[member] [flag-style]")
    async def gay(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]], flag: typing.Optional[flags] = 'gay'):
        """ Puts a pride flag in front of the member's avatar.

        Can be any of the following flags:
        `Asexual`, `Bisexual`, `Gay`, `Genderfluid`,
        `Genderqueer`, `Intersex`, `Lesbian`,
        `Nonbinary`, `Progress`, `Pan`, `Trans`
        _defaults to the Gay flag._
        """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.pride(), flag=flag.lower()))

    @commands.command()
    async def trash(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Takes out the trash. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.trash()))

    @commands.command()
    async def deepfry(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Deep fries a user. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.deepfry()))

    @commands.command()
    async def ascii(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ *(#@$#%>#%$@%}{:">?$@%@#%$*)@#($. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.ascii()))

    @commands.command()
    async def charcoal(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Applies a charcoal filter to a user's avatar. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.charcoal()))

    @commands.command()
    async def poster(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Posterizes an image. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.poster()))

    @commands.command()
    async def sepia(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Adds a sepia filter to an image. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.sepia()))

    @commands.command()
    async def swirl(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Swirls a member's avatar. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.swirl()))

    @commands.command()
    async def paint(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Adds a painted effect to a member's avatar. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.paint()))

    @commands.command()
    async def night(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ De-saturates a member's avatar. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.night()))

    @commands.command()
    async def rainbow(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Adds a rainbow effect to an image. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.rainbow()))

    @commands.command()
    async def magik(self, ctx: CustomContext, member: typing.Optional[typing.Union[discord.Member, discord.User]]):
        """ Magiks an image. """
        await ctx.send(file=await ctx.dagpi(member, feature=dtype.magik()))

    @commands.command(name='5g1g')
    async def _g_g(self, ctx: CustomContext, guys: typing.Union[discord.Member, discord.User], girl: typing.Union[discord.Member, discord.User]):
        """ Five guys one girl meme. """
        await ctx.send(file=await ctx.dagpi(guys, feature=dtype.five_guys_one_girl(), url2=girl.display_avatar.url))

    @commands.command(name='wayg', aliases=['why-are-you-gay', 'why-gay'])
    async def why_are_g(self, ctx: CustomContext, interviewer: typing.Union[discord.Member, discord.User], person: typing.Union[discord.Member, discord.User]):
        """ Why are you gay meme. """
        await ctx.send(file=await ctx.dagpi(interviewer, feature=dtype.why_are_you_gay(), url2=person.display_avatar.url))

