import discord


def get_perms(permissions: discord.Permissions):
    if permissions.administrator:
        return ['Administrator']
    wanted_perms = dict({x for x in permissions if x[1] is True} - set(discord.Permissions(521942715969)))
    return [p.replace('_', ' ').replace('guild', 'server').title() for p in wanted_perms]
