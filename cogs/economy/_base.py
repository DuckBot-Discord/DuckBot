import asyncio
import contextlib
import datetime
import logging
import math
import os
import random
import typing
from collections import defaultdict
from typing import TYPE_CHECKING

import asyncpg
import discord
from discord import Interaction

from discord.ext import commands

from errors import (
    EconomyNotSetup,
    AccountNotFound,
    AccountAlreadyExists,
    EconomyOnCooldown,
    CooldownType,
    WalletInUse,
)

from helpers.time_inputs import human_timedelta

if TYPE_CHECKING:
    from bot import DuckBot
    from helpers.context import CustomContext
else:
    from discord.ext.commands import Bot as DuckBot, BadArgument
    from discord.ext.commands import Context as CustomContext


class EconomyBase(commands.Cog):
    def __init__(self, bot: DuckBot):
        self.symbols = ['💵', '💎', '🍇', '7️⃣', '🍉', '🍒', '\U0001fa99']
        self.bot = bot
        self.coin_name = "duckcoins"
        self.coin_emoji = "\U0001fa99"

        # Work messages
        self.work_messages = [
            "{coin} You worked hard and earned **{amount} {currency}**.",
            "{coin} You worked and earned **{amount} {currency}**.",
            "{coin} You sold your body and earned **{amount} {currency}**.",
            "{coin} You sold some bread and earned **{amount} {currency}**.",
            "{coin} Someone bought a beer from you for **{amount} {currency}**.",
            "{coin} You did some freelancing and earned **{amount} {currency}**.",
            "{coin} An artist bought your painting for **{amount} {currency}**.",
            "{coin} You sold your soul to the devil and earned **{amount} {currency}**.",
        ]

    @staticmethod
    def win_multiplier(bets) -> int:
        if len(set(bets)) == 1:
            return 2
        elif len(set(bets)) == 2:
            return 1
        else:
            return 0
