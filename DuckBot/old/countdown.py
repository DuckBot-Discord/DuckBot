
import typing, discord, asyncio, random, datetime
from discord.ext import commands, tasks, timers
import datetime

class help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @tasks.loop(seconds=10.0)
    async def countdown(self):
        SECOND = 1
        MINUTE = 60 * SECOND
        HOUR = 60 * MINUTE
        DAY = 24 * HOUR
        MONTH = 30 * DAY
        def get_relative_time(dt):
            now = discord.utils.utcnow()
            delta_time = dt - now

            delta =  delta_time.days * DAY + delta_time.seconds
            minutes = delta / MINUTE
            hours = delta / HOUR
            days = delta / DAY

            if delta <  0:
                return ":tada: :tada: :tada:"



            if delta < 60 * MINUTE:
                return str(round(minutes, 2)) + " minutes to go"

            if delta < 24 * HOUR:
                return str(round(hours, 2)) + " hours to go"

            if delta < 48 * HOUR:
                return "yesterday"

            if delta < 30 * DAY:
                return str(round(days, 2)) + " days to go"

            if delta < 12 * MONTH:
                months = delta / MONTH
                if months <= 1:
                    return "one month to go"
                else:
                    return str(round(months, 2)) + " months to go"
            else:
              years = days / 365.0
              if  years <= 1:
                  return "one year to go"
              else:
                  return str(round(years, 2)) + " years to go"

        channel = self.bot.get_channel(798740083451625542)
        message = await channel.fetch_message(801991174352011276)
        await message.edit(content = "<@&798698824738668605> here's a countdown! \n:timer: " + get_relative_time(datetime.datetime(2021, 1, 22, 23)) )

def setup(bot):
    bot.add_cog(help(bot))
