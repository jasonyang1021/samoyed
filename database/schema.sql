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
