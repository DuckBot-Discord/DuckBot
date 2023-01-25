import asyncio
import logging
import os
from typing import Union

import aiohttp
import asyncpg
import discord
from asyncdagpi.image_features import ImageFeatures
from discord.ext import commands
import sentry_sdk

import errors
from cogs.economy.helper_classes import Wallet
from helpers.bot_base import BaseDuck, col, get_or_fail
from helpers.context import CustomContext

logging.basicConfig(
    level=logging.INFO,
    format=f"{col()}[{col(7)}%(asctime)s{col()} | {col(4)}%(name)s{col()}:{col(3)}%(levelname)s{col()}] %(message)s",
)

os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_HIDE"] = "True"
TOKEN = os.getenv("DISCORD_TOKEN")
target_type = Union[
    discord.Member,
    discord.User,
    discord.PartialEmoji,
    discord.Guild,
    discord.Invite,
    str,
]


class DuckBot(BaseDuck):
    async def create_gist(self, *, filename: str, description: str, content: str, public: bool = False):
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DuckBot-Discord",
            "Authorization": f'token {os.getenv("GH_TOKEN")}',
        }

        data = {
            "public": public,
            "files": {filename: {"content": content}},
            "description": description,
        }
        output = await self.session.request("POST", "https://api.github.com/gists", json=data, headers=headers)
        info = await output.json()
        return info["html_url"]

    async def get_welcome_channel(self, member: discord.Member):
        if not isinstance(member, discord.Member):
            raise errors.NoWelcomeChannel
        try:
            channel = self.welcome_channels[member.guild.id]
        except KeyError:
            raise errors.NoWelcomeChannel

        if not channel:
            raise errors.NoWelcomeChannel

        welcome_channel = member.guild.get_channel(channel) or (await member.guild.fetch_channel(channel))
        if not isinstance(welcome_channel, discord.TextChannel):
            self.welcome_channels[member.guild.id] = None
            raise errors.NoWelcomeChannel
        return welcome_channel

    async def dagpi_request(
        self,
        ctx: CustomContext,
        target: target_type,
        *,
        feature: ImageFeatures,
        **kwargs,
    ) -> discord.File:
        bucket = self.dagpi_cooldown.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            raise commands.CommandOnCooldown(commands.Cooldown(60, 60), retry_after, commands.BucketType.default)
        url = (
            getattr(target, "display_avatar", None)
            or getattr(target, "icon", None)
            or getattr(target, "guild", None)
            or target
        )
        url = getattr(getattr(url, "icon", url), "url", url)
        request = await self.dagpi_client.image_process(feature, url, **kwargs)
        return discord.File(fp=request.image, filename=f"DuckBot-{str(feature)}.{request.format}")

    # noinspection PyProtectedMember
    def update_log(self, deliver_type: str, webhook_url: str, guild_id: int):
        guild_id = getattr(guild_id, "id", guild_id)
        if deliver_type == "default":
            self.log_channels[guild_id]._replace(default=webhook_url)
        elif deliver_type == "message":
            self.log_channels[guild_id]._replace(message=webhook_url)
        elif deliver_type == "member":
            self.log_channels[guild_id]._replace(member=webhook_url)
        elif deliver_type == "join_leave":
            self.log_channels[guild_id]._replace(join_leave=webhook_url)
        elif deliver_type == "voice":
            self.log_channels[guild_id]._replace(voice=webhook_url)
        elif deliver_type == "server":
            self.log_channels[guild_id]._replace(server=webhook_url)

    async def get_wallet(self, user) -> Wallet:
        try:
            self.wallets[user.id]
        except KeyError:
            wallet = await Wallet.from_user(self, user)
            self.wallets[user.id] = wallet
        return self.wallets[user.id]


if __name__ == "__main__":
    sentry_sdk.init(
        get_or_fail("SENTRY_URL"),
        traces_sample_rate=1.0,
        environment=os.getenv("SENTRY_ENV") or 'development',
    )

    async def user_blacklisted(ctx: CustomContext):
        if not ctx.bot.blacklist.get(ctx.author.id, None) or await ctx.bot.is_owner(ctx.author):
            return True
        if ctx.command and ctx.command.root_parent and ctx.command.root_parent.name == "pit":
            return True
        raise errors.UserBlacklisted

    async def maintenance_mode(ctx: CustomContext):
        if not ctx.bot.maintenance or await ctx.bot.is_owner(ctx.author):
            return True
        else:
            raise errors.BotUnderMaintenance

    credentials = {
        "user": f"{get_or_fail('PSQL_USER')}",
        "password": f"{get_or_fail('PSQL_PASSWORD')}",
        "database": f"{get_or_fail('PSQL_DB')}",
        "host": f"{get_or_fail('PSQL_HOST')}",
        "port": f"{get_or_fail('PSQL_PORT')}",
    }

    async def runner():
        async with asyncpg.create_pool(**credentials) as pool, aiohttp.ClientSession() as session, DuckBot(
            pool, session
        ) as bot:
            bot.add_check(user_blacklisted)
            bot.add_check(maintenance_mode)
            await bot.start(TOKEN)

    asyncio.run(runner())
