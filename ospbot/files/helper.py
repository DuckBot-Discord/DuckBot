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
