import discord, asyncio, typing, aiohttp, random, json, yaml, re
from discord.ext import commands, menus
from main import execute_command

class form(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        #------------- YAML STUFF -------------#
        with open(r'files/config.yaml') as file:
            full_yaml = yaml.full_load(file)

    @commands.command()
    @commands.guild_only()
    @commands.max_concurrency(1, per=commands.BucketType.user, wait=False)
    async def form(self, ctx):
        embed=discord.Embed(color=0x47B781, description=f"<a:loading:864708067496296468> Iniciando...")
        message = await ctx.send(ctx.author.mention, embed=embed)

        def check(m: discord.Message):  # m = discord.Message.
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

        def reaction_check(reaction, user):
            return user == ctx.message.author and str(reaction.emoji) in ['✅', '❌', '❓']

        await asyncio.sleep(2)


############################################################################################


        embed=discord.Embed(color=0x47B781,
                            description=f"""
Hola {ctx.author.mention}, bienvenid@ al formulario!
Se te harán una serie de preguntas referentes a aplicar para el servidor de minecraft.
**¿Quieres continuar?**""")

        await message.edit(content=ctx.author.mention, embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=600.0, check=reaction_check)

        except asyncio.TimeoutError:
            # at this point, the check didn't become True, let's handle it.
            err=discord.Embed(color=0xD7342A, description=f"**Confirmación fallida**")
            await message.edit(content=ctx.author.mention, embed=err)
            return
        else:
            if str(reaction.emoji) == '❌':
                err=discord.Embed(color=0xD7342A, description=f"**Cancelado!**")
                await ctx.send(ctx.author.mention, embed=err)
                return


############################################################################################


        embed.description="_ _"
        embed.title="¿Cual es tu usuario de twitch?"
        embed.set_footer(text="envía \"cancelar\" para cancelar y finalizar.")
        await ctx.send(ctx.author.mention, embed=embed)

        try:
            msg = await self.bot.wait_for(event = 'message', check = check, timeout = 600.0)

        except asyncio.TimeoutError:
            err=discord.Embed(color=0xD7342A, description=f"**Cancelado! No has respondido a tiempo.**")
            await ctx.send(ctx.author.mention, embed=err)
            return

        else:
            if msg.content.lower() == "cancelar":
                    err=discord.Embed(color=0xD7342A, description=f"**Cancelado!**")
                    await ctx.send(ctx.author.mention, embed=err)
                    return
            usuario = msg.content


############################################################################################


        embed.title="¿Utilizas el launcher oficial de minecraft?"
        embed.description="✅ **Sí**\n❌ **No**\n❓ **No sé**"
        embed.set_footer(text=discord.Embed.Empty)

        chm = await ctx.send(ctx.author.mention, embed=embed)
        await chm.add_reaction("✅")
        await chm.add_reaction("❌")
        await chm.add_reaction("❓")

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=600.0, check=reaction_check)

        except asyncio.TimeoutError:
            err=discord.Embed(color=0xD7342A, description=f"**tiempo de espera caducado**")
            await chm.edit(content=ctx.author.mention, embed=err)
            return

        else:
            oficial = str(reaction.emoji)


############################################################################################


        embed.title="¿Necesitas ayuda para instalar mods/server/launcher?"
        embed.description="_ _"
        chm = await ctx.send(ctx.author.mention, embed=embed)
        await chm.add_reaction("✅")
        await chm.add_reaction("❌")

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=600.0, check=reaction_check)

        except asyncio.TimeoutError:
            # at this point, the check didn't become True, let's handle it.
            err=discord.Embed(color=0xD7342A, description=f"**tiempo de espera caducado**")
            await chm.edit(content=ctx.author.mention, embed=err)
            return
        else:
            ayuda = str(reaction.emoji)


############################################################################################


        embed.description="_ _"
        embed.title="¿Cuál es tu user de Minecraft?"
        embed.set_footer(text="envía \"cancelar\" para cancelar y finalizar.")
        await ctx.send(ctx.author.mention, embed=embed)

        looping = True
        while looping == True:
            try:
                msg = await self.bot.wait_for(event = 'message', check = check, timeout = 600.0)

            except asyncio.TimeoutError:
                err=discord.Embed(color=0xD7342A, description=f"**Cancelado! No has respondido a tiempo.**")
                await ctx.send(ctx.author.mention, embed=err)
                return

            else:
                if msg.content.lower() == "cancelar":
                    err=discord.Embed(color=0xD7342A, description=f"**Cancelado!**")
                    await ctx.send(ctx.author.mention, embed=err)
                    return

                async with aiohttp.ClientSession() as cs:
                    async with cs.get(f"https://api.mojang.com/users/profiles/minecraft/{msg.content}") as cs:
                        if cs.status == 204 or cs.status == 404:
                            usuario_mc = msg.content
                            looping = False

                        elif cs.status == 400:
                            await ctx.send(f"`{msg.content}` no es un usuario valido, intenta de nuevo")
                        else:
                            res = await cs.json()
                            usu = res["name"]

                            chm = await ctx.send(f"`{usu}` es un nombre **premium** de minecraft. ¿Estás seguro de querer usarlo?")
                            await chm.add_reaction("✅")
                            await chm.add_reaction("❌")
                            try:
                                reaction, user = await self.bot.wait_for('reaction_add', timeout=600.0, check=reaction_check)

                            except asyncio.TimeoutError:
                                # at this point, the check didn't become True, let's handle it.
                                err=discord.Embed(color=0xD7342A, description=f"**tiempo de espera de reaccion caducado**")
                                await chm.edit(content=ctx.author.mention, embed=err)
                                return
                            else:
                                if str(reaction.emoji) == "❌":
                                    await ctx.send("ingrese un nuevo usuario")
                                if str(reaction.emoji) == "✅":
                                    usuario_mc = usu
                                    looping = False


############################################################################################


        embed.description="_ _"
        embed.title="¿Eres parte activa de la comunidad? ¿Desde cuándo eres Gafapaster?"
        embed.set_footer(text="envía \"cancelar\" para cancelar y finalizar.")
        await ctx.send(ctx.author.mention, embed=embed)

        try:
            msg = await self.bot.wait_for(event = 'message', check = check, timeout = 600.0)

        except asyncio.TimeoutError:
            err=discord.Embed(color=0xD7342A, description=f"**Cancelado! No has respondido a tiempo.**")
            await ctx.send(ctx.author.mention, embed=err)
            return

        else:
            if msg.content.lower() == "cancelar":
                    err=discord.Embed(color=0xD7342A, description=f"**Cancelado!**")
                    await ctx.send(ctx.author.mention, embed=err)
                    return
            comunidad = msg.content

############################################################################################


        embed.title="¿Estás de acuerdo con las normas del server?"
        embed.description="_ _"
        chm = await ctx.send(ctx.author.mention, embed=embed)

        await chm.add_reaction("✅")
        await chm.add_reaction("❌")

        looping = True
        while looping == True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=600.0, check=reaction_check)

            except asyncio.TimeoutError:
                # at this point, the check didn't become True, let's handle it.
                err=discord.Embed(color=0xD7342A, description=f"**tiempo de espera de reaccion caducado**")
                await chm.edit(content=ctx.author.mention, embed=err)
                return
            else:
                if str(reaction.emoji) == "✅":
                    looping = False
                if str(reaction.emoji) == "❌":
                    await reaction.remove(ctx.author)


############################################################################################


        embed.description="_ _"
        embed.title="¿Qué crees que podrías aportar al servidor?"
        embed.set_footer(text="envía \"cancelar\" para cancelar y finalizar.")
        await ctx.send(ctx.author.mention, embed=embed)

        try:
            msg = await self.bot.wait_for(event = 'message', check = check, timeout = 600.0)

        except asyncio.TimeoutError:
            err=discord.Embed(color=0xD7342A, description=f"**Cancelado! No has respondido a tiempo.**")
            await ctx.send(ctx.author.mention, embed=err)
            return

        else:
            if msg.content.lower() == "cancelar":
                    err=discord.Embed(color=0xD7342A, description=f"**Cancelado!**")
                    await ctx.send(ctx.author.mention, embed=err)
                    return
            aporte = msg.content

        msg = await ctx.send('<a:loading:864708067496296468>')
        await msg.edit(content=f"""
```
USU TWITCH: {usuario}
LAUNCHER OFICIAL: {oficial}
NECESITA AYUDA: {ayuda}
USUARIO MC: {usuario_mc}
ACTIVO COM: {comunidad}
APORTE A COM: {aporte}
```
""")
        logm = await self.bot.get_channel(self.yaml_data['log_whitelist']).send(f"""
```
USU TWITCH: {usuario}
LAUNCHER OFICIAL: {oficial}
NECESITA AYUDA: {ayuda}
USUARIO MC: {usuario_mc}
ACTIVO COM: {comunidad}
APORTE A COM: {aporte}
```
""")
        await logm.add_reaction('➕')
        await logm.add_reaction('➖')

    @commands.command(aliases=['comando','cmd'])
    @commands.check_any(commands.is_owner(), commands.has_permissions(administrator=True))
    async def ejec(self, ctx, *, comando):
        resp = await execute_command(comando)
        if resp:
            await ctx.send(resp)
        else:
            await ctx.send('Ha ocurrido un error')


def setup(bot):
    bot.add_cog(form(bot))
