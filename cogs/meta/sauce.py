import os
import inspect
from typing import Optional
from utils import DuckCog, command, DuckContext


class Sauce(DuckCog):
    @command(aliases=['source', 'src', 'github'])
    async def sauce(self, ctx: DuckContext, *, command: Optional[str]):
        """Displays my full source code or for a specific command.

        Parameters
        ----------
        command: Optional[str]
            The command to display the source code for.
        """
        source_url = 'https://github.com/LeoCx1000/discord-bots'
        branch = 'rewrite'
        if command is None:
            return await ctx.send(f"<{source_url}>")

        if command == 'help':
            src = type(self.bot.help_command)
            module = src.__module__
            filename = inspect.getsourcefile(src)
        else:
            obj = self.bot.get_command(command.replace('.', ' '))
            if obj is None:
                return await ctx.send('Could not find command.')
            elif obj.cog.__class__.__name__ in ('Jishaku', 'DuckBotJishaku'):
                return await ctx.send(
                    '<:jsk:984549118129111060> Jishaku, a debugging and utility extension for discord.py bots:'
                    '\nSee the full source here: <https://github.com/Gorialis/jishaku>'
                )

            # since we found the command we're looking for, presumably anyway, let's
            # try to access the code itself
            src = obj.callback.__code__
            module = obj.callback.__module__
            filename = src.co_filename

        try:
            lines, firstlineno = inspect.getsourcelines(src)
        except Exception as e:
            await ctx.send(f'**Could not retrieve source:**\n{e.__class__.__name__}:{e}')
            return
        if not module.startswith('discord'):
            # not a built-in command
            if filename is None:
                return await ctx.send('Could not find source for command.')

            location = os.path.relpath(filename).replace('\\', '/')
        else:
            location = module.replace('.', '/') + '.py'
            source_url = 'https://github.com/Rapptz/discord.py'
            branch = 'master'

        final_url = f'<{source_url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>'
        await ctx.send(final_url)
