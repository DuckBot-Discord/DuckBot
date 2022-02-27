from ._base import IpcBase


class GuildRoutes(IpcBase):

    async def get_stats(self, _) -> dict:
        return {
            'guilds': len(self.bot.guilds),
            'users': len(self.bot.users),
            'channels': self.channel_count,
            'bot_owner': getattr(self.bot.get_user(self.bot.owner_id), 'name', 'Could not resolve owner'),
        }
