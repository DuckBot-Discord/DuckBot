

CREATE TABLE event_notifications (
    event_id SERIAL PRIMARY KEY,
    guild_id BIGINT REFERENCES guilds(guild_id) ON DELETE CASCADE,
    channel_id BIGINT,
    content TEXT,
    embed JSONB,
    condition INT,
    condition_data JSONB
);

CREATE TABLE user_notification_data (
    user_id BIGINT,
    event_id BIGINT REFERENCES event_notifications(event_id) ON DELETE CASCADE,
    condition_data JSONB
);