CREATE TABLE labs (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE lab_profiles (
  lab_id UUID PRIMARY KEY REFERENCES labs(id),
  research_scope JSONB NOT NULL DEFAULT '{}'::jsonb,
  watchlist JSONB NOT NULL DEFAULT '{}'::jsonb,
  key_questions JSONB NOT NULL DEFAULT '[]'::jsonb,
  update_frequency TEXT NOT NULL DEFAULT 'daily'
);

CREATE TABLE sources (
  id UUID PRIMARY KEY,
  source_type TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT,
  published_at TIMESTAMPTZ,
  raw_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE changes (
  id UUID PRIMARY KEY,
  title TEXT NOT NULL,
  previous_state TEXT,
  current_state TEXT NOT NULL,
  change_summary TEXT NOT NULL,
  importance TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'detected',
  detected_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE change_evidence (
  change_id UUID REFERENCES changes(id),
  source_id UUID REFERENCES sources(id),
  evidence_text TEXT,
  PRIMARY KEY (change_id, source_id)
);

CREATE TABLE lab_change_interpretations (
  id UUID PRIMARY KEY,
  lab_id UUID NOT NULL REFERENCES labs(id),
  change_id UUID NOT NULL REFERENCES changes(id),
  relevance_score NUMERIC(5,2),
  interpretation TEXT NOT NULL,
  impact TEXT,
  follow_up TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(lab_id, change_id)
);
