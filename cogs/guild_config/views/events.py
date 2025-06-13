import discord


class ModifyEvent(discord.ui.View):
    @discord.ui.button(label="Edit Content")
    async def edit_content(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button()
    async def edit_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass
