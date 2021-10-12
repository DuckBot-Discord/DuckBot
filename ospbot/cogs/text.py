import json, random, typing, discord, asyncio, time, os, inspect, itertools, re, time, yaml, json, aiohttp
from discord.ext import commands, menus
from discord.ext.commands import Paginator as CommandPaginator
import helpers

class Duckinator(menus.MenuPages):
    def __init__(self, source):
        super().__init__(source=source, check_embeds=True)
        self.input_lock = asyncio.Lock()

    async def finalize(self, timed_out):
        try:
            if timed_out:
                await self.message.clear_reactions()
            else:
                await self.message.delete()
        except discord.HTTPException:
            pass

    @menus.button('\N{INFORMATION SOURCE}\ufe0f', position=menus.Last(3))
    async def show_help(self, payload):
        """shows this message"""
        embed = discord.Embed(title='Paginator help', description='Hello! Welcome to the help page.')
        messages = []
        for (emoji, button) in self.buttons.items():
            messages.append(f'{emoji}: {button.action.__doc__}')

        embed.add_field(name='What are these reactions for?', value='\n'.join(messages), inline=False)
        embed.set_footer(text=f'We were on page {self.current_page + 1} before this message.')
        await self.message.edit(content=None, embed=embed)

        async def go_back_to_current_page():
            await asyncio.sleep(30.0)
            await self.show_page(self.current_page)

        self.bot.loop.create_task(go_back_to_current_page())

    @menus.button('\N{INPUT SYMBOL FOR NUMBERS}', position=menus.Last(1.5), lock=False)
    async def numbered_page(self, payload):
        """lets you type a page number to go to"""
        if self.input_lock.locked():
            return

        async with self.input_lock:
            channel = self.message.channel
            author_id = payload.user_id
            to_delete = []
            to_delete.append(await channel.send('What page do you want to go to?'))

            def message_check(m):
                return m.author.id == author_id and \
                       channel == m.channel and \
                       m.content.isdigit()

            try:
                msg = await self.bot.wait_for('message', check=message_check, timeout=30.0)
            except asyncio.TimeoutError:
                to_delete.append(await channel.send('Took too long.'))
                await asyncio.sleep(5)
            else:
                page = int(msg.content)
                to_delete.append(msg)
                await self.show_checked_page(page - 1)

            try:
                await channel.delete_messages(to_delete)
            except Exception:
                pass

class HelpMenu(Duckinator):
    def __init__(self, source):
        super().__init__(source)

    @menus.button('\N{WHITE QUESTION MARK ORNAMENT}', position=menus.Last(5))
    async def show_bot_help(self, payload):
        """shows how to use the bot"""

        embed = discord.Embed(title='Using the bot', colour=discord.Colour.blurple())
        embed.title = 'Using the bot'
        embed.description = 'Hello! Welcome to the help page.'

        entries = (
            ('<argument>', 'This means the argument is __**required**__.'),
            ('[argument]', 'This means the argument is __**optional**__.'),
            ('[A|B]', 'This means that it can be __**either A or B**__.'),
            ('[argument...]', 'This means you can have multiple arguments.\n' \
                              'Now that you know the basics, it should be noted that...\n' \
                              '__**You do not type in the brackets!**__')
        )

        embed.add_field(name='How do I use this bot?', value='Reading the bot signature is pretty simple.')

        for name, value in entries:
            embed.add_field(name=name, value=value, inline=False)

        embed.set_footer(text=f'We were on page {self.current_page + 1} before this message.')
        await self.message.edit(embed=embed)

        async def go_back_to_current_page():
            await asyncio.sleep(30.0)
            await self.show_page(self.current_page)

        self.bot.loop.create_task(go_back_to_current_page())

class GroupHelpPageSource(menus.ListPageSource):
    def __init__(self, group, commands, *, prefix):
        super().__init__(entries=commands, per_page=6)
        self.group = group
        self.prefix = prefix
        self.title = f'{self.group.qualified_name} Commands'
        self.description = self.group.description

    async def format_page(self, menu, commands):
        embed = discord.Embed(title=self.title, description=self.description, colour=discord.Colour.blurple())

        for command in commands:
            signature = f'{command.qualified_name} {command.signature}'
            if command.help: command_help = command.help.replace("%PRE%", self.prefix)
            else: command_help = 'No help given...'
            embed.add_field(name=signature, value=f"```yaml\n{command_help}```", inline=False)

        maximum = self.get_max_pages()
        if maximum > 1:
            embed.set_author(name=f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} commands)')

        embed.set_footer(text=f'Use "{self.prefix}help command" for more info on a command.')
        return embed

class MyHelp(commands.HelpCommand):
    # Formatting
    def get_minimal_command_signature(self, command):
        return '%s%s %s' % (self.context.clean_prefix, command.qualified_name, command.signature)

    def get_command_name(self, command):
        return '%s' % (command.qualified_name)

   # !help
    async def send_bot_help(self, mapping):
        embed = discord.Embed(color=discord.Colour.blurple(), title=f"ℹ {self.context.me.name} help",
        description=f"""
```fix
usage format: <required> [optional]
{self.context.clean_prefix}help [command] - get information on a command
{self.context.clean_prefix}help [category] - get information on a category
```
_ _""")

        ignored_cogs=['helpcog']
        for cog, commands in mapping.items():
            if cog is None or cog.qualified_name in ignored_cogs: continue
            filtered = await self.filter_commands(commands, sort=True)
            command_signatures = [self.get_command_name(c) for c in filtered]
            if command_signatures:
                val = "`, `".join(command_signatures)
                embed.add_field(name=cog.qualified_name, value=f"{cog.description}\n`{val}`", inline=True)

        channel = self.get_destination()
        await channel.send(embed=embed)

    def common_command_formatting(self, embed_like, command):
        embed_like.title = self.get_command_signature(command)
        if command.description:
            embed_like.description = f'{command.description}\n\n```yaml\n{command.help}\n```'
        else:
            embed_like.description = command.help or '```yaml\nNo help found...\n```'

  # !help <command>
    async def send_command_help(self, command):
        alias = command.aliases
        if command.help: command_help = command.help.replace("%PRE%", self.context.clean_prefix)
        else: command_help = 'No help given...'
        if alias:
            embed = discord.Embed(color=discord.Colour.blurple(), title=f"information about: {self.context.clean_prefix}{command}",
            description=f"""
```yaml
      usage: {self.get_minimal_command_signature(command)}
    aliases: {', '.join(alias)}
description: {command_help}
```""")
        else:
            embed = discord.Embed(color=discord.Colour.blurple(), title=f"information about {self.context.clean_prefix}{command}", description=f"""```yaml
      usage: {self.get_minimal_command_signature(command)}
description: {command_help}
```""")
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_cog_help(self, cog):
        entries = cog.get_commands()
        menu = HelpMenu(GroupHelpPageSource(cog, entries, prefix=self.context.clean_prefix))
        await menu.start(self.context)


    async def send_group_help(self, group):
        subcommands = group.commands
        if len(subcommands) == 0:
            return await self.send_command_help(group)

        entries = await self.filter_commands(subcommands, sort=True)
        if len(entries) == 0:
            return await self.send_command_help(group)

        source = GroupHelpPageSource(group, entries, prefix=self.context.clean_prefix)
        menu = HelpMenu(source)
        await menu.start(self.context)




class text(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        help_command = MyHelp()
        help_command.cog = self
        bot.help_command = help_command

    ##### .s <text> #####
    # resends the message as the bot

    @commands.command(aliases=['s', 'send'], usage="<text>", help="Speak as if you were me. # URLs/Invites not allowed!")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(send_messages=True, manage_messages=True)
    async def say(self, ctx, *, msg: typing.Optional[str]):
        if msg==None:
            await ctx.send(f"Error! empty. do: `{ctx.prefix}{ctx.command} <text>`")

        results = re.findall("http[s]?:\/\/(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", msg) # HTTP/HTTPS URL regex
        results2 = re.findall("(?:https?:\/\/)?discord(?:app)?\.(?:com\/invite|gg)\/[a-zA-Z0-9]+\/?", msg) # Discord invite regex
        if results or results2:
            await ctx.send(f"`{ctx.prefix}{ctx.command}` can't be used to send invites or URLs, as it could bypass spam filters!", delete_after=5)
            try: await ctx.message.delete(delay=5)
            except: return
            return

        try:
            await ctx.message.delete()
        except:
            pass
        if ctx.channel.permissions_for(ctx.author).mention_everyone:
            if ctx.message.reference:
                reply = ctx.message.reference.resolved
                await reply.reply(msg)
            else:
                await ctx.send(msg)
        else:
            if ctx.message.reference:
                reply = ctx.message.reference.resolved
                await reply.reply(msg, allowed_mentions = discord.AllowedMentions(everyone = False))
            else:
                await ctx.send(msg, allowed_mentions = discord.AllowedMentions(everyone = False))

    ##### .a <TextChannel> <text> ######
    #sends the message in a channel

    @commands.command(help="Echoes a message to another channel",aliases=['a', 'an', 'announce'], usage="<channel> <message>")
    @commands.check_any(commands.has_permissions(manage_messages=True), commands.is_owner())
    @commands.bot_has_permissions(send_messages=True, manage_messages=True)
    async def echo(self, ctx, channels: commands.Greedy[discord.TextChannel], *, msg):
        await ctx.send(f"""```
{msg}
``` sent to: {', '.join([tc.mention for tc in channels])}""")
        for channel in channels:
            if channel.permissions_for(ctx.author).mention_everyone:
                if ctx.message.reference:
                    msg = ctx.message.reference.resolved.content
                await channel.send(msg)

            else:
                if ctx.message.reference:
                    msg = ctx.message.reference.resolved.content
                await channel.send(msg, allowed_mentions = discord.AllowedMentions(everyone = False))

    @commands.command(  aliases=['e'],
                        usage="-reply- [new message] [--d|--s]",
                        help="Quote a bot message to edit it. # Append --s at the end to supress embeds and --d to delete the message")
    @commands.check_any(commands.has_permissions(manage_messages=True), commands.is_owner())
    @commands.bot_has_permissions(send_messages=True, manage_messages=True)
    async def edit(self, ctx, *, new_message : typing.Optional[str] = '--d'):
        new = new_message
        if ctx.message.reference:
            msg = ctx.message.reference.resolved
            try:
                if new.endswith("--s"): await msg.edit(content=f"{new[:-3]}", suppress=True)
                elif new.endswith('--d'): await msg.delete()
                else: await msg.edit(content=new, suppress=False)
                try: await ctx.message.delete()
                except discord.Forbidden:
                    return
            except: pass
        else:
            await ctx.message.add_reaction('⚠')
            await asyncio.sleep(3)
            try: await ctx.message.delete()
            except discord.Forbidden: return

    #### .jumbo <Emoji> ####
    # makes emoji go big

    @commands.command(  aliases=['jumbo', 'bigemoji', 'emojinfo'],
                        help="Makes an emoji bigger and shows it's formatting", usage="<emoji>")
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def emoji(self, ctx, emoji: typing.Optional[discord.PartialEmoji]):
        if emoji == None: await ctx.send(embed = discord.Embed(description="Please specify a valid Custom Emoji", color=ctx.me.color))
        else:
            if emoji.animated: emojiformat = f"*`<`*`a:{emoji.name}:{emoji.id}>`"
            else: emojiformat = f"*`<`*`:{emoji.name}:{emoji.id}>`"
            embed = discord.Embed(description=f"{emojiformat}",color=ctx.me.color)
            embed.set_image(url = emoji.url)
            await ctx.send(embed=embed)

    @commands.command()
    async def ping(self, ctx):
        embed = discord.Embed(title='', description="🏓 pong!", color=ctx.me.color)
        start = time.perf_counter()
        message = await ctx.send(embed=embed)
        end = time.perf_counter()
        await asyncio.sleep(0.7)
        duration = (end - start) * 1000
        embed = discord.Embed(title='', description=f'**websocket:** `{(self.bot.latency * 1000):.2f}ms` \n**message:** `{duration:.2f}ms`', color=ctx.me.color)
        await message.edit(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def sendembed(self, ctx, *, data):
        try:
            dictionary = json.loads(data)
        except:
            await ctx.send("json data malformed")
            return
        embed = discord.Embed().from_dict(dictionary)
        try:
            await ctx.send(embed=embed)
        except:
            await ctx.send("json data malformed")
            return
        await ctx.message.delete()

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def addemb(self, ctx, *, data):
        if ctx.message.reference:
            msg = ctx.message.reference.resolved
            try:
                dictionary = json.loads(data)
            except:
                await ctx.send("json data malformed", delete_after=3)
                return
            embed = discord.Embed().from_dict(dictionary)
            try:
                await msg.edit(content = msg.content, embed=embed)
            except:
                await ctx.send("json data malformed", delete_after=3)
                return
            await ctx.message.delete()
        else:
            await ctx.message.add_reaction('⚠')
            await asyncio.sleep(3)
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                return

    @commands.command()
    @helpers.is_osp_server()
    async def donate(self,ctx):
        embed=discord.Embed(title="**Thank you so much for supporting us!**", description="If applicable, please add a note saying it's for OSP so I can put it in the right bank account!", color=0x0066ff)
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)
        embed.set_thumbnail(url="https://i.pinimg.com/originals/b9/27/e8/b927e82096e8f74e62b1666e727a694c.gif")
        embed.add_field(name="Donate using Venmo:", value="[Click Here to donate using Venmo](http://venmo.com/maxwellmandell)", inline=False)
        embed.add_field(name="Donate using CashApp:", value="[Click Here to donate using Cashapp](https://cash.app/obscuresorrowsproj)", inline=False)
        embed.add_field(name="Donate using Paypal:", value="[Click Here to donate using PayPal](https://www.paypal.com/paypalme/maxwellmandell)", inline=False)
        embed.set_footer(text="Again, thank you for your support! Money that isn't planned to be used for the project will be donated to NAMI.")
        await ctx.send(embed=embed)

    @commands.command(help = "shows a specified server rule")
    @commands.guild_only()
    @helpers.is_osp_server()
    async def rule(self, ctx, number: typing.Optional[int]):
        if number == None:
            await ctx.send(
embed = discord.Embed(color = 0x0066ff, description=
"""
Command Usage:
.rule [rule_number]
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

    @commands.command()
    @helpers.is_osp_server()
    async def about(self, ctx):
        await ctx.send("""**The Obscure Sorrows Project**
*Helping us make sense of our past, and giving it purpose and creativity.*
https://youtu.be/sSDfBiHTFpo""")

    @commands.command()
    @helpers.is_osp_server()
    async def vote(self, ctx):
        embed = discord.Embed(color = ctx.me.color, description="**On [Disboard](https://disboard.org/server/831897006812561409) and [Disforge](https://disforge.com/server/46125-osp)!**")
        embed.set_author(name=f"{ctx.guild.name} - vote here:", icon_url=ctx.guild.icon.url)
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(text(bot))
