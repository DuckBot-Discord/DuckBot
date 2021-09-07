import asyncio
import discord
import yaml
from discord.ext import commands, menus


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
            if command.help:
                command_help = command.help.replace("%PRE%", self.prefix)
            else:
                command_help = 'No help given...'
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

        ignored_cogs = ['helpcog']
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
        if command.help:
            command_help = command.help.replace("%PRE%", self.context.clean_prefix)
        else:
            command_help = 'No help given...'
        if alias:
            embed = discord.Embed(color=discord.Colour.blurple(),
                                  title=f"information about: {self.context.clean_prefix}{command}",
                                  description=f"""
```yaml
      usage: {self.get_minimal_command_signature(command)}
    aliases: {', '.join(alias)}
description: {command_help}
```""")
        else:
            embed = discord.Embed(color=discord.Colour.blurple(),
                                  title=f"information about {self.context.clean_prefix}{command}", description=f"""```yaml
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


class info(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        help_command = MyHelp()
        help_command.cog = self
        bot.help_command = help_command

        # ------------- YAML STUFF -------------#
        with open(r'files/config.yaml') as file:
            full_yaml = yaml.full_load(file)
            self.staff_roles = []
            for roleid in full_yaml['StaffRoles']:
                self.staff_roles.append(self.bot.get_guild(717140270789033984).get_role(roleid))
        self.console = self.bot.get_channel(full_yaml['ConsoleCommandsChannel'])
        self.yaml_data = full_yaml

    @commands.command()
    async def guide(self, ctx):
        embed = discord.Embed(title="Please follow the guide!",
                              description="To make sure that your resource pack is set up correctly, please follow [this guide](https://www.stylizedresourcepack.com/guide). Make sure to enable POM (parallax occlusion mapping) to get the 3D effect",
                              color=ctx.me.color)
        embed.add_field(name="Which shaders does the guide cover?",
                        value="The goes in depth into settings for [BSL shaders](https://bitslablab.com/bslshaders/#download) and [SEUS renewed](https://sonicether.com/shaders/download/renewed-v1-0-1/) shaders.",
                        inline=False)
        embed.add_field(name="Help! I have square artifacts on my blocks.",
                        value="For SEUS renewed, make sure to set the parallax resolution correctly to avoid the blocks having artifacts that look like a grid.",
                        inline=False)
        if ctx.message.reference:
            reply = ctx.message.reference.resolved
            await reply.reply(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.command(aliases=['mods'])
    async def modded(self, ctx):
        embed = discord.Embed(title="Texture packs and mods don't go along well.", description="""
First off, remember that this texture pack is **1.13 and up only**, so if you're using a 1.12 modpack you'll need to convert the pack. do `!1.12` for more info.
Second, We don't assure this texture pack will go along well with mods, there might be compatibility issues and other conflicts with some mod's textures, and especially when using POM(3D stuff)
```as a troubleshooting step, remove all your mods and try the texture pack with vanilla. If it works, then it's a compatibility issue with mods. If that doesn't fix it re-install the pack from #downloads, and also check "!guide"```
""", color=ctx.me.color)
        if ctx.message.reference:
            reply = ctx.message.reference.resolved
            await reply.reply(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.command(aliases=['jvm', 'moreram'])
    async def ram(self, ctx):
        embed = discord.Embed(title="", description="""**[Guide on how to allocate more ram](https://www.online-tech-tips.com/gaming/how-to-allocate-more-ram-to-minecraft/)**
(Keep it between 2-4GB, 6 at most. the default amount of ram is 2GB for a reason)
For more info read [this message](https://ptb.discord.com/channels/717140270789033984/732911954116739143/741047980542525451) and [the follow-up mesage](https://ptb.discord.com/channels/717140270789033984/732911954116739143/859835012983554089) in <#732911954116739143>""",
                              color=ctx.me.color)
        if ctx.message.reference:
            reply = ctx.message.reference.resolved
            await reply.reply(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.command()
    async def shaders(self, ctx):
        embed = discord.Embed(title="",
                              description="**download links for: [optifine](https://optifine.net/downloads), [BSL shaders](https://bitslablab.com/bslshaders/#download) and [SEUS renewed shaders](https://www.sonicether.com/seus/#downloads)**",
                              color=ctx.me.color)
        if ctx.message.reference:
            reply = ctx.message.reference.resolved
            await reply.reply(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.command()
    async def bsl(self, ctx):
        embed = discord.Embed(title="",
                              description="**[download BSL shaders](https://bitslablab.com/bslshaders/#download)** \n**[BitsLab discord server](https://discord.com/invite/ZJd7jjA)** \n**[alternative download](https://drive.google.com/file/d/1DFMQE5JIIFrBATLVnPHsHVOKysEr24xx/view?usp=sharing)**",
                              color=ctx.me.color)
        if ctx.message.reference:
            reply = ctx.message.reference.resolved
            await reply.reply(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.command()
    async def seus(self, ctx):
        embed = discord.Embed(title="",
                              description="**[download SEUS renewed shaders](https://www.sonicether.com/seus/#downloads)** \n**[SEUS alternative download link](https://drive.google.com/file/d/1Z35kGKzKa14ifLeW3QaSFjOzMueaKCH1/view?usp=sharing)**",
                              color=ctx.me.color)
        embed.set_footer(text='May not work well with AMD graphics!')
        if ctx.message.reference:
            reply = ctx.message.reference.resolved
            await reply.reply(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.command(aliases=['of'])
    async def optifine(self, ctx):
        embed = discord.Embed(title="",
                              description="**[download optifine](https://optifine.net/downloads)** \n **[optifine's discord](https://optifine.net/discord)**",
                              color=ctx.me.color)
        if ctx.message.reference:
            reply = ctx.message.reference.resolved
            await reply.reply(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.command(aliases=['upgrade', 'pledge'])
    async def cancel(self, ctx):
        embed = discord.Embed(title="",
                              description="**[cancel/upgrade your pledge here](https://www.patreon.com/pledges)**",
                              color=ctx.me.color)
        if ctx.message.reference:
            reply = ctx.message.reference.resolved
            await reply.reply(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.command(aliases=['download', 'dchannel'])
    async def downloads(self, ctx):
        embed = discord.Embed(title="", description="""To access the download channel you need to have a role `Steeler` or higher, and you don't appear to have it.
If you already purchased a `Steeler` or higher subscription, link your Patreon to Discord. [[more info]](https://support.patreon.com/hc/en-us/articles/212052266-Get-my-Discord-role#:~:text=Step%201%3A%20Log%20in%20to,role%20tied%20to%20your%20Tier!)
If your account is already linked, unlink and relink it. [[more info]](https://support.patreon.com/hc/en-us/articles/212052266-Get-my-Discord-role#:~:text=Step%201%3A%20Log%20in%20to,role%20tied%20to%20your%20Tier!) about how to get your role.

If you don't already have a `Steeler` or higher subscription, you can get one at [patreon.com/stylized](https://www.patreon.com/Stylized).""",
                              color=ctx.me.color)
        if ctx.message.reference:
            reply = ctx.message.reference.resolved
            await reply.reply(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.command()
    async def radeon(self, ctx):
        embed = discord.Embed(title="", description="""**__Regarding shaders and AMD Radeon Drivers__**
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
Also, starting with 21.2.3, some packs will refuse to load, such as Chocapic V9, while others have improved stability.""",
                              color=ctx.me.color)
        embed.set_author(name="Copied straight from optifine's support channel",
                         icon_url="https://i.imgur.com/uZsxgEf.png")
        if ctx.message.reference:
            reply = ctx.message.reference.resolved
            await reply.reply(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.command(aliases=['oldversions', '1.12', '1.8', '1.8.9'])
    async def unsupported(self, ctx):
        embed = discord.Embed(title="Can i use this pack with an older version of minecraft?", description="""You technically can, but this pack is only made for versions that are 1.13 and higher.
Older versions of minecraft use a different file structure for their resource packs and/or different names for some of the textures.
There seems to be some conversion tools out there that can change a texture pack to work in one of these older versions of the game but this is not supported by us, and you will not recieve the same support that you would get using a newer version of minecraft.
Another way is, if you have the time, changing it manually to the old file structure.""", color=ctx.me.color)
        if ctx.message.reference:
            reply = ctx.message.reference.resolved
            await reply.reply(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.command(aliases=['communication', 'translate', 'translator'])
    async def translation(self, ctx):
        embed = discord.Embed(title="Is english not your main language?", description=
        """
You can use <@471542070817849355> to translate your messages!
To translate to english just do:
```?en <message>```
""", color=ctx.me.color)
        await ctx.send(embed=embed)

    @commands.command()
    async def rank(self, ctx):
        embed = discord.Embed(description="Nah... 😂", color=ctx.me.color)
        await ctx.send(embed=embed)

    @commands.command()
    async def relink(self, ctx):
        embed = discord.Embed(title="You have an active subscription but you don't have a role?", description=f"""
to get your role, go to [patreon.com/settings/apps ](https://www.patreon.com/settings/apps), then `disconnect` and `connect` your discord account.
**Done, you should get your role now!**

[Patreon official support aticle.](https://support.patreon.com/hc/en-us/articles/212052266-Get-my-Discord-role)
""", color=ctx.me.color)
        if ctx.message.reference:
            reply = ctx.message.reference.resolved
            await reply.reply(embed=embed)
        else:
            await ctx.send(embed=embed)


# ------------------------------------------------------------------------------
# ---- 2.0 stuff that will be available when d.py gets a stable 2.0 release ----
# ------------------------------------------------------------------------------

#    @commands.command()
#    async def links(self, ctx):
#
#        class View(discord.ui.View):
#            @discord.ui.button(style=discord.ButtonStyle.secondary, label="Guide", emoji="<:info:847682027892768768>")
#            async def Guide(self, button, interaction):
#                embed=discord.Embed(title="Please follow the guide!", description="To make sure that your resource pack is set up correctly, please follow [this guide](https://www.stylizedresourcepack.com/guide). Make sure to enable POM (parallax occlusion mapping) to get the 3D effect", color=ctx.me.color)
#                embed.add_field(name="Which shaders does the guide cover?", value="The goes in depth into settings for [BSL shaders](https://bitslablab.com/bslshaders/#download) and [SEUS renewed](https://sonicether.com/shaders/download/renewed-v1-0-1/) shaders.", inline=False)
#                embed.add_field(name="Help! I have square artifacts on my blocks.", value="For SEUS renewed, make sure to set the parallax resolution correctly to avoid the blocks having artifacts that look like a grid.", inline=False)
#                await interaction.response.send_message(embed=embed, ephemeral=True)
#            @discord.ui.button(style=discord.ButtonStyle.secondary, label="Optifine", emoji="<:download:847682027435327498>")
#            async def Optifine(self, button, interaction):
#                embed=discord.Embed(title="", description="**[download optifine](https://optifine.net/downloads)** \n **[optifine's discord](https://optifine.net/discord)**", color=ctx.me.color)
#                await interaction.response.send_message(embed=embed, ephemeral=True)
#            @discord.ui.button(style=discord.ButtonStyle.secondary, label="BSL", emoji="<:download:847682027435327498>")
#            async def DownloadBsl(self, button, interaction):
#                embed=discord.Embed(title="", description="**[download BSL shaders](https://bitslablab.com/bslshaders/#download)** \n **[BitsLab discord server](https://discord.com/invite/ZJd7jjA)**", color=ctx.me.color)
#                await interaction.response.send_message(embed=embed, ephemeral=True)
#            @discord.ui.button(style=discord.ButtonStyle.secondary, label="SEUS renewed", emoji="<:download:847682027435327498>")
#            async def DownloadSeus(self, button, interaction):
#                embed=discord.Embed(title="", description="**[download SEUS renewed shaders](https://www.sonicether.com/seus/#downloads)**", color=ctx.me.color)
#                embed.set_footer(text='May not work well with AMD graphics!')
#                await interaction.response.send_message(embed=embed, ephemeral=True)
#            @discord.ui.button(style=discord.ButtonStyle.secondary, label="Allocate more RAM", emoji="<:info:847682027892768768>")
#            async def MoreRam(self, button, interaction):
#                embed=discord.Embed(title="", description="**[How to allocate more ram](https://www.online-tech-tips.com/gaming/how-to-allocate-more-ram-to-minecraft/)** (keep it between 6-8GB)", color=ctx.me.color)
#                await interaction.response.send_message(embed=embed, ephemeral=True)
#        view = View()
#
#        embed=discord.Embed(title="Here are some useful links you might need", description="**Click on the buttons to see them**", color=ctx.me.color)
#        embed.set_footer(text="this !message expires in 1 minute")
#        await ctx.send(embed=embed, view = view, delete_after = 60)
#        await asyncio.sleep(60)
#        await ctx.message.delete()
#
#
#    @commands.command(aliases=['info'])
#    async def buttons(self, ctx):
#
#        class View(discord.ui.View):
#            @discord.ui.button(style=discord.ButtonStyle.secondary, label="Guide", emoji="<:info:847682027892768768>")
#            async def Guide(self, button, interaction):
#                embed=discord.Embed(title="Please follow the guide!", description="To make sure that your resource pack is set up correctly, please follow [this guide](https://www.stylizedresourcepack.com/guide). Make sure to enable POM (parallax occlusion mapping) to get the 3D effect", color=ctx.me.color)
#                embed.add_field(name="Which shaders does the guide cover?", value="The goes in depth into settings for [BSL shaders](https://bitslablab.com/bslshaders/#download) and [SEUS renewed](https://sonicether.com/shaders/download/renewed-v1-0-1/) shaders.", inline=False)
#                embed.add_field(name="Help! I have square artifacts on my blocks.", value="For SEUS renewed, make sure to set the parallax resolution correctly to avoid the blocks having artifacts that look like a grid.", inline=False)
#                await interaction.response.send_message(embed=embed, ephemeral=True)
#            @discord.ui.button(style=discord.ButtonStyle.secondary, label="Allocate more RAM", emoji="<:info:847682027892768768>")
#            async def MoreRam(self, button, interaction):
#                embed=discord.Embed(title="", description="**[How to allocate more ram](https://www.online-tech-tips.com/gaming/how-to-allocate-more-ram-to-minecraft/)** (keep it between 6-8GB)", color=ctx.me.color)
#                await interaction.response.send_message(embed=embed, ephemeral=True)
#            @discord.ui.button(style=discord.ButtonStyle.secondary, label="Optifine", emoji="<:download:847682027435327498>")
#            async def Optifine(self, button, interaction):
#                embed=discord.Embed(title="", description="**[download optifine](https://optifine.net/downloads)** \n **[optifine's discord](https://optifine.net/discord)**", color=ctx.me.color)
#                await interaction.response.send_message(embed=embed, ephemeral=True)
#            @discord.ui.button(style=discord.ButtonStyle.secondary, label="BSL", emoji="<:download:847682027435327498>")
#            async def DownloadBsl(self, button, interaction):
#                embed=discord.Embed(title="", description="**[download BSL shaders](https://bitslablab.com/bslshaders/#download)** \n **[BitsLab discord server](https://discord.com/invite/ZJd7jjA)**", color=ctx.me.color)
#                await interaction.response.send_message(embed=embed, ephemeral=True)
#            @discord.ui.button(style=discord.ButtonStyle.secondary, label="SEUS renewed", emoji="<:download:847682027435327498>")
#            async def DownloadSeus(self, button, interaction):
#                embed=discord.Embed(title="", description="**[download SEUS renewed shaders](https://www.sonicether.com/seus/#downloads)**", color=ctx.me.color)
#                embed.set_footer(text='May not work well with AMD graphics!')
#                await interaction.response.send_message(embed=embed, ephemeral=True)
#        view = View()
#
#
#        await ctx.send("<:Discord:847690431227494401> Buttons! _these will disappear in 1 minute_", view = view, delete_after = 60)
#        await asyncio.sleep(60)
#        await ctx.message.delete()
#
#
#    @commands.command()
#    async def guideTest(self, ctx):
#        view = discord.ui.View
#        view.add_item(self, item=discord.ui.Button(style=discord.ButtonStyle.primary, label="Guide", url = "https://www.stylizedresourcepack.com/guide"))
#        embed=discord.Embed(description="test", color=ctx.me.color)
#        await ctx.send(embed=embed, view = view)


def setup(bot):
    bot.add_cog(info(bot))
