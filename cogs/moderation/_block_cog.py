from typing import Optional

import discord
from discord.ext import commands

from utils import DuckCog, ActionNotExecutable


class BlockCog(DuckCog):

    async def toggle_block(
            self,
            channel: discord.abc.Messageable,
            member: discord.Member,
            blocked: bool = True,
            update_db: bool = True,
            reason: Optional[str] = None
    ) -> None:
        """|coro|

        Toggle the block status of a member in a channel.

        Parameters
        ----------
        channel : `discord.abc.Messageable`
            The channel to block/unblock the member in.
        member : `discord.Member`
            The member to block/unblock.
        blocked : `bool`, optional
            Whether to block or unblock the member. Defaults to ``True``, which means block.
        update_db : `bool`, optional
            Whether to update the database with the new block status.
        """
        if isinstance(channel, discord.abc.PrivateChannel):
            raise commands.NoPrivateMessage()

        if isinstance(channel, discord.Thread):
            channel = channel.parent  # type: ignore
            if not channel:
                raise ActionNotExecutable("Couldn't block! This thread has no parent channel... somehow.")

        val = False if blocked else None
        overwrites = channel.overwrites_for(member)
        try:
            await channel.set_permissions(
                member, reason=reason,
                overwrite=overwrites.update(
                    send_messages=val,
                    add_reactions=val,
                    create_public_threads=val,
                    create_private_threads=val,
                    send_messages_in_threads=val
                )
            )

        finally:
            if update_db:
                if blocked:
                    query = 'INSERT INTO blocks (guild_id, channel_id, user_id) VALUES ($1, $2, $3) ' \
                            'ON CONFLICT (guild_id, channel_id, user_id) DO NOTHING'
                else:
                    query = "DELETE FROM blocks WHERE guild_id = $1 AND channel_id = $2 AND user_id = $3"

                async with self.bot.safe_connection() as conn:
                    await conn.execute(query, channel.guild.id, channel.id, member.id)  # type: ignore
