import asyncpg
import discord
from utils import DuckCog, group


class BadgeManagement(DuckCog):
    @group(name='badges', aliases=['badge'], invoke_without_command=True)
    async def badges(self, ctx):
        """|coro|

        Displays all available badges.
        """
        badges = await self.bot.pool.fetch("SELECT badge_id, name, emoji FROM badges")
        to_send = []
        for badge_id, name, emoji in badges:
            to_send.append(f"**({badge_id})** {emoji} {name}")

        await ctx.send(embed=discord.Embed(title='All badges:', description="\n".join(to_send)))

    @badges.command(name='add', aliases=['create'])
    async def badges_add(self, ctx, emoji: str, *, name: str):
        """|coro|

        Adds a badge to the database.

        Parameters
        ----------
        emoji: discord.PartialEmoji
            The emoji to use for the badge.
        name: str
            The name of the badge.
        """
        badge_id = await self.bot.pool.fetchval(
            "INSERT INTO badges (name, emoji) VALUES ($1, $2) RETURNING badge_id", name, emoji
        )
        await ctx.send(f"Created badge with id {badge_id}:\n" f"> {emoji} {name}")

    @badges.command(name='delete')
    async def badges_delete(self, ctx, badge_id: int):
        """|coro|

        Removes a badge from the database.

        Parameters
        ----------
        badge_id: int
            The id of the badge to remove.
        """
        b_id = await self.bot.pool.fetchval("DELETE FROM badges WHERE badge_id = $1 RETURNING badge_id", badge_id)
        if b_id is not None:
            await ctx.send(f"Removed badge with id {badge_id}.")
        else:
            await ctx.send(f"There's no tag with id {badge_id}.")

    @badges.command(name='grant', aliases=['give'])
    async def badges_grant(self, ctx, user: discord.User, badge_id: int):
        """|coro|

        Adds a badge to a user.

        Parameters
        ----------
        user: :class:`discord.User`
            The user to give the badge to.
        badge_id: :class:`int`
            The ID of the badge.
        """
        try:
            await self.bot.pool.execute(
                "INSERT INTO acknowledgements (user_id, badge_id) VALUES ($1, $2) "
                "ON CONFLICT (user_id, badge_id) DO NOTHING ",
                user.id,
                badge_id,
            )
            await ctx.message.add_reaction("✅")
        except asyncpg.ForeignKeyViolationError:
            await ctx.send("That badge doesn't exist.")

    @badges.command(name='revoke', aliases=['remove'])
    async def badges_revoke(self, ctx, user: discord.User, badge_id: int):
        """|coro|

        Revokes a badge from a user

        Parameters
        ----------
        user: :class:`discord.User`
            The user to take the badge from.
        badge_id: :class:`int`
            The ID of the badge.
        """
        b_id = await self.bot.pool.execute(
            "DELETE FROM acknowledgements WHERE user_id = $1 AND badge_id = $2 RETURNING badge_id", user.id, badge_id
        )
        if b_id is not None:
            await ctx.message.add_reaction("✅")
        else:
            await ctx.message.add_reaction("❌")
