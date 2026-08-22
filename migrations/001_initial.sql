-- OIN MVP metadata schema. Raw WARC/WACZ artifacts are stored through StorageBackend, never in PostgreSQL.
CREATE TABLE IF NOT EXISTS observers (
    observer_id TEXT PRIMARY KEY,
    public_key TEXT NOT NULL UNIQUE,
    key_algorithm VARCHAR(32) NOT NULL CHECK (key_algorithm = 'Ed25519'),
    created_at TIMESTAMPTZ NOT NULL,
    operator_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    key_status VARCHAR(16) NOT NULL DEFAULT 'active' CHECK (key_status IN ('active','revoked','compromised','retired')),
    replacement_observer_id TEXT NULL
);

CREATE TABLE IF NOT EXISTS independence_profiles (
    observer_id TEXT PRIMARY KEY REFERENCES observers(observer_id),
    profile JSONB NOT NULL,
    risk_score SMALLINT NULL CHECK (risk_score BETWEEN 0 AND 100),
    score_method TEXT NULL,
    attested_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS objects (
    object_id TEXT PRIMARY KEY,
    canonical_url TEXT NOT NULL UNIQUE,
    original_url TEXT NOT NULL,
    resource_type VARCHAR(32) NOT NULL,
    semantic_identifiers JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_objects_resource_type ON objects(resource_type);

CREATE TABLE IF NOT EXISTS observations (
    observation_id TEXT PRIMARY KEY,
    object_id TEXT NOT NULL REFERENCES objects(object_id),
    observer_id TEXT NOT NULL REFERENCES observers(observer_id),
    captured_at TIMESTAMPTZ NOT NULL,
    raw_content_hash TEXT NOT NULL,
    raw_content_reference TEXT NOT NULL,
    archive_format VARCHAR(16) NOT NULL CHECK (archive_format IN ('warc','wacz')),
    manifest JSONB NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_observations_object_time ON observations(object_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_observations_observer_time ON observations(observer_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_observations_hash ON observations(raw_content_hash);

CREATE TABLE IF NOT EXISTS signatures (
    observation_id TEXT PRIMARY KEY REFERENCES observations(observation_id),
    algorithm VARCHAR(32) NOT NULL CHECK (algorithm = 'Ed25519'),
    signature TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS timestamps (
    id BIGSERIAL PRIMARY KEY,
    observation_id TEXT NOT NULL REFERENCES observations(observation_id),
    kind VARCHAR(32) NOT NULL,
    evidence JSONB NOT NULL,
    verified BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS idx_timestamps_observation ON timestamps(observation_id);

CREATE TABLE IF NOT EXISTS storage_refs (
    id BIGSERIAL PRIMARY KEY,
    observation_id TEXT NOT NULL REFERENCES observations(observation_id),
    backend VARCHAR(64) NOT NULL,
    locator TEXT NOT NULL,
    verified_at TIMESTAMPTZ NULL,
    UNIQUE (observation_id, backend, locator)
);
CREATE INDEX IF NOT EXISTS idx_storage_refs_observation ON storage_refs(observation_id);

CREATE TABLE IF NOT EXISTS log_entries (
    observation_id TEXT PRIMARY KEY REFERENCES observations(observation_id),
    log_id TEXT NOT NULL,
    leaf_index BIGINT NOT NULL,
    checkpoint JSONB NOT NULL,
    proof JSONB NOT NULL,
    UNIQUE (log_id, leaf_index)
);

CREATE TABLE IF NOT EXISTS conflicts (
    id BIGSERIAL PRIMARY KEY,
    object_id TEXT NOT NULL REFERENCES objects(object_id),
    observation_a_id TEXT NOT NULL REFERENCES observations(observation_id),
    observation_b_id TEXT NOT NULL REFERENCES observations(observation_id),
    classification VARCHAR(32) NOT NULL CHECK (classification IN ('identical_content','temporal_variation','observation_divergence','replication_difference')),
    is_conflict_candidate BOOLEAN NOT NULL DEFAULT false,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (observation_a_id, observation_b_id),
    CHECK (observation_a_id < observation_b_id)
);
CREATE INDEX IF NOT EXISTS idx_conflicts_object ON conflicts(object_id, classification);

CREATE TABLE IF NOT EXISTS replicas (
    id BIGSERIAL PRIMARY KEY,
    observation_id TEXT NOT NULL REFERENCES observations(observation_id),
    peer_id TEXT NOT NULL,
    status VARCHAR(32) NOT NULL CHECK (status IN ('advertised','pulling','verified','failed','missing')),
    verified_at TIMESTAMPTZ NULL,
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (observation_id, peer_id)
);
CREATE INDEX IF NOT EXISTS idx_replicas_peer_status ON replicas(peer_id, status);
