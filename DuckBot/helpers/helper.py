

def get_perms(permissions):
    perms = []
    if permissions.administrator:
        perms.append("Administrator")
        return ["Administrator"]
    if permissions.manage_guild:
        perms.append("Manage Server")
    if permissions.ban_members:
        perms.append("Ban Members")
    if permissions.kick_members:
        perms.append("Kick Members")
    if permissions.manage_channels:
        perms.append("Manage Channels")
    if permissions.manage_threads:
        perms.append("Manage Threads")
    if permissions.manage_emojis_and_stickers:
        perms.append("Manage Emojis and Stickers")
    if permissions.manage_messages:
        perms.append("Manage Messages")
    if permissions.manage_permissions:
        perms.append("Manage Permissions")
    if permissions.manage_roles:
        perms.append("Manage Roles")
    if permissions.mention_everyone:
        perms.append("Mention Everyone")
    if permissions.manage_emojis:
        perms.append("Manage Emojis")
    if permissions.manage_webhooks:
        perms.append("Manage Webhooks")
    if permissions.manage_events:
        perms.append("Manage Events")
    if permissions.move_members:
        perms.append("Move Members")
    if permissions.mute_members:
        perms.append("Mute Members")
    if permissions.deafen_members:
        perms.append("Deafen Members")
    if permissions.priority_speaker:
        perms.append("Priority Speaker")
    if permissions.view_audit_log:
        perms.append("See Audit Log")
    if permissions.create_instant_invite:
        perms.append("Create Instant Invites")
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
        emoji_flags = f"{emoji_flags} <:bughunter_gold:850843414953984041>"  # not from bots.gg
    if flags['verified_bot_developer'] is True:
        emoji_flags = f"{emoji_flags} <:earlybotdev:850843591756349450>"  # not from bots.gg
    if emoji_flags == "":
        emoji_flags = None
    return emoji_flags
