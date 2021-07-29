import discord, asyncio, json, yaml

def get_perms(permissions):
    perms = []
    if permissions.administrator:
        perms.append("Administrator")
        return ["Administrator"]
    if permissions.manage_guild:
        perms.append("Manage guild")
    if permissions.ban_members:
        perms.append("Ban members")
    if permissions.kick_members:
        perms.append("Kick members")
    if permissions.manage_channels:
        perms.append("Manage channels")
    if permissions.manage_emojis:
        perms.append("Manage custom emotes")
    if permissions.manage_messages:
        perms.append("Manage messages")
    if permissions.manage_permissions:
        perms.append("Manage permissions")
    if permissions.manage_roles:
        perms.append("Manage roles")
    if permissions.mention_everyone:
        perms.append("Mention everyone")
    if permissions.manage_emojis:
        perms.append("Manage emojis")
    if permissions.manage_webhooks:
        perms.append("Manage webhooks")
    if permissions.move_members:
        perms.append("Move members")
    if permissions.mute_members:
        perms.append("Mute members")
    if permissions.deafen_members:
        perms.append("Deafen members")
    if permissions.priority_speaker:
        perms.append("Priority speaker")
    if permissions.view_audit_log:
        perms.append("See audit log")
    if permissions.create_instant_invite:
        perms.append("Create instant invites")
    if len(perms) == 0:
        return None
    return perms


def get_user_badges(user):
    author_flags = user.public_flags
    flags = dict(author_flags)
    emoji_flags = ""
    if flags['staff'] is True:
        emoji_flags = f"{emoji_flags} <:staff:314068430787706880>"
    if flags['partner'] is True:
        emoji_flags = f"{emoji_flags} <:partnernew:754032603081998336>"
    if flags['hypesquad'] is True:
        emoji_flags = f"{emoji_flags} <:hypesquad:314068430854684672>"
    if flags['bug_hunter'] is True:
        emoji_flags = f"{emoji_flags} <:bughunter:585765206769139723>"
    if flags['hypesquad_bravery'] is True:
        emoji_flags = f"{emoji_flags} <:bravery:585763004218343426>"
    if flags['hypesquad_brilliance'] is True:
        emoji_flags = f"{emoji_flags} <:brilliance:585763004495298575>"
    if flags['hypesquad_balance'] is True:
        emoji_flags = f"{emoji_flags} <:balance:585763004574859273>"
    if flags['early_supporter'] is True:
        emoji_flags = f"{emoji_flags} <:supporter:585763690868113455>"
    if user.premium_since:
        emoji_flags = f"{emoji_flags} <:booster4:585764446178246657>"
    if flags['bug_hunter_level_2'] is True:
        emoji_flags = f"{emoji_flags} <:bughunter_gold:850843414953984041>" #not from bots.gg
    if flags['verified_bot_developer'] is True:
        emoji_flags = f"{emoji_flags} <:earlybotdev:850843591756349450>" #not from bots.gg
    if emoji_flags == "": emoji_flags = None
    return emoji_flags
