import itertools

from discord.ext import tasks

from ._base import EventsBase


class Tasks(EventsBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.do_member_count_update.start()
        self.cache_common_discriminators.start()

    def cog_unload(self):
        self.do_member_count_update.cancel()
        self.cache_common_discriminators.cancel()

    @tasks.loop(minutes=30)
    async def do_member_count_update(self):
        if self.bot.user.id == 788278464474120202:
            await self.bot.top_gg.post_guild_count()
        else:
            print('User is not DuckBot! Did not post data to Top.gg')

    @tasks.loop(minutes=5)
    async def cache_common_discriminators(self):
        discrims = [[m.discriminator for m in g.members if
                     (m.premium_since or m.display_avatar.is_animated()) and (len(set(m.discriminator)) < 3)] for g in
                    self.bot.guilds]
        self.bot.common_discrims = sorted(list(set(itertools.chain(*discrims))))

    @cache_common_discriminators.before_loop
    @do_member_count_update.before_loop
    async def wait(self):
        await self.bot.wait_until_ready()
