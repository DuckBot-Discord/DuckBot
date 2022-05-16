import re
from typing import Tuple

import discord
from discord.app_commands import Transformer


__all__: Tuple[str, ...] = ("CleanContent",)

# noinspection PyShadowingBuiltins
class CleanContent(Transformer):
    def __init__(
        self,
        fix_channel_mentions: bool = True,
        escape_markdown: bool = True,
        remove_markdown: bool = True,
        use_nicknames: bool = True,
    ):
        self.fix_channel_mentions = fix_channel_mentions
        self.escape_markdown = escape_markdown
        self.remove_markdown = remove_markdown
        self.use_nicknames = use_nicknames

    async def transform(self, interaction: discord.Interaction, argument):
        msg = interaction.message

        if interaction.guild:

            def resolve_member(id: int) -> str:
                m = discord.utils.get(msg.mentions, id=id) or interaction.guild.get_member(id)
                return f'@{m.display_name if self.use_nicknames else m.name}' if m else '@deleted-user'

            def resolve_role(id: int) -> str:
                r = discord.utils.get(msg.role_mentions, id=id) or interaction.guild.get_role(id)
                return f'@{r.name}' if r else '@deleted-role'

        else:

            def resolve_member(id: int) -> str:
                m = discord.utils.get(msg.mentions, id=id) or interaction.client.get_user(id)
                return f'@{m.name}' if m else '@deleted-user'

            def resolve_role(id: int) -> str:
                return '@deleted-role'

        if self.fix_channel_mentions and interaction.guild:

            def resolve_channel(id: int) -> str:
                c = interaction.guild.get_channel(id)  # type: ignore
                return f'#{c.name}' if c else '#deleted-channel'

        else:

            def resolve_channel(id: int) -> str:
                return f'<#{id}>'

        transforms = {
            '@': resolve_member,
            '@!': resolve_member,
            '#': resolve_channel,
            '@&': resolve_role,
        }

        def repl(match: re.Match) -> str:
            type = match[1]
            id = int(match[2])
            transformed = transforms[type](id)
            return transformed

        result = re.sub(r'<(@[!&]?|#)([0-9]{15,20})>', repl, argument)
        if self.escape_markdown:
            result = discord.utils.escape_markdown(result)
        elif self.remove_markdown:
            result = discord.utils.remove_markdown(result)

        # Completely ensure no mentions escape:
        return discord.utils.escape_mentions(result)
