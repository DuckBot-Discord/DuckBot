import discord
from utils import group, DuckCog, DuckContext, View, DeleteButton


class ShowMeMyKey(View):
    def __init__(self, key: str, user: discord.User | discord.Member):
        self.key = key
        self.user = user
        super().__init__()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.user

    @property
    def embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Your key",
            description=f"Your key is ``{self.key}``",
            color=discord.Color.green(),
        )
        embed.add_field(
            name='So now what... ?',
            value='Now you can access some things of the DuckBot API! '
            'You just need to pass an ``Authorization`` header with a '
            'Bearer key (``Bearer {my key}``).\nIf you wish to see all'
            ' the endpoints that are available to you, ``GET`` to the '
            '``api.duck-bot.com/endpoints`` endpoint.\n\n If you wish '
            'to see the documentation for a specific endpoint, ``GET``'
            ' to ``api.duck-bot.com/endpoints/{endpoint}`` endpoint.',
        )
        return embed

    @discord.ui.button(label="Show me my key", emoji="🔑")
    async def show_me_my_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"{self.key}", embed=self.embed, ephemeral=True)


class Api(DuckCog):
    """
    API commands for the bot owner.
    """

    def __init__(self, bot, *args, **kwargs) -> None:
        super().__init__(bot, *args, **kwargs)
        self.c = 0

    async def handle(self, ctx: DuckContext) -> bool:
        if not ctx.subcommand_passed:
            await ctx.send_help(ctx.command)
        elif not ctx.invoked_subcommand and ctx.subcommand_passed:
            await ctx.send(f"{ctx.subcommand_passed[0:100]!r} is not a valid sub-command!")
        else:
            return False
        return True

    async def try_react(self, message: discord.Message, emoji: str) -> None:
        try:
            await message.add_reaction(emoji)
        except discord.HTTPException:
            await message.channel.send(emoji)

    @group(name='api', invoke_without_command=False)
    async def api(self, ctx: DuckContext):
        if await self.handle(ctx):
            return

    @api.group(name='key', invoke_without_command=False)
    async def api_key(self, ctx: DuckContext, user: discord.Member):
        if await self.handle(ctx):
            return
        ctx.user = user

    @api_key.command(name='generate', aliases=['regenerate', 'gen', 'make', 'regen'])
    async def api_key_generate(self, ctx: DuckContext):
        assert ctx.user
        key = await ctx.bot.provider.make(ctx.user.id)
        if ctx.user.bot:
            view = ShowMeMyKey(key, ctx.author)
            message = f"**Hey {ctx.author.mention}, click here to see {ctx.user.mention}'s API key! You won't be able to see it again.**"
        else:
            view = ShowMeMyKey(key, ctx.user)
            message = f"**Hey {ctx.user.mention}, click here to see your API key! You won't be able to see it again.**"

        await ctx.channel.send(
            message,
            view=view,
            allowed_mentions=discord.AllowedMentions(users=True),
        )

    @api_key.command(name='check')
    async def api_key_check(self, ctx: DuckContext) -> None:
        assert ctx.user
        data = await ctx.bot.provider.get(ctx.user.id)
        if data:
            return await self.try_react(ctx.message, '\N{WHITE HEAVY CHECK MARK}')
        return await self.try_react(ctx.message, '\N{CROSS MARK}')

    @api_key.group(name='deny')
    async def api_key_revoke(self, ctx: DuckContext, endpoint: str) -> None:
        assert ctx.user
        token = await ctx.bot.provider.get(ctx.user.id)
        if not token:
            return await self.try_react(ctx.message, '\N{BLACK QUESTION MARK ORNAMENT}')
        try:
            await token.deny(endpoint)
        except ValueError as e:
            await ctx.send(str(e))
        else:
            await self.try_react(ctx.message, '\N{WHITE HEAVY CHECK MARK}')

    @api_key.group(name='allow', invoke_without_command=True)
    async def api_key_allow(self, ctx: DuckContext, endpoint: str) -> None:
        assert ctx.user
        token = await ctx.bot.provider.get(ctx.user.id)
        if not token:
            return await self.try_react(ctx.message, '\N{BLACK QUESTION MARK ORNAMENT}')
        try:
            await token.allow(endpoint)
        except ValueError as e:
            await ctx.send(str(e))
        else:
            await self.try_react(ctx.message, '\N{WHITE HEAVY CHECK MARK}')

    @api.group(name='endpoints', invoke_without_command=True)
    async def api_endpoints(self, ctx: DuckContext):
        endpoints = await ctx.bot.provider.endpoints.get_all()
        embed = discord.Embed(
            title="Available endpoints",
            description="\n".join(endpoints),
            color=discord.Color.green(),
        )
        await DeleteButton.to_destination(ctx, embed=embed)

    @api_endpoints.command(name='add')
    async def api_endpoints_add(self, ctx: DuckContext, endpoint: str) -> None:
        try:
            await ctx.bot.provider.endpoints.add(endpoint)
        except ValueError as e:
            await ctx.send(str(e))
        else:
            await self.try_react(ctx.message, '\N{WHITE HEAVY CHECK MARK}')

    @api_endpoints.command(name='remove')
    async def api_endpoints_remove(self, ctx: DuckContext, endpoint: str) -> None:
        try:
            await ctx.bot.provider.endpoints.remove(endpoint)
        except ValueError as e:
            await ctx.send(str(e))
        else:
            await self.try_react(ctx.message, '\N{WHITE HEAVY CHECK MARK}')
