
import  discord, asyncio
from discord.ext import commands
from discord.ext.commands import BucketType

class handler(commands.Cog):
    """🆘 manejar los errores 👀"""
    def __init__(self, bot):
        self.bot = bot

    async def perms_error(self, ctx):
        await ctx.message.add_reaction('🚫')
        try: await ctx.message.delete(delay=5)
        except: pass

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, "original", error)

        if isinstance(error, discord.ext.commands.CheckAnyFailure):
            for e in error.errors:
                if error != commands.NotOwner:
                    error = e
                    break


        embed = discord.Embed(color=0xD7342A)
        embed.set_author(name = 'Permisos insuficientes!', icon_url='https://i.imgur.com/OAmzSGF.png')

        if isinstance(error, commands.NotOwner):
            await ctx.send(f"Debes ser el dueño de `{ctx.me.display_name}` para usar `{ctx.command}`")
            return

        if isinstance(error, commands.MissingPermissions):
            text=f"Te faltan los siguientes permisos: \n**{', '.join(error.missing_perms)}**"
            try:
                embed.description=text
                await ctx.send(embed=embed)
            except:
                try: await ctx.send(text)
                except: pass
            return

        elif isinstance(error, commands.BotMissingPermissions):
            text=f"Me faltan los siguientes permisos: \n**{', '.join(error.missing_perms)}**"
            try:
                embed.description=text
                await ctx.send(embed=embed)
            except:
                try: await ctx.send(text)
                except: pass
            return

        elif isinstance(error, discord.ext.commands.MissingRequiredArgument):
            missing=f"{str(error.param).split(':')[0]}"
            command = f"{ctx.prefix}{ctx.command} {ctx.command.signature}"
            separator = (' ' * (len(command.split(missing)[0])-1))
            indicator = ('^' * (len(missing)+2))
            print(f"`{separator}`  `{indicator}`")
            print(error.param)
            print()
            await ctx.send(f"""```
{command}
{separator}{indicator}
Argumento faltante: {missing}
```""")


        elif isinstance(error, discord.ext.commands.errors.CommandOnCooldown):
            embed = discord.Embed(color=0xD7342A, description = f'Por favor intenta de nuevo en {round(error.retry_after, 2)} segundo(s)')
            embed.set_author(name = 'Comando en cooldown!', icon_url='https://i.imgur.com/izRBtg9.png')

            if error.cooldown.type == BucketType.default: per = ""
            if error.cooldown.type == BucketType.user: per = "por usuario"
            if error.cooldown.type == BucketType.guild: per = "por servidor"
            if error.cooldown.type == BucketType.channel: per = "por canal"
            if error.cooldown.type == BucketType.member: per = "por miembro"
            if error.cooldown.type == BucketType.category: per = "por categoría"
            if error.cooldown.type == BucketType.role: per = "por rol"

            embed.set_footer(text=f"delay: {error.cooldown.rate} veces cada {error.cooldown.per}s {per}")
            return await ctx.send(embed=embed)

        elif isinstance(error, discord.ext.commands.errors.CommandNotFound):
            pass

        else:
            await self.bot.wait_until_ready()
            await ctx.send(f"""```diff\n- Un error inesperado ha ocurrido durante la ejecución del comando \"{ctx.command}\"
{error}```""")
            await self.bot.get_channel(847943387083440128).send(f"""```diff\n- {ctx.command} command raised an error:
{error}```""")
            raise error

def setup(bot):
    bot.add_cog(handler(bot))
