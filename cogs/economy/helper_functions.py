import logging
from typing import TYPE_CHECKING

from discord.ext import commands

from errors import (
    EconomyNotSetup,
    EconomyOnCooldown,
    CooldownType,
)

if TYPE_CHECKING:
    from helpers.context import CustomContext
else:
    from discord.ext.commands import Context as CustomContext


def require_setup(prompt: bool = False):
    async def predicate(ctx: CustomContext):
        try:
            await ctx.get_wallet()
            if ctx.wallet.deleted:
                await ctx.wallet.delete()
            return True
        except Exception as e:
            raise EconomyNotSetup(prompt=prompt)

    return commands.check(predicate)


def refresh():
    async def predicate(ctx: CustomContext):
        if ctx.wallet:
            try:
                await ctx.wallet.refresh()
            except Exception as e:
                logging.error('Silently failed to refresh wallet for {}: {}'.format(ctx.author, e), exc_info=e)
        return True

    return commands.check(predicate)


def reset_cooldown(cooldown_type: CooldownType):
    async def predicate(ctx: CustomContext):
        wallet = ctx.wallet or await ctx.get_wallet()

        if cooldown_type == CooldownType.WORK:
            if not wallet.can_work:
                raise EconomyOnCooldown(cooldown_type, wallet.next_work)
            if ctx.invoked_with == 'work':
                await wallet.update_last_work()
            return True

        elif cooldown_type == CooldownType.DAILY:
            if not wallet.can_daily:
                raise EconomyOnCooldown(cooldown_type, wallet.next_daily)
            if ctx.invoked_with == 'daily':
                await wallet.update_last_daily()
            return True

        elif cooldown_type == CooldownType.WEEKLY:
            if not wallet.can_weekly:
                raise EconomyOnCooldown(cooldown_type, wallet.next_weekly)
            if ctx.invoked_with == 'weekly':
                await wallet.update_last_weekly()
            return True

        elif cooldown_type == CooldownType.MONTHLY:
            if not wallet.can_monthly:
                raise EconomyOnCooldown(cooldown_type, wallet.next_monthly)
            if ctx.invoked_with == 'monthly':
                await wallet.update_last_monthly()
            return True

        else:
            raise ValueError("Invalid cooldown type.")

    return commands.check(predicate)
