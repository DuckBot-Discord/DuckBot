import asyncio
import contextlib
import inspect
import logging
import random
import re
import traceback
import typing
import urllib.parse

import aiowiki
import discord
from async_timeout import timeout
from discord.ext import commands

from DuckBot import errors
from DuckBot.__main__ import DuckBot, CustomContext
from DuckBot.helpers import constants
from DuckBot.helpers.paginator import ViewPaginator, UrbanPageSource
from DuckBot.helpers.rock_paper_scissors import RockPaperScissors, RequestToPlayView
from DuckBot.helpers.tictactoe import LookingToPlay, TicTacToe

_8ball_good = ['It is certain',
               'It is decidedly so',
               'Without a doubt',
               'Yes - definitely',
               'You may rely on it',
               'As I see it, yes',
               'Most likely',
               'Outlook good',
               'Yes',
               'Signs point to yes']

_8ball_meh = ['Reply hazy, try again',
              'Ask again later',
              'Better not tell you now',
              'Cannot predict now',
              'Concentrate and ask again']

_8ball_bad = ['Don\'t count on it',
              'My reply is no',
              'My sources say no',
              'Outlook not so good',
              'Very doubtful']

_8ball_answers = _8ball_good + _8ball_meh + _8ball_bad


event_types = {
    # Credits to RemyK888
    'youtube': '880218394199220334',
    'poker': '755827207812677713',
    'betrayal': '773336526917861400',
    'fishing': '814288819477020702',
    'chess': '832012774040141894',

    # Credits to awesomehet2124
    'letter-tile': '879863686565621790',
    'word-snack': '879863976006127627',
    'doodle-crew': '878067389634314250',

    'spellcast': '852509694341283871',
    'awkword': '879863881349087252',
    'checkers': '832013003968348200',
}


# Embed command stuff
def strip_codeblock(content):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
        return content.strip('```')

    # remove `foo`
    return content.strip('` \n')


def verify_link(argument: str) -> str:
    link = re.fullmatch('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|%[0-9a-fA-F][0-9a-fA-F])+', argument)
    if not link:
        raise commands.BadArgument('Invalid URL provided.')
    return link.string


class FieldFlags(commands.FlagConverter, prefix='--', delimiter=''):
    name: str
    value: str
    inline: bool = True


class FooterFlags(commands.FlagConverter, prefix='--', delimiter=''):
    text: str
    icon: verify_link = discord.Embed.Empty


class AuthorFlags(commands.FlagConverter, prefix='--', delimiter=''):
    name: str
    icon: verify_link = discord.Embed.Empty
    url: verify_link = discord.Embed.Empty


class EmbedFlags(commands.FlagConverter, prefix='--', delimiter=''):

    @classmethod
    async def convert(cls, ctx: CustomContext, argument: str):
        argument = strip_codeblock(argument)
        return await super().convert(ctx, argument)


    title: str = discord.Embed.Empty
    description: str = discord.Embed.Empty
    color: discord.Color = discord.Embed.Empty
    field: typing.List[FieldFlags] = None
    footer: FooterFlags = None
    image: verify_link = None
    author: AuthorFlags = None
    thumbnail: verify_link = None

# End of embed command stuff


async def create_link(bot: DuckBot, vc: discord.VoiceChannel, option: str) -> str:
    """
    Generates an invite link to a VC with the Discord Party VC Feature.
    Parameters
    ----------
    bot: :class: commands.Bot
        the bot instance. It must have a :attr:`session` attribute (a :class:`aiohttp.ClientSession`)
    vc: :class: discord.VoiceChannel
        the voice channel to create the invite link for
    option: str
        the event type to create the invite link for
    Returns
    ----------
    :class:`str`
        Contains the discord invite link which, upon clicked, starts the custom activity in the VC.
    """

    if not vc.permissions_for(vc.guild.me).create_instant_invite:
        raise commands.BotMissingPermissions(['CREATE_INSTANT_INVITE'])

    data = {
        'max_age': 0,
        'max_uses': 0,
        'target_application_id': event_types.get(option),
        'target_type': 2,
        'temporary': False,
        'validate': None
    }

    async with bot.session.post(f"https://discord.com/api/v8/channels/{vc.id}/invites",
                                  json=data, headers={'Authorization': f'Bot {bot.http.token}',
                                                      'Content-Type': 'application/json'}) as resp:
        resp_code = resp.status
        result = await resp.json()

    if resp_code == 429:
        raise commands.BadArgument('Woah there! Slow down. You are being rate-limited.'
                                   f'\nTry again in {result.get("X-RateLimit-Reset-After")}s')
    elif resp_code == 401:
        raise commands.BadArgument('Unauthorized')
    elif result['code'] == 10003 or (result['code'] == 50035 and 'channel_id' in result['errors']):
        raise commands.BadArgument('For some reason, that voice channel is not valid...')
    elif result['code'] == 50013:
        raise commands.BotMissingPermissions(['CREATE_INSTANT_INVITE'])
    elif result['code'] == 130000:
        raise commands.BadArgument('The api is currently overloaded... Try later maybe?')

    return f"https://discord.gg/{result['code']}"


class YoutubeDropdown(discord.ui.View):
    def __init__(self, ctx: CustomContext):
        super().__init__()
        self.ctx = ctx
        self.message: discord.Message = None

    @discord.ui.select(placeholder='Select an activity type...', options=[
        discord.SelectOption(label='Cancel', value='cancel', emoji='❌'),
        discord.SelectOption(label='Youtube', value='youtube', emoji=constants.YOUTUBE_LOGO),
        discord.SelectOption(label='Poker', value='poker', emoji='<:poker_cards:917645571274195004>'),
        discord.SelectOption(label='Betrayal', value='betrayal', emoji='<:betrayal:917647390717141072>'),
        discord.SelectOption(label='Fishing', value='fishing', emoji='🎣'),
        discord.SelectOption(label='Chess', value='chess', emoji='\U0000265f\U0000fe0f'),
        discord.SelectOption(label='Letter Tile', value='letter-tile', emoji='<:letterTile:917647925927084032>'),
        discord.SelectOption(label='Word Snacks', value='word-snack', emoji='<:wordSnacks:917648019342655488>'),
        discord.SelectOption(label='Doodle Crew', value='doodle-crew', emoji='<:doodle:917648115656437810>'),
        discord.SelectOption(label='Spellcast', value='spellcast', emoji='📜'),
        discord.SelectOption(label='Awkword', value='awkword', emoji=constants.TYPING_INDICATOR),
        discord.SelectOption(label='Checkers', value='checkers', emoji='🏁'),
        discord.SelectOption(label='Cancel', value='cancel2', emoji='❌'),
    ])
    async def activity_select(self, select: discord.ui.Select, interaction: discord.Interaction):
        member = interaction.user
        if not member.voice:
            await interaction.response.edit_message(content='You are not connected to a voice channel', view=None)
            return self.stop()
        if 'cancel' in select.values[0]:
            self.stop()
            with contextlib.suppress(discord.HTTPException):
                await interaction.message.delete()
                await self.ctx.message.add_reaction(random.choice(constants.DONE))
            return
        try:
            link = await create_link(self.ctx.bot, member.voice.channel, select.values[0])
        except Exception as e:
            self.stop()
            self.ctx.bot.dispatch('command_error', self.ctx, e)
            with contextlib.suppress(discord.HTTPException):
                await self.message.delete()
            return
        await interaction.response.edit_message(content=f'**To start the activity, press the blue link:**'
                                                        f'\n> <{link}>'
                                                        f'\n_note: activities don\'t work on mobile yet..._', view=None)
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.ctx.author

    async def start(self):
        await self.ctx.send(':rocket: Select the activity you want to start!', view=self)

    async def on_timeout(self) -> None:
        with contextlib.suppress(discord.HTTPException):
            await self.message.delete()
            await self.ctx.message.add_reaction(random.choice(constants.DONE))


def fancify(text, *, style: list, normal: list = None):
    normal = normal or ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
    sub = dict(zip(normal, style))
    pattern = '|'.join(sorted(re.escape(k) for k in sub))

    return re.sub(pattern, lambda m: sub.get(m.group(0)), text, flags=re.IGNORECASE)


def setup(bot):
    bot.add_cog(Fun(bot))


class Fun(commands.Cog):
    """
    🤪 General entertainment commands, and all other commands that don't fit within other categories.
    """

    __slots__ = ('bot',)

    def __init__(self, bot):
        self.bot: DuckBot = bot
        self.select_emoji = '🤪'
        self.select_brief = 'General Entertainment Commands'

    async def reddit(self, subreddit: str, title: bool = False, embed_type: str = 'IMAGE') -> discord.Embed:
        try:
            subreddit = await self.bot.reddit.subreddit(subreddit)
            post = await subreddit.random()

            if embed_type == 'IMAGE':
                while 'i.redd.it' not in post.url or post.over_18:
                    post = await subreddit.random()

                embed = discord.Embed(color=discord.Color.random(),
                                      description=f"🌐 [Post](https://reddit.com{post.permalink}) • "
                                                  f"{constants.REDDIT_UPVOTE} {post.score} ({post.upvote_ratio * 100}%) "
                                                  f"• from [r/{subreddit}](https://reddit.com/r/{subreddit})")
                embed.title = post.title if title is True else None
                embed.set_image(url=post.url)
                return embed

            if embed_type == 'POLL':
                while not hasattr(post, 'poll_data') or not post.poll_data or post.over_18:
                    post = await (await self.bot.reddit.subreddit(subreddit)).random()

                iterations: int = 1
                options = []
                emojis = []
                for option in post.poll_data.options:
                    num = f"{iterations}\U0000fe0f\U000020e3"
                    options.append(f"{num} {option.text}")
                    emojis.append(num)
                    iterations += 1
                    if iterations > 9:
                        iterations = 1

                embed = discord.Embed(color=discord.Color.random(),
                                      description='\n'.join(options))
                embed.title = post.title if title is True else None
                return embed, emojis
        except Exception as error:
            for line in "".join(traceback.format_exception(etype=None, value=error, tb=error.__traceback__)).split(
                    '\n'):
                logging.info(line)
            await self.bot.get_channel(880181130408636456).send('A reddit error occurred! Please check the console.')
            return discord.Embed(description='Whoops! An unexpected error occurred')

    @commands.max_concurrency(1, commands.BucketType.user, wait=True)
    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def cat(self, ctx: CustomContext) -> discord.Message:
        """ Sends a random cat image from r/cats """
        async with ctx.typing():
            await ctx.send(embed=await self.reddit('cats'))

    @commands.max_concurrency(1, commands.BucketType.user, wait=True)
    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def dog(self, ctx: CustomContext) -> discord.Message:
        """ Sends a random dog image from r/dog """
        async with ctx.typing():
            await ctx.send(embed=await self.reddit('dog'))

    @commands.max_concurrency(1, commands.BucketType.user, wait=True)
    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def duck(self, ctx: CustomContext) -> discord.Message:
        """
        Sends a random duck image from random-d.uk
        """
        async with self.bot.session.get('https://random-d.uk/api/random?format=json') as r:
            if r.status != 200:
                raise discord.HTTPException

            res = await r.json()

        embed = discord.Embed(title='Here is a duck!',
                              color=random.randint(0, 0xFFFFFF))
        embed.set_image(url=res["url"])
        embed.set_footer(text='by random-d.uk', icon_url='https://avatars2.githubusercontent.com/u/38426912')
        return await ctx.send(embed=embed)

    @commands.command()
    @commands.bot_has_permissions(send_messages=True)
    async def tias(self, ctx: CustomContext) -> discord.Message:
        """
        Try it and see...
        """
        return await ctx.send("https://tryitands.ee/")

    @commands.command()
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def inspireme(self, ctx: CustomContext) -> discord.Message:
        """
        shows a funny "inspirational" image from inspirobot.me
        """
        async with self.bot.session.get('http://inspirobot.me/api?generate=true') as r:
            if r.status != 200:
                raise discord.HTTPException

            res = await r.text()

        embed = discord.Embed(title='An inspirational image...',
                              color=random.randint(0, 0xFFFFFF))
        embed.set_image(url=res)
        embed.set_footer(text='by inspirobot.me',
                         icon_url='https://inspirobot.me/website/images/inspirobot-dark-green.png')
        return await ctx.send(embed=embed)

    @commands.command(aliases=['pp', 'eggplant', 'cucumber'])
    async def banana(self, ctx: CustomContext, *, member: discord.Member = None) -> discord.Message:
        """
        Measures your banana 😏
        """
        member = member or ctx.author
        scheme = random.choice([("🍆", 0x744EAA), ("🥒", 0x74AE53), ("🍌", 0xFFCD71)])
        size = random.uniform(8, 25)
        embed = discord.Embed(colour=scheme[1])
        embed.description = f"8{'=' * int(round(size, 0))}D\n\n**{member.name}**'s {scheme[0]} is {round(size, 1)} cm"
        embed.set_author(icon_url=member.display_avatar.url, name=member)
        return await ctx.send(embed=embed)

    @commands.max_concurrency(1, commands.BucketType.user, wait=True)
    @commands.command()
    async def meme(self, ctx: CustomContext) -> discord.Message:
        """
        Sends a random meme from r/memes
        """
        async with ctx.typing():
            return await ctx.send(embed=await self.reddit(random.choice(['memes', 'dankmemes'])))

    @commands.max_concurrency(1, commands.BucketType.user, wait=True)
    @commands.command(aliases=['wyr'])
    async def would_you_rather(self, ctx: CustomContext) -> discord.Message:
        """
        Sends a random meme from r/WouldYouRather
        """
        async with ctx.typing():
            poll: tuple = await self.reddit('WouldYouRather', embed_type='POLL', title=True)
            message = await ctx.send(embed=poll[0])
            for reaction in poll[1]:
                await message.add_reaction(reaction)

    @commands.max_concurrency(1, commands.BucketType.user, wait=True)
    @commands.command()
    async def aww(self, ctx: CustomContext) -> discord.Message:
        """
        Sends cute pic from r/aww
        """
        async with ctx.typing():
            return await ctx.send(embed=await self.reddit('aww'))

    @commands.command(name="8ball")
    async def _8ball(self, ctx: CustomContext, *, question: str) -> discord.Message:
        """
        Vaguely answers your question.
        """
        async with ctx.typing():
            await asyncio.sleep(0.5)
            return await ctx.send(f"**Q: {question[0:1800]}**"
                                  f"\nA: {random.choice(_8ball_answers)}")

    @commands.command()
    async def choose(self, ctx: CustomContext, *choices: str) -> discord.Message:
        """
        Chooses one random word from the list of choices you input.
        If you want multi-word choices, use "Quotes for it" "Like so"
        """
        if len(choices) < 2:
            return await ctx.send("You must input at least 2 choices")
        return await ctx.send(random.choice(choices),
                              allowed_mentions=discord.AllowedMentions().none())

    @commands.command(aliases=['cf', 'flip', 'coin'])
    async def coinflip(self, ctx: CustomContext) -> discord.Message:
        """ Flips a VirtualCoin™ """
        return await ctx.send(random.choice(constants.COINS_STRING))

    @commands.command(aliases=['RandomNumber', 'dice'])
    async def roll(self, ctx: CustomContext, number: typing.Optional[int]) -> discord.Message:
        """
        Rolls a VirtualDice™ or, if specified, sends a random number
        """
        number = number if number and number > 0 else None
        if not number:
            return await ctx.send(random.choice(constants.DICES))
        return await ctx.send(random.randint(0, number))

    @commands.command(aliases=['wiki'])
    async def wikipedia(self, ctx, *, search: str):
        """ Searches on wikipedia, and shows the 10 best returns """
        async with ctx.typing():
            async with aiowiki.Wiki.wikipedia('en') as w:
                hyperlinked_titles = [f"[{p.title}]({(await p.urls()).view})" for p in (await w.opensearch(search))]

            iterations = 1
            enumerated_titles = []
            for title_hyperlink in hyperlinked_titles:
                enumerated_titles.append(f"{iterations}) {title_hyperlink}")
                iterations += 1

            embed = discord.Embed(description='\n'.join(enumerated_titles),
                                  colour=discord.Colour.random())
            embed.set_author(icon_url="https://upload.wikimedia.org/wikipedia/en/thumb/8/80/"
                                      "Wikipedia-logo-v2.svg/512px-Wikipedia-logo-v2.svg.png",
                             name="Here are the top 10 Wikipedia results:",
                             url="https://en.wikipedia.org/")
            return await ctx.send(embed=embed)

    @commands.command(name='urban', aliases=['ud'])
    async def _urban(self, ctx, *, word):
        """Searches urban dictionary."""

        url = 'http://api.urbandictionary.com/v0/define'
        async with self.bot.session.get(url, params={'term': word}) as resp:
            if resp.status != 200:
                return await ctx.send(f'An error occurred: {resp.status} {resp.reason}')

            js = await resp.json()
            data = js.get('list', [])
            if not data:
                return await ctx.send('No results found, sorry.')

        pages = ViewPaginator(UrbanPageSource(data), ctx=ctx)
        await pages.start()

    @commands.command(name='achievement')
    async def minecraft_achievement(self, ctx: CustomContext, *, text: commands.clean_content):
        text = urllib.parse.quote(text)
        await ctx.trigger_typing()
        async with self.bot.session.get(f'https://api.cool-img-api.ml/achievement?text={text}',
                                        allow_redirects=True) as r:
            return await ctx.send(r.url)

    @commands.max_concurrency(1, commands.BucketType.user, wait=False)
    @commands.command(aliases=['ttt', 'tic'])
    async def tictactoe(self, ctx: CustomContext, to_invite: discord.Member = None):
        """Starts a tic-tac-toe game."""
        player1 = ctx.author
        if not to_invite:
            embed = discord.Embed(description=f'🔎 | **{ctx.author.display_name}**'
                                              f'\n👀 | User is looking for someone to play **Tic-Tac-Toe**')
            embed.set_thumbnail(url=constants.SPINNING_MAG_GLASS)
            embed.set_author(name='Tic-Tac-Toe', icon_url='https://i.imgur.com/SrRrarG.png')
            view = LookingToPlay(timeout=120)
            view.ctx = ctx
            view.message = await ctx.send(embed=embed,
                                          view=view, footer=None)
            await view.wait()
            player2 = view.value
        else:
            view = RequestToPlayView(ctx, to_invite, game='Tic-Tac-Toe')
            await view.start()
            await view.wait()
            if view.value:
                player2 = to_invite
            else:
                player2 = None

        if player2:
            starter = random.choice([player1, player2])
            ttt = TicTacToe(ctx, player1, player2, starter=starter)
            ttt.message = await view.message.edit(content=f'#️⃣ | **{starter.name}** goes first', view=ttt, embed=None)
            await ttt.wait()

    @commands.command(name='rock-paper-scissors', aliases=['rps', 'rock_paper_scissors'], usage='[to-invite]')
    async def rock_paper_scissors(self, ctx: CustomContext, to_invite: discord.Member = None):
        """Starts a rock-paper-scissors game."""
        player1 = ctx.author
        if not to_invite:
            embed = discord.Embed(description=f'🔎 | **{ctx.author.display_name}**'
                                              f'\n👀 | User is looking for someone to play **Rock-Paper-Scissors**')
            embed.set_thumbnail(url=constants.SPINNING_MAG_GLASS)
            embed.set_author(name='Rock-Paper-Scissors', icon_url='https://i.imgur.com/ZJvaA90.png')

            sep = '\u2001'
            view = LookingToPlay(timeout=120, label=f'{sep * 13}Join this game!{sep * 13}')
            view.ctx = ctx
            view.message = await ctx.send(embed=embed,
                                          view=view, footer=False)
            await view.wait()
            player2 = view.value
        else:
            view = RequestToPlayView(ctx, to_invite)
            await view.start()
            await view.wait()
            if view.value:
                player2 = to_invite
            else:
                player2 = None

        if player2:
            embed = discord.Embed(description=f"> ❌ {player1.display_name}"
                                              f"\n> ❌ {player2.display_name}",
                                  colour=discord.Colour.blurple())
            embed.set_author(name='Rock-Paper-Scissors', icon_url='https://i.imgur.com/ZJvaA90.png')
            rps = RockPaperScissors(ctx, player1, player2)
            rps.message = await view.message.edit(embed=embed, content=None, view=rps)
            await rps.wait()

    @commands.command(aliases=['cag'])
    async def catch(self, ctx: CustomContext, member: typing.Optional[discord.Member]):
        """Catches someone. 😂 """
        upper_hand = await ctx.send(constants.CAG_UP, reply=False, reminders=False)
        message: discord.Message = await self.bot.wait_for('message', check=lambda m: m.channel == ctx.channel and m.author != ctx.me)
        if (member and message.author != member) or message.author == ctx.author:
            await ctx.message.add_reaction(random.choice(constants.DONE))
            return await upper_hand.delete()
        await ctx.send(constants.CAG_DOWN, reply=False, reminders=False)

    async def message_receiver(self, channel: discord.TextChannel, content: str, t_o: int) -> discord.Message:
        def check(m):
            return m.channel == channel and m.content.lower() == content.lower() and not m.author.bot

        try:
            async with timeout(t_o):
                while True:
                    message = await self.bot.wait_for('message', timeout=t_o, check=check)
                    yield message
        except asyncio.TimeoutError:
            return

    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @commands.command(name='type-race', aliases=['tr'], brief='Starts a type-race game. No cheating!')
    async def type_race(self, ctx: CustomContext, amount: typing.Optional[int] = 6):
        """ Starts a Type-Race game.
        Sends some random words as a sentence.
        """
        messages = []

        if 0 > amount > 25:
            raise commands.BadArgument('Amount must be between 1 and 25 words.')
        res = random.sample(constants.COMMON_WORDS, k=amount)
        words = ' '.join(res)

        inv_ch = '\u200b'
        embed = discord.Embed(title=f'{constants.TYPING_INDICATOR} Type-race:',
                              description="**Type the following words:**\n"
                                          f"```\n{inv_ch.join(words)}\n```",
                              timestamp=ctx.message.created_at)
        embed.set_footer(text=f"Results will appear in {amount * 5} seconds!")
        main = await ctx.send(embed=embed)

        async def update_message(m: discord.Message):
            if m.author.id in [msg.author.id for msg in messages]:
                return
            messages.append(m)
            try:
                await m.add_reaction('🎉')
            except discord.HTTPException:
                pass
            embed.clear_fields()
            embed.add_field(name='Results:', value='\n'.join(
                f'{m.author} ({(m.created_at - main.created_at).total_seconds()}s)' for m in messages))
            try:
                await main.edit(embed=embed)
            except discord.HTTPException:
                raise errors.NoHideout()

        async for message in self.message_receiver(content=words, channel=ctx.channel, t_o=amount * 5):
            self.bot.loop.create_task(update_message(message))

        if not messages:
            embed.add_field(name='Results:', value='No one typed anything!')
            await main.edit(embed=embed)
        else:
            await main.delete(delay=0)
            text = embed.fields[0].value
            lines = text.split('\n')

            winner_lines = []

            winner_emotes = ['🥇', '🥈', '🥉']

            for line in lines:
                try:
                    emoji = winner_emotes[lines.index(line)]
                except IndexError:
                    emoji = '🏅'
                winner_lines.append(f'{emoji} {line}')

                embed = discord.Embed(title=f'💤 Type-race game ended!',
                                      description=f"```\n{words}\n```",
                                      timestamp=ctx.message.created_at)
                embed.add_field(name='Game Winners:', value='\n'.join(winner_lines))
                embed.set_footer(text=f'{len(messages)} players got the words right!')
            await ctx.send(embed=embed, reply=False)

    @commands.command(name='fancify', aliases=['fancy', 'ff'])
    async def fancify(self, ctx, *, text):
        """ 𝓯𝓪𝓷𝓬𝓲𝓯𝓲𝓮𝓼 𝓽𝓮𝔁𝓽 """
        style = ['𝓪', '𝓫', '𝓬', '𝓭', '𝓮', '𝓯', '𝓰', '𝓱', '𝓲', '𝓳', '𝓴', '𝓵', '𝓶',
                 '𝓷', '𝓸', '𝓹', '𝓺', '𝓻', '𝓼', '𝓽', '𝓾', '𝓿', '𝔀', '𝔁', '𝔂', '𝔃']
        await ctx.send(fancify(text, style=style), reminders=False)

    @commands.command(name='thicc-text', aliases=['thicc', 'tt'])
    async def thicc_text(self, ctx, *, text):
        """ 𝗠𝗮𝗸𝗲𝘀 𝘁𝗲𝘅𝘁 𝗧𝗛𝗜𝗖𝗖 """
        style = ['𝗔', '𝗕', '𝗖', '𝗗', '𝗘', '𝗙', '𝗚', '𝗛', '𝗜', '𝗝', '𝗞', '𝗟', '𝗠', '𝗡', '𝗢', '𝗣', '𝗤', '𝗥', '𝗦', '𝗧', '𝗨', '𝗩', '𝗪', '𝗫', '𝗬', '𝗭',
                 '𝗮', '𝗯', '𝗰', '𝗱', '𝗲', '𝗳', '𝗴', '𝗵', '𝗶', '𝗷', '𝗸', '𝗹', '𝗺', '𝗻', '𝗼', '𝗽', '𝗾', '𝗿', '𝘀', '𝘁', '𝘂', '𝘃', '𝘄', '𝘅', '𝘆', '𝘇',
                 '𝟭', '𝟮', '𝟯', '𝟰', '𝟱', '𝟲', '𝟳', '𝟴', '𝟵', '𝟬']
        normal = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
                  'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
                  '1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
        await ctx.send(fancify(text, style=style, normal=normal), reminders=False)

    @commands.cooldown(1, 5, commands.BucketType.guild)
    @commands.command()
    async def activity(self, ctx: CustomContext):
        """ Method to start one of the new discord activities """
        if not ctx.author.voice:
            ctx.command.reset_cooldown(ctx)
            await ctx.send('You are not connected to a voice channel')
            return
        view = YoutubeDropdown(ctx)
        await view.start()

    @commands.command(brief='Sends an embed using flags')
    async def embed(self, ctx: commands.Context, *, flags: EmbedFlags):
        """
        A test command for trying out the new flags feature in discord.py v2.0
        Flag usage: `--flag [flag string]`
        Note that `--text... [text]` (with ellipsis) can accept a repeated amount of them:
        Like for example, in this case, with the flag `text`:
        `--text hello --text hi how r u --text a third text and so on`
        `--text...(25)` would mean it can have up to 25 different inputs.
        `--text [text*]` would mean that its **necessary but not mandatory**. AKA if there's multiple of them, you can pass only one, and it will work. But you need **__at least one of the flags marked with `*`__**

        Flags that have an `=` sign mean that they have a default value.
        for example: `--color [Color=#ffffff]` means the color will be `#ffffff` if it can't find a color in the given input.
        Flags can also be mandatory, for example: `--text <text>`. the `<>` brackets mean it is not optional

        **Available flags:**
        `--title [text*]` Sets the embed title.
        `--description [text*]` Sets the embed body/description.
        `--color [color]` Sets the embed's color.
        `--image [http/https URL*]` Sets the embed's image.
        `--thumbnail [http/https URL*]` Sets the embed's thumbnail.
        `--author [AuthorFlags*]` Sets the embed's author.
        `--field...(25) [FieldFlags*]` Sets one of the embed's fields using field flags.
        `--footer [FooterFlags*]` Sets the embed's footer using footer flags.

        **AuthorFlags:**
        > `--name [text*]` Sets the author's name.
        > `--url [http/https URL*]` Sets the author's url.
        > `--icon [http/https URL*]` Sets the author's icon.

        **FieldFlags:**
        > `--name <text>` Sets that field's name
        > `--value <text>` Sets that field's value / body
        > `--inline [yes/no]` If the field should be in-line (displayed alongside other in-line fields if any)
        **For example:** `--field --name hi hello --value more text --inline no`
        _Note: You can have multiple `--field`(s) using `--name` and `--value` (up to 25)_

        **FooterFlags:**
        > `--text [text]` Sets the footer's text
        > `--icon [http/https URL]` Sets the footer's icon

        **Here is an example of the command:**
        ```
        %PRE%embed --title This is the title
        --description This is the description
        --field --name One --value One
        --field --name Two --value Two
        --field --name Three --value Three (but this one isn't in-line) --inline No
        --footer --text This is the footer text
        ```
        """
        embed = discord.Embed(title=flags.title, description=flags.description, colour=flags.color)

        if flags.field and len(flags.field) > 25:
            raise commands.BadArgument('You can only have up to 25 fields!')

        for f in flags.field or []:
            embed.add_field(name=f.name, value=f.value, inline=f.inline)

        if flags.thumbnail:
            embed.set_thumbnail(url=flags.thumbnail)

        if flags.image:
            embed.set_image(url=flags.image)

        if flags.author:
            embed.set_author(name=flags.author.name, url=flags.author.url, icon_url=flags.author.icon)

        if flags.footer:
            embed.set_footer(text=flags.footer.text, icon_url=flags.footer.icon or discord.Embed.Empty)

        if embed:
            if len(embed) > 6000:
                raise commands.BadArgument('The embed is too big! (too much text!)')
            try:
                await ctx.channel.send(embed=embed)
            except discord.HTTPException as e:
                raise commands.BadArgument(f'Failed to send the embed! {type(e).__name__}: {e.text}`')
            except Exception as e:
                raise commands.BadArgument(f'An unexpected error occurred: {type(e).__name__}: {e}')
        else:
            raise commands.BadArgument('You must pass at least one of the necessary (`*`) flags!')
