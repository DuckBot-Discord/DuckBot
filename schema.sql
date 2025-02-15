-- noinspection SpellCheckingInspectionForFile

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT PRIMARY KEY,
    prefixes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    muted_role_id BIGINT,
    muted_role_mode INT DEFAULT 0,
    min_join_age BIGINT,
    mutes BIGINT[] NOT NULL DEFAULT ARRAY[]::BIGINT[]
);

CREATE TABLE IF NOT EXISTS news (
    news_id BIGINT PRIMARY KEY,
    title VARCHAR(256) NOT NULL,
    content VARCHAR(1024) NOT NULL,
    author_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS timers (
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

DO $$ BEGIN
    CREATE TYPE blacklist_type AS ENUM ('guild', 'channel', 'user');
EXCEPTION
    WHEN duplicate_object THEN null;
END$$;


CREATE TABLE IF NOT EXISTS blacklist (
    blacklist_type blacklist_type,
    entity_id bigint,
    guild_id bigint NOT NULL default 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (blacklist_type, entity_id, guild_id)
);


CREATE TABLE IF NOT EXISTS badges (
    badge_id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    emoji TEXT NOT NULL
);

CREATE TABLE acknowledgements (
    user_id BIGINT,
    badge_id BIGINT REFERENCES badges(badge_id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, badge_id)
);

-- Functions that are dispatched to a listener
-- that updates the prefix cache automatically
CREATE OR REPLACE FUNCTION update_prefixes_cache()
  RETURNS TRIGGER AS $$
  BEGIN
    IF TG_OP = 'DELETE' THEN
      PERFORM pg_notify('delete_prefixes', NEW.guild_id::TEXT);
    ELSIF TG_OP = 'UPDATE' AND OLD.prefixes <> NEW.prefixes THEN
      PERFORM pg_notify('update_prefixes',
        JSON_BUILD_OBJECT(
              'guild_id', NEW.guild_id,
              'prefixes', NEW.prefixes
            )::TEXT
          );
    ELSIF TG_OP = 'INSERT' AND NEW.prefixes <> ARRAY[]::TEXT[] THEN
        PERFORM pg_notify('update_prefixes',
        JSON_BUILD_OBJECT(
              'guild_id', NEW.guild_id,
              'prefixes', NEW.prefixes
            )::TEXT
          );
    END IF;
    RETURN NEW;
  END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_prefixes_cache_trigger
  AFTER INSERT OR UPDATE OR DELETE
  ON guilds
  FOR EACH ROW
  EXECUTE PROCEDURE update_prefixes_cache();

-- For tags.
CREATE TABLE IF NOT EXISTS tags (
    id BIGSERIAL,
    name VARCHAR(200),
    content VARCHAR(2000),
    owner_id BIGINT,
    guild_id BIGINT,
    uses INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE
        NOT NULL DEFAULT NOW(),
    points_to BIGINT
        REFERENCES tags(id)
            ON DELETE CASCADE,
    embed JSONB,
    PRIMARY KEY (id),
    UNIQUE (name, guild_id),
    CONSTRAINT tags_mutually_excl_cnt_p_to CHECK (
            ((content IS NOT NULL OR embed IS NOT NULL) and points_to IS NULL)
            OR (points_to IS NOT NULL and (content IS NULL AND embed IS NULL))
        )
);

CREATE INDEX IF NOT EXISTS tags_name_ind ON tags (name);
CREATE INDEX IF NOT EXISTS tags_location_id_ind ON tags (guild_id);
-- noinspection SqlResolve
CREATE INDEX IF NOT EXISTS tags_name_trgm_ind ON tags USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS tags_name_lower_ind ON tags (LOWER(name));
CREATE UNIQUE INDEX IF NOT EXISTS tags_uniq_ind ON tags (LOWER(name), guild_id);

CREATE TABLE commands (
    user_id BIGINT NOT NULL,
    guild_id  BIGINT,
    command   TEXT NOT NULL ,
    timestamp TIMESTAMP WITH TIME ZONE
        NOT NULL DEFAULT NOW()
);

CREATE TABLE auto_sync (
    guild_id BIGINT,
    payload JSONB
);


CREATE TABLE user_settings (
    user_id BIGINT PRIMARY KEY,
    locale TEXT
);

CREATE TABLE dm_flow (
    user_id BIGINT PRIMARY KEY,
    dms_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    dm_channel BIGINT NULL,
    dm_webhook TEXT NULL
);

-- From https://github.com/Rapptz/RoboDanny/blob/rewrite/migrations/V1__Initial_migration.sql
CREATE TABLE IF NOT EXISTS plonks (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT,
    entity_id BIGINT UNIQUE
);

CREATE INDEX IF NOT EXISTS plonks_guild_id_idx ON plonks (guild_id);
CREATE INDEX IF NOT EXISTS plonks_entity_id_idx ON plonks (entity_id);

CREATE TABLE IF NOT EXISTS command_config (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT,
    channel_id BIGINT,
    name TEXT,
    whitelist BOOLEAN
);

CREATE INDEX IF NOT EXISTS command_config_guild_id_idx ON command_config (guild_id);
-- End