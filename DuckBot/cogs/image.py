# basic dependencies
import discord
from discord.ext import commands

# aiohttp should be installed if discord.py is
import aiohttp

# PIL can be installed through
# `pip install -U Pillow`
from PIL import Image, ImageDraw

# partial lets us prepare a new function with args for run_in_executor
from functools import partial

# BytesIO allows us to convert bytes into a file-like byte stream.
from io import BytesIO

# this just allows for nice function annotation, and stops my IDE from complaining.
from typing import Union

class ImageCog(commands.Cog):
    def __init__(self, bot: commands.Bot):

        # we need to include a reference to the bot here so we can access its loop later.
        self.bot = bot

        # create a ClientSession to be used for downloading avatars
        self.session = aiohttp.ClientSession(loop=bot.loop)


    async def get_avatar(self, user: Union[discord.User, discord.Member]) -> bytes:

        # generally an avatar will be 1024x1024, but we shouldn't rely on this
        avatar_url = user.avatar_url_as(format="png")

        async with self.session.get(avatar_url) as response:
            # this gives us our response object, and now we can read the bytes from it.
            avatar_bytes = await response.read()

        return avatar_bytes

    @staticmethod
    def processing(avatar_bytes: bytes, colour: tuple) -> BytesIO:

        # we must use BytesIO to load the image here as PIL expects a stream instead of
        # just raw bytes.
        with Image.open(BytesIO(avatar_bytes)) as im:

            # this creates a new image the same size as the user's avatar, with the
            # background colour being the user's colour.
            with Image.new("RGB", im.size, colour) as background:

                # this ensures that the user's avatar lacks an alpha channel, as we're
                # going to be substituting our own here.
                rgb_avatar = im.convert("RGB")

                # this is the mask image we will be using to create the circle cutout
                # effect on the avatar.
                with Image.new("L", im.size, 0) as mask:

                    # ImageDraw lets us draw on the image, in this instance, we will be
                    # using it to draw a white circle on the mask image.
                    mask_draw = ImageDraw.Draw(mask)

                    # draw the white circle from 0, 0 to the bottom right corner of the image
                    mask_draw.ellipse([(0, 0), im.size], fill=255)

                    # paste the alpha-less avatar on the background using the new circle mask
                    # we just created.
                    background.paste(rgb_avatar, (0, 0), mask=mask)

                # prepare the stream to save this image into
                final_buffer = BytesIO()

                # save into the stream, using png format.
                background.save(final_buffer, "png")

        # seek back to the start of the stream
        final_buffer.seek(0)

        return final_buffer

    @commands.command()
    async def circle(self, ctx, *, member: discord.Member = None):
        """Display the user's avatar on their colour."""

        # this means that if the user does not supply a member, it will default to the
        # author of the message.
        member = member or ctx.author

        async with ctx.typing():
            # this means the bot will type while it is processing and uploading the image

            if isinstance(member, discord.Member):
                # get the user's colour, pretty self explanatory
                member_colour = member.colour.to_rgb()
            else:
                # if this is in a DM or something went seriously wrong
                member_colour = (0, 0, 0)

            # grab the user's avatar as bytes
            avatar_bytes = await self.get_avatar(member)

            # create partial function so we don't have to stack the args in run_in_executor
            fn = partial(self.processing, avatar_bytes, member_colour)

            # this runs our processing in an executor, stopping it from blocking the thread loop.
            # as we already seeked back the buffer in the other thread, we're good to go
            final_buffer = await self.bot.loop.run_in_executor(None, fn)

            # prepare the file
            file = discord.File(filename="circle.png", fp=final_buffer)

            # send it
            await ctx.send(file=file)


# setup function so this can be loaded as an extension
def setup(bot: commands.Bot):
    bot.add_cog(ImageCog(bot))
