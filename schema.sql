CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT PRIMARY KEY,
    prefixes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[]
);