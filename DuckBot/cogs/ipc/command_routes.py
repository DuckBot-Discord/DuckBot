import inspect

from ._base import IpcBase


class CommandRoutes(IpcBase):

    async def get_command(self, data) -> dict:
        command_name = data.command
        command = self.bot.get_command(command_name)
        if not command:
            return {'error': f'Command {command_name} not found'}

        try:
            source_lines, _ = inspect.getsourcelines(command.callback)
        except (TypeError, OSError):
            return {'error': f'Command {command_name} has no source'}

        source_text = ''.join(source_lines)

        return {'command_name': command.qualified_name, 'source_text': source_text}
