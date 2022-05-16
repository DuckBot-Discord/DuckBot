from discord.app_commands import AppCommandError
from utils.bases.errors import DuckBotException
from .. import human_join

from typing import Tuple

__all__: Tuple[str, ...] = (
    'InteractionError',
    'ActionNotExecutable',
    'PermissionsError',
)


class InteractionError(DuckBotException, AppCommandError):
    """
    Base class for all errors DuckBot errors.
    """

    __all__: Tuple[str, ...] = ()


class ActionNotExecutable(InteractionError):
    """
    The action is not executable.
    """

    def __init__(self, message: str):
        super().__init__(f"{message}")


class PermissionsError(InteractionError):
    """
    The invoker does not have the required permissions.
    """

    def __init__(self, missing: list = None, needed: list = None):
        self.missing: list = missing
        self.needed: list = needed
        message = "You"
        if missing:
            message += f"'re missing {human_join(missing, 'and')} permission(s)"
        if missing and needed:
            message += " and you"
        if needed:
            message += f" need {human_join(needed, 'and')} permission(s)"
        message += '.'
        super().__init__(message)


class BotPermissionsError(InteractionError):
    """
    The invoker does not have the required permissions.
    """

    def __init__(self, missing: list = None, needed: list = None):
        self.missing: list = missing
        self.needed: list = needed
        message = "I"
        if missing:
            message += f"'m missing **{human_join(missing, 'and')}** permission(s)"
        if missing and needed:
            message += " and"
        if needed:
            message += f" need **{human_join(needed, 'and')}** permission(s)"
        message += '.'
        super().__init__(message)
