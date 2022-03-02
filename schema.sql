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
)