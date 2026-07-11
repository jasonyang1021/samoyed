CREATE TABLE labs (
  id VARCHAR(64) PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE lab_profiles (
  lab_id VARCHAR(64) PRIMARY KEY REFERENCES labs(id),
  research_scope JSONB NOT NULL DEFAULT '{}'::jsonb,
  watchlist JSONB NOT NULL DEFAULT '{}'::jsonb,
  key_questions JSONB NOT NULL DEFAULT '[]'::jsonb,
  update_frequency VARCHAR(32) NOT NULL DEFAULT 'daily'
);

CREATE TABLE sources (
  id VARCHAR(64) PRIMARY KEY,
  source_type VARCHAR(64) NOT NULL,
  title TEXT NOT NULL,
  url TEXT,
  published_at TIMESTAMPTZ,
  raw_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE watch_items (
  id VARCHAR(64) PRIMARY KEY,
  kind VARCHAR(32) NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  is_following BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE documents (
  id VARCHAR(64) PRIMARY KEY,
  source_id VARCHAR(64) NOT NULL REFERENCES sources(id),
  canonical_url TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  content_text TEXT NOT NULL,
  authors JSONB NOT NULL DEFAULT '[]'::jsonb,
  content_level VARCHAR(32) NOT NULL DEFAULT 'metadata',
  published_at TIMESTAMPTZ,
  fetched_at TIMESTAMPTZ NOT NULL,
  content_fingerprint VARCHAR(64) NOT NULL UNIQUE,
  status VARCHAR(32) NOT NULL DEFAULT 'new',
  raw_metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE analyses (
  id VARCHAR(64) PRIMARY KEY,
  document_id VARCHAR(64) NOT NULL UNIQUE REFERENCES documents(id),
  relevance_score NUMERIC(5,2) NOT NULL,
  is_relevant BOOLEAN NOT NULL,
  category VARCHAR(32) NOT NULL,
  matched_entities JSONB NOT NULL DEFAULT '[]'::jsonb,
  extracted_facts JSONB NOT NULL DEFAULT '[]'::jsonb,
  summary TEXT NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'completed',
  analyzed_at TIMESTAMPTZ NOT NULL,
  raw_result JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE radar_runs (
  id VARCHAR(64) PRIMARY KEY,
  started_at TIMESTAMPTZ NOT NULL,
  finished_at TIMESTAMPTZ,
  status VARCHAR(32) NOT NULL,
  source_count INTEGER NOT NULL DEFAULT 0,
  documents_fetched INTEGER NOT NULL DEFAULT 0,
  documents_created INTEGER NOT NULL DEFAULT 0,
  analyzed INTEGER NOT NULL DEFAULT 0,
  relevant INTEGER NOT NULL DEFAULT 0,
  generated_changes INTEGER NOT NULL DEFAULT 0,
  errors JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE radar_settings (
  id VARCHAR(32) PRIMARY KEY,
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  run_time VARCHAR(5) NOT NULL DEFAULT '08:00',
  timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Tokyo',
  last_run_date VARCHAR(10),
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE entity_states (
  id VARCHAR(64) PRIMARY KEY,
  entity_type VARCHAR(64) NOT NULL,
  entity_name TEXT NOT NULL,
  state_summary TEXT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  source_id VARCHAR(64) REFERENCES sources(id),
  raw_metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE changes (
  id VARCHAR(64) PRIMARY KEY,
  title TEXT NOT NULL,
  new_facts JSONB NOT NULL DEFAULT '[]'::jsonb,
  previous_state TEXT NOT NULL,
  current_state TEXT NOT NULL,
  change_summary TEXT NOT NULL,
  importance VARCHAR(1) NOT NULL,
  evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
  next_watch_points JSONB NOT NULL DEFAULT '[]'::jsonb,
  watch_item_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  status VARCHAR(32) NOT NULL DEFAULT 'detected',
  detected_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE lab_change_interpretations (
  id VARCHAR(64) PRIMARY KEY,
  lab_id VARCHAR(64) NOT NULL REFERENCES labs(id),
  change_id VARCHAR(64) NOT NULL REFERENCES changes(id),
  relevance_score NUMERIC(5,2),
  why_relevant TEXT NOT NULL,
  impact TEXT NOT NULL,
  next_watch_points JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL,
  CONSTRAINT uq_lab_change_interpretation UNIQUE(lab_id, change_id)
);
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(128) PRIMARY KEY,
    email VARCHAR(320) NOT NULL UNIQUE,
    name TEXT,
    picture TEXT,
    role VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS lab_memberships (
    user_id VARCHAR(128) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    lab_id VARCHAR(64) NOT NULL REFERENCES labs(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, lab_id)
);

CREATE TABLE IF NOT EXISTS lab_invitations (
    id VARCHAR(64) PRIMARY KEY,
    email VARCHAR(320) NOT NULL,
    lab_id VARCHAR(64) NOT NULL REFERENCES labs(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL,
    invited_by VARCHAR(128) REFERENCES users(id),
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS lab_watch_items (
    lab_id VARCHAR(64) NOT NULL REFERENCES labs(id) ON DELETE CASCADE,
    watch_item_id VARCHAR(64) NOT NULL REFERENCES watch_items(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (lab_id, watch_item_id)
);
