-- OIN observations are immutable capture events. Identical bytes at different capture times remain distinct Observations.
-- PostgreSQL names the original unnamed UNIQUE constraint from 001 as observations_observer_id_raw_content_hash_key.
ALTER TABLE observations DROP CONSTRAINT IF EXISTS observations_observer_id_raw_content_hash_key;
ALTER TABLE observations DROP CONSTRAINT IF EXISTS uq_observer_raw_hash;
