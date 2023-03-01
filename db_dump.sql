--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: modlogs; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA modlogs;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA public;


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- Name: ban; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.ban AS ENUM (
    'channel',
    'user',
    'guild'
);


--
-- Name: t_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.t_type AS ENUM (
    'user',
    'role'
);


--
-- Name: clear_inventory(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.clear_inventory() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
      -- Check if there is a new  
      IF ( TG_OP = 'DELETE' ) THEN
        DELETE FROM inventory WHERE user_id = OLD.user_id;
      ELSIF ( TG_OP = 'UPDATE' AND NEW.deleted IS TRUE ) THEN
        DELETE FROM inventory WHERE user_id = NEW.user_id;
      END IF;
      RETURN NULL;
    END;
  $$;


--
-- Name: pg_schema_size(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.pg_schema_size(text) RETURNS bigint
    LANGUAGE sql
    AS $_$
  select sum(pg_total_relation_size(quote_ident(schemaname) || '.' || quote_ident(tablename)))::bigint from pg_tables where schemaname = $1
  $_$;


--
-- Name: purge_inventory(bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.purge_inventory(to_delete_uid bigint) RETURNS bigint
    LANGUAGE plpgsql
    AS $$
  BEGIN
    DELETE FROM inventory
    WHERE user_id = to_delete_uid;
  END;
  $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ack; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ack (
    user_id bigint NOT NULL,
    description text
);


--
-- Name: addbot; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.addbot (
    owner_id bigint NOT NULL,
    bot_id bigint NOT NULL,
    added boolean DEFAULT false NOT NULL,
    pending boolean DEFAULT true NOT NULL
);


--
-- Name: afk; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.afk (
    user_id bigint NOT NULL,
    start_time timestamp with time zone,
    reason text,
    auto_un_afk boolean,
    raw_message boolean
);


--
-- Name: blacklist; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.blacklist (
    user_id bigint NOT NULL,
    is_blacklisted boolean DEFAULT true NOT NULL,
    reason text
);


--
-- Name: blackout; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.blackout (
    user_id bigint NOT NULL,
    roles bigint[] DEFAULT ARRAY[]::bigint[] NOT NULL
);


--
-- Name: bot_bans; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bot_bans (
    ban_type public.ban DEFAULT 'user'::public.ban NOT NULL,
    object_id bigint NOT NULL,
    reason text NOT NULL,
    end_time timestamp with time zone
);


--
-- Name: command_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.command_config (
    id integer NOT NULL,
    guild_id bigint,
    channel_id bigint,
    name text,
    whitelist boolean
);


--
-- Name: command_config_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.command_config_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: command_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.command_config_id_seq OWNED BY public.command_config.id;


--
-- Name: commands; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.commands (
    user_id bigint NOT NULL,
    guild_id bigint,
    command text NOT NULL,
    "timestamp" timestamp with time zone NOT NULL
);


--
-- Name: count_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.count_settings (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    current_number integer DEFAULT 1 NOT NULL,
    last_counter bigint,
    delete_messages boolean DEFAULT true NOT NULL,
    reset_on_fail boolean DEFAULT false NOT NULL
);


--
-- Name: counting; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.counting (
    guild_id bigint NOT NULL,
    reward_number integer NOT NULL,
    reward_message text,
    role_to_grant bigint,
    reaction_to_add text
);


--
-- Name: dm_modmail; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dm_modmail (
    user_id bigint NOT NULL,
    thread_id bigint
);


--
-- Name: economy; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.economy (
    user_id bigint NOT NULL,
    balance integer DEFAULT 200 NOT NULL,
    last_worked timestamp with time zone,
    last_daily timestamp with time zone,
    last_weekly timestamp with time zone,
    last_monthly timestamp with time zone,
    deleted boolean DEFAULT false NOT NULL
);


--
-- Name: emojis; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.emojis (
    emoji text,
    image bytea
);


--
-- Name: guilds; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.guilds (
    guild_id bigint NOT NULL,
    muted_id bigint,
    dj_id bigint,
    welcome_channel bigint,
    welcome_message text,
    snipe_enabled boolean DEFAULT false,
    modlog bigint,
    special_roles bigint[] DEFAULT ARRAY[]::bigint[] NOT NULL,
    until timestamp with time zone
);


--
-- Name: inv_whitelist; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inv_whitelist (
    uid bigint NOT NULL
);


--
-- Name: inventory; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inventory (
    user_id bigint NOT NULL,
    item_id bigint NOT NULL,
    amount integer NOT NULL
);


--
-- Name: inviter; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inviter (
    guild_id bigint NOT NULL,
    category bigint NOT NULL,
    text_channel bigint NOT NULL
);


--
-- Name: items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.items (
    item_id bigint,
    item_name text,
    price integer NOT NULL,
    stock integer DEFAULT 0 NOT NULL
);


--
-- Name: log_channels; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.log_channels (
    guild_id bigint NOT NULL,
    default_channel text,
    default_chid bigint NOT NULL,
    message_channel text,
    message_chid bigint,
    join_leave_channel text,
    join_leave_chid bigint,
    member_channel text,
    member_chid bigint,
    voice_channel text,
    voice_chid bigint,
    server_channel text,
    server_chid bigint
);


--
-- Name: logging_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.logging_events (
    guild_id bigint NOT NULL,
    message_delete boolean DEFAULT true NOT NULL,
    message_purge boolean DEFAULT true NOT NULL,
    message_edit boolean DEFAULT true NOT NULL,
    member_join boolean DEFAULT true NOT NULL,
    member_leave boolean DEFAULT true NOT NULL,
    member_update boolean DEFAULT true NOT NULL,
    user_ban boolean DEFAULT true NOT NULL,
    user_unban boolean DEFAULT true NOT NULL,
    user_update boolean DEFAULT true NOT NULL,
    invite_create boolean DEFAULT true NOT NULL,
    invite_delete boolean DEFAULT true NOT NULL,
    voice_join boolean DEFAULT true NOT NULL,
    voice_leave boolean DEFAULT true NOT NULL,
    voice_move boolean DEFAULT true NOT NULL,
    voice_mod boolean DEFAULT true NOT NULL,
    emoji_create boolean DEFAULT true NOT NULL,
    emoji_delete boolean DEFAULT true NOT NULL,
    emoji_update boolean DEFAULT true NOT NULL,
    sticker_create boolean DEFAULT true NOT NULL,
    sticker_delete boolean DEFAULT true NOT NULL,
    sticker_update boolean DEFAULT true NOT NULL,
    server_update boolean DEFAULT true NOT NULL,
    stage_open boolean DEFAULT true NOT NULL,
    stage_close boolean DEFAULT true NOT NULL,
    channel_create boolean DEFAULT true NOT NULL,
    channel_delete boolean DEFAULT true NOT NULL,
    channel_edit boolean DEFAULT true NOT NULL,
    role_create boolean DEFAULT true NOT NULL,
    role_delete boolean DEFAULT true NOT NULL,
    role_edit boolean DEFAULT true NOT NULL
);


--
-- Name: modlogs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.modlogs (
    guild_id bigint NOT NULL,
    case_id bigint NOT NULL,
    action text NOT NULL,
    reason text,
    offender bigint NOT NULL,
    moderator bigint,
    message_id bigint,
    log_date timestamp with time zone NOT NULL
);


--
-- Name: muted; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.muted (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL
);


--
-- Name: overwrites; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.overwrites (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    target_id bigint NOT NULL,
    target_type public.t_type NOT NULL,
    allow bigint NOT NULL,
    deny bigint NOT NULL
);


--
-- Name: pits; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pits (
    pit_id bigint NOT NULL,
    pit_owner bigint NOT NULL
);


--
-- Name: plonks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.plonks (
    id integer NOT NULL,
    guild_id bigint,
    entity_id bigint
);


--
-- Name: plonks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.plonks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: plonks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.plonks_id_seq OWNED BY public.plonks.id;


--
-- Name: pre; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pre (
    guild_id bigint NOT NULL,
    prefix text NOT NULL
);


--
-- Name: restarting; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.restarting (
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    restart_time timestamp with time zone
);


--
-- Name: suggestions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.suggestions (
    channel_id bigint NOT NULL,
    image_only boolean DEFAULT false NOT NULL
);


--
-- Name: temporary_mutes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.temporary_mutes (
    guild_id bigint NOT NULL,
    member_id bigint NOT NULL,
    reason text,
    end_time timestamp with time zone
);


--
-- Name: test_array; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.test_array (
    guild_id bigint NOT NULL,
    prefixes text[]
);


--
-- Name: test_table; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.test_table (
    guild_id bigint NOT NULL,
    case_id integer NOT NULL
);


--
-- Name: test_table_case_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.test_table_case_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: test_table_case_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.test_table_case_id_seq OWNED BY public.test_table.case_id;


--
-- Name: todo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.todo (
    user_id bigint NOT NULL,
    added_time timestamp with time zone NOT NULL,
    text text NOT NULL,
    jump_url text NOT NULL
);


--
-- Name: voice_channels; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.voice_channels (
    channel_id bigint NOT NULL,
    message_id bigint
);


--
-- Name: command_config id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.command_config ALTER COLUMN id SET DEFAULT nextval('public.command_config_id_seq'::regclass);


--
-- Name: plonks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plonks ALTER COLUMN id SET DEFAULT nextval('public.plonks_id_seq'::regclass);


--
-- Name: test_table case_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.test_table ALTER COLUMN case_id SET DEFAULT nextval('public.test_table_case_id_seq'::regclass);


--
-- Name: ack ack_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ack
    ADD CONSTRAINT ack_pkey PRIMARY KEY (user_id);


--
-- Name: addbot addbot_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.addbot
    ADD CONSTRAINT addbot_pkey PRIMARY KEY (owner_id, bot_id);


--
-- Name: afk afk_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.afk
    ADD CONSTRAINT afk_pkey PRIMARY KEY (user_id);


--
-- Name: blacklist blacklist_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.blacklist
    ADD CONSTRAINT blacklist_pkey PRIMARY KEY (user_id);


--
-- Name: bot_bans bot_bans_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bot_bans
    ADD CONSTRAINT bot_bans_pkey PRIMARY KEY (object_id);


--
-- Name: command_config command_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.command_config
    ADD CONSTRAINT command_config_pkey PRIMARY KEY (id);


--
-- Name: count_settings count_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.count_settings
    ADD CONSTRAINT count_settings_pkey PRIMARY KEY (guild_id);


--
-- Name: counting counting_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.counting
    ADD CONSTRAINT counting_pkey PRIMARY KEY (guild_id, reward_number);


--
-- Name: dm_modmail dm_modmail_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dm_modmail
    ADD CONSTRAINT dm_modmail_pkey PRIMARY KEY (user_id);


--
-- Name: dm_modmail dm_modmail_thread_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dm_modmail
    ADD CONSTRAINT dm_modmail_thread_id_key UNIQUE (thread_id);


--
-- Name: economy economy_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.economy
    ADD CONSTRAINT economy_pkey PRIMARY KEY (user_id);


--
-- Name: emojis emojis_emoji_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.emojis
    ADD CONSTRAINT emojis_emoji_key UNIQUE (emoji);


--
-- Name: inv_whitelist inv_whitelist_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inv_whitelist
    ADD CONSTRAINT inv_whitelist_pkey PRIMARY KEY (uid);


--
-- Name: inventory inventory_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory
    ADD CONSTRAINT inventory_pkey PRIMARY KEY (user_id, item_id);


--
-- Name: inviter inviter_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inviter
    ADD CONSTRAINT inviter_pkey PRIMARY KEY (guild_id);


--
-- Name: items items_item_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_item_id_key UNIQUE (item_id);


--
-- Name: items items_item_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_item_name_key UNIQUE (item_name);


--
-- Name: log_channels log_channels_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.log_channels
    ADD CONSTRAINT log_channels_pkey PRIMARY KEY (guild_id);


--
-- Name: logging_events logging_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.logging_events
    ADD CONSTRAINT logging_events_pkey PRIMARY KEY (guild_id);


--
-- Name: modlogs modlogs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.modlogs
    ADD CONSTRAINT modlogs_pkey PRIMARY KEY (guild_id, case_id);


--
-- Name: muted muted_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.muted
    ADD CONSTRAINT muted_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: overwrites overwrites_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.overwrites
    ADD CONSTRAINT overwrites_pkey PRIMARY KEY (guild_id, channel_id, target_id, target_type);


--
-- Name: pits pits_pit_owner_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pits
    ADD CONSTRAINT pits_pit_owner_key UNIQUE (pit_owner);


--
-- Name: pits pits_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pits
    ADD CONSTRAINT pits_pkey PRIMARY KEY (pit_id);


--
-- Name: plonks plonks_entity_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plonks
    ADD CONSTRAINT plonks_entity_id_key UNIQUE (entity_id);


--
-- Name: plonks plonks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.plonks
    ADD CONSTRAINT plonks_pkey PRIMARY KEY (id);


--
-- Name: pre pre_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pre
    ADD CONSTRAINT pre_pkey PRIMARY KEY (guild_id, prefix);


--
-- Name: guilds prefixes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.guilds
    ADD CONSTRAINT prefixes_pkey PRIMARY KEY (guild_id);


--
-- Name: restarting restarting_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.restarting
    ADD CONSTRAINT restarting_pkey PRIMARY KEY (channel_id, message_id);


--
-- Name: suggestions suggestions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.suggestions
    ADD CONSTRAINT suggestions_pkey PRIMARY KEY (channel_id);


--
-- Name: temporary_mutes temporary_mutes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.temporary_mutes
    ADD CONSTRAINT temporary_mutes_pkey PRIMARY KEY (guild_id, member_id);


--
-- Name: test_array test_array_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.test_array
    ADD CONSTRAINT test_array_pkey PRIMARY KEY (guild_id);


--
-- Name: test_table test_table_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.test_table
    ADD CONSTRAINT test_table_pkey PRIMARY KEY (guild_id, case_id);


--
-- Name: todo todo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.todo
    ADD CONSTRAINT todo_pkey PRIMARY KEY (user_id, text);


--
-- Name: voice_channels voice_channels_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.voice_channels
    ADD CONSTRAINT voice_channels_pkey PRIMARY KEY (channel_id);


--
-- Name: command_config_guild_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX command_config_guild_id_idx ON public.command_config USING btree (guild_id);


--
-- Name: plonks_entity_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX plonks_entity_id_idx ON public.plonks USING btree (entity_id);


--
-- Name: plonks_guild_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX plonks_guild_id_idx ON public.plonks USING btree (guild_id);


--
-- Name: economy on_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER on_delete AFTER DELETE OR UPDATE OF deleted ON public.economy FOR EACH ROW EXECUTE FUNCTION public.clear_inventory();


--
-- Name: count_settings fk_prefixes; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.count_settings
    ADD CONSTRAINT fk_prefixes FOREIGN KEY (guild_id) REFERENCES public.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: counting fk_prefixes; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.counting
    ADD CONSTRAINT fk_prefixes FOREIGN KEY (guild_id) REFERENCES public.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: logging_events fk_prefixes; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.logging_events
    ADD CONSTRAINT fk_prefixes FOREIGN KEY (guild_id) REFERENCES public.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: log_channels fk_prefixes; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.log_channels
    ADD CONSTRAINT fk_prefixes FOREIGN KEY (guild_id) REFERENCES public.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: inventory inventory_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory
    ADD CONSTRAINT inventory_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(item_id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

