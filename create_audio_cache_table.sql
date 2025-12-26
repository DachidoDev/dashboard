-- Create table to cache audio recordings for faster access
-- This table stores metadata about recordings to avoid querying Azure Blob Storage every time

CREATE TABLE IF NOT EXISTS audio_recordings_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL UNIQUE,
    organization TEXT NOT NULL,
    container TEXT NOT NULL,  -- 'recordings', 'processed-recordings', 'failedrecordings'
    status TEXT NOT NULL,  -- 'pending', 'processed', 'failed'
    size INTEGER,
    upload_timestamp TEXT,
    processed_timestamp TEXT,
    detected_language TEXT,
    language_code TEXT,
    audio_duration REAL,
    processing_time REAL,
    quality_rating TEXT DEFAULT 'unreviewed',
    has_transcription INTEGER DEFAULT 0,  -- 0 or 1
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_audio_cache_org_status ON audio_recordings_cache(organization, status);
CREATE INDEX IF NOT EXISTS idx_audio_cache_filename ON audio_recordings_cache(filename);
CREATE INDEX IF NOT EXISTS idx_audio_cache_updated ON audio_recordings_cache(last_updated);

-- Table to track when cache was last synced
CREATE TABLE IF NOT EXISTS audio_cache_sync (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization TEXT NOT NULL,
    container TEXT NOT NULL,
    last_sync_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    records_count INTEGER DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_sync_org_container ON audio_cache_sync(organization, container);

