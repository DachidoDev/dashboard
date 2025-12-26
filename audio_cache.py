"""
Audio Recordings Cache Module
Caches audio recording metadata in SQLite database for faster access
"""

import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Optional
from audio_monitor import AudioMonitor, Config

# Use the same database path as app.py
if os.environ.get("WEBSITE_INSTANCE_ID"):  # Running on Azure
    DB_PATH = "/home/site/data/fieldforce.db"
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
else:
    DB_PATH = "fieldforce.db"


def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_cache_tables():
    """Initialize cache tables if they don't exist"""
    conn = get_db_connection()
    try:
        with open('create_audio_cache_table.sql', 'r') as f:
            sql = f.read()
            conn.executescript(sql)
        conn.commit()
        print("✅ Audio cache tables initialized")
    except Exception as e:
        print(f"⚠️  Error initializing cache tables: {e}")
        # Create tables manually if SQL file not found
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audio_recordings_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                organization TEXT NOT NULL,
                container TEXT NOT NULL,
                status TEXT NOT NULL,
                size INTEGER,
                upload_timestamp TEXT,
                processed_timestamp TEXT,
                detected_language TEXT,
                language_code TEXT,
                audio_duration REAL,
                processing_time REAL,
                quality_rating TEXT DEFAULT 'unreviewed',
                has_transcription INTEGER DEFAULT 0,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audio_cache_org_status 
            ON audio_recordings_cache(organization, status)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audio_cache_filename 
            ON audio_recordings_cache(filename)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audio_cache_sync (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization TEXT NOT NULL,
                container TEXT NOT NULL,
                last_sync_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                records_count INTEGER DEFAULT 0,
                UNIQUE(organization, container)
            )
        """)
        conn.commit()
    finally:
        conn.close()


def sync_recordings_to_cache(organization: Optional[str] = None, force: bool = False):
    """
    Sync recordings from Azure Blob Storage to cache database
    organization: Filter by organization (None = all)
    force: Force sync even if recently synced
    """
    monitor = AudioMonitor()
    if not monitor.enabled:
        return {"error": "AudioMonitor not enabled"}
    
    init_cache_tables()
    conn = get_db_connection()
    
    try:
        containers = [
            ("recordings", "pending"),
            ("processed-recordings", "processed"),
            ("failedrecordings", "failed")
        ]
        
        org_prefix = f"{organization}/" if organization and organization != "dachido" else None
        
        total_synced = 0
        
        for container_name, status in containers:
            container = monitor.blob_client.get_container_client(container_name)
            synced_count = 0
            
            for blob in container.list_blobs():
                # Filter by organization
                if org_prefix and not blob.name.startswith(org_prefix):
                    continue
                
                # Extract organization from filename
                org = blob.name.split('/')[0] if '/' in blob.name else "unknown"
                
                # Check if audio file
                if not any(blob.name.endswith(ext) for ext in monitor.AUDIO_EXTENSIONS):
                    continue
                
                # Check if transcription exists
                has_transcription = monitor._has_transcription(blob.name)
                
                # Get metadata
                try:
                    blob_client = monitor.blob_client.get_blob_client(container_name, blob.name)
                    props = blob_client.get_blob_properties()
                    metadata = props.metadata or {}
                except:
                    metadata = {}
                
                # Insert or update cache
                conn.execute("""
                    INSERT OR REPLACE INTO audio_recordings_cache 
                    (filename, organization, container, status, size, upload_timestamp,
                     detected_language, language_code, audio_duration, processing_time,
                     quality_rating, has_transcription, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    blob.name,
                    org,
                    container_name,
                    status,
                    blob.size,
                    blob.last_modified.isoformat() if blob.last_modified else None,
                    metadata.get('detected_language'),
                    metadata.get('language_code'),
                    float(metadata.get('audio_duration', 0)) if metadata.get('audio_duration') else None,
                    float(metadata.get('processing_time', 0)) if metadata.get('processing_time') else None,
                    metadata.get('quality_rating', 'unreviewed'),
                    1 if has_transcription else 0,
                    datetime.now().isoformat()
                ))
                synced_count += 1
            
            # Update sync timestamp
            conn.execute("""
                INSERT OR REPLACE INTO audio_cache_sync 
                (organization, container, last_sync_timestamp, records_count)
                VALUES (?, ?, ?, ?)
            """, (
                organization or "all",
                container_name,
                datetime.now().isoformat(),
                synced_count
            ))
            
            total_synced += synced_count
        
        conn.commit()
        return {"synced": total_synced, "organization": organization or "all"}
    
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        conn.close()


def get_recordings_from_cache(organization: str, status: str, limit: int = 100, offset: int = 0) -> Dict:
    """
    Get recordings from cache database
    Much faster than querying Azure Blob Storage
    """
    conn = get_db_connection()
    
    try:
        # Get total count
        count_query = """
            SELECT COUNT(*) as total 
            FROM audio_recordings_cache 
            WHERE organization = ? AND status = ?
        """
        total = conn.execute(count_query, (organization, status)).fetchone()['total']
        
        # Get paginated results
        query = """
            SELECT * FROM audio_recordings_cache 
            WHERE organization = ? AND status = ?
            ORDER BY upload_timestamp DESC
            LIMIT ? OFFSET ?
        """
        rows = conn.execute(query, (organization, status, limit, offset)).fetchall()
        
        recordings = []
        for row in rows:
            recordings.append({
                'filename': row['filename'],
                'size': row['size'],
                'upload_timestamp': row['upload_timestamp'],
                'detected_language': row['detected_language'],
                'language_code': row['language_code'],
                'audio_duration': row['audio_duration'],
                'processing_time': row['processing_time'],
                'quality_rating': row['quality_rating'],
                'has_transcription': bool(row['has_transcription'])
            })
        
        return {
            'recordings': recordings,
            'total': total,
            'limit': limit,
            'offset': offset
        }
    
    except Exception as e:
        return {'error': str(e), 'recordings': [], 'total': 0}
    finally:
        conn.close()


def should_sync_cache(organization: str, container: str, max_age_minutes: int = 5) -> bool:
    """Check if cache needs to be synced"""
    conn = get_db_connection()
    try:
        row = conn.execute("""
            SELECT last_sync_timestamp 
            FROM audio_cache_sync 
            WHERE organization = ? AND container = ?
        """, (organization, container)).fetchone()
        
        if not row:
            return True  # Never synced
        
        last_sync = datetime.fromisoformat(row['last_sync_timestamp'])
        age = (datetime.now() - last_sync).total_seconds() / 60
        
        return age > max_age_minutes
    
    except:
        return True  # Error, sync anyway
    finally:
        conn.close()

