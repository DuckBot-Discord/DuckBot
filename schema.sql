CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT PRIMARY KEY,
    prefixes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    muted_role_id BIGINT,
    mutes BIGINT[] NOT NULL DEFAULT ARRAY[]::BIGINT[]
);

CREATE TABLE IF NOT EXISTS news (
    news_id BIGINT PRIMARY KEY,
    title VARCHAR(256) NOT NULL,
    content VARCHAR(1024) NOT NULL,
    author_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS timers(
    id BIGSERIAL PRIMARY KEY,
    precise BOOLEAN DEFAULT TRUE,
    event TEXT,
    extra JSONB,
    created TIMESTAMP,
    expires TIMESTAMP
);

CREATE TABLE IF NOT EXISTS blocks (
    guild_id BIGINT,
    channel_id BIGINT,
    user_id BIGINT,
    PRIMARY KEY (guild_id, channel_id, user_id)
);

-- Thanks chai :)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'blacklist_type ') THEN
        CREATE TYPE blacklist_type AS ENUM ('guild', 'channel', 'user');
    END IF;
END$$;


CREATE TABLE IF NOT EXISTS blacklist (
    blacklist_type blacklist_type,
    entity_id bigint,
    guild_id bigint NOT NULL default 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (blacklist_type, entity_id, guild_id)
);

-- not as important as roles. But still.
CREATE TABLE IF NOT EXISTS disabled_entities (
    guild_id BIGINT,
    entity_id BIGINT,
    PRIMARY KEY (guild_id, entity_id)
);

CREATE TABLE IF NOT EXISTS disabled_commands (
    guild_id BIGINT,
    entity_id BIGINT,
    command_name TEXT,
    PRIMARY KEY (guild_id, entity_id, command_name)
);
