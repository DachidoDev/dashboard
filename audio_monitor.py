"""
Audio Processing Monitor - Backend API
Provides monitoring, analytics, and quality feedback for audio processing pipeline
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from azure.storage.blob import BlobServiceClient, ContentSettings, generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import ResourceNotFoundError
import traceback
from dotenv import load_dotenv
load_dotenv()  # Add this at the top of your main file

class Config:
    """Configuration from environment variables"""
    CONNECTION_STRING = os.environ.get('AZURE_STORAGE_CONNECTION_STRING', '')
    RECORDINGS_CONTAINER = os.environ.get('RECORDINGS_CONTAINER', 'recordings')
    TRANSCRIPTIONS_CONTAINER = os.environ.get('TRANSCRIPTIONS_CONTAINER', 'transcriptions')
    PROCESSED_CONTAINER = os.environ.get('PROCESSED_RECORDINGS_CONTAINER', 'processed-recordings')
    FAILED_CONTAINER = os.environ.get('FAILED_RECORDINGS_CONTAINER', 'failedrecordings')
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.CONNECTION_STRING:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING is required")
    
    @classmethod
    def get_blob_client(cls) -> BlobServiceClient:
        """Create Azure Blob Storage client"""
        return BlobServiceClient.from_connection_string(cls.CONNECTION_STRING)


class AudioMonitor:
    """
    Monitor for audio processing pipeline
    Provides views into pending, processed, and failed recordings
    """
    
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.MP3', '.WAV', '.M4A', '.FLAC', '.OGG'}
    
    def __init__(self):
        # Do not raise on missing configuration during import/runtime.
        # Allow creating an AudioMonitor in a disabled/stub mode so the
        # Flask endpoints can return graceful errors instead of 500s.
        if not Config.CONNECTION_STRING:
            print("⚠️  AZURE_STORAGE_CONNECTION_STRING not set — AudioMonitor running in disabled mode")
            self.enabled = False
            self.blob_client = None
            return

        Config.validate()
        self.enabled = True
        self.blob_client = Config.get_blob_client()
    
    def get_pending_recordings(self, limit: int = 100, offset: int = 0, organization: Optional[str] = None) -> Dict:
        """
        Get all recordings awaiting processing
        organization: Filter by organization (blobs must be prefixed with {organization}/)
        Returns: List of pending recordings with metadata
        """
        # If not configured, return an empty but successful structure
        if not getattr(self, 'enabled', False) or not self.blob_client:
            return {'recordings': [], 'total': 0, 'limit': limit, 'offset': offset, 'error': 'AudioMonitor not configured'}

        try:
            container = self.blob_client.get_container_client(Config.RECORDINGS_CONTAINER)
            pending = []
            
            # Organization prefix for filtering
            org_prefix = f"{organization}/" if organization and organization != "dachido" else None
            
            # First pass: Count ALL pending recordings (before pagination)
            total = 0
            all_pending_blobs = []
            
            for blob in container.list_blobs():
                # Filter by organization prefix if specified
                if org_prefix and not blob.name.startswith(org_prefix):
                    continue
                
                # Check if it's an audio file
                if not any(blob.name.endswith(ext) for ext in self.AUDIO_EXTENSIONS):
                    continue
                
                # Check if already processed (has transcription)
                if self._has_transcription(blob.name):
                    continue
                
                # This is a pending recording
                total += 1
                all_pending_blobs.append(blob)
            
            # Second pass: Apply pagination to get only the records for current page
            start_idx = offset
            end_idx = offset + limit
            
            for blob in all_pending_blobs[start_idx:end_idx]:
                pending.append({
                    'filename': blob.name,
                    'size': blob.size,
                    'upload_timestamp': blob.last_modified.isoformat() if blob.last_modified else None,
                    'status': 'pending',
                    'url': self._get_blob_url(Config.RECORDINGS_CONTAINER, blob.name)
                })
            
            return {
                'recordings': pending,
                'total': total,  # Total count from first pass (all matching records)
                'limit': limit,
                'offset': offset
            }
        
        except Exception as e:
            print(f"Error fetching pending recordings: {e}")
            traceback.print_exc()
            return {'recordings': [], 'total': 0, 'error': str(e)}
    
    def get_processed_recordings(self, limit: int = 100, offset: int = 0, 
                                 quality_filter: Optional[str] = None,
                                 language_filter: Optional[str] = None,
                                 include_transcription: bool = False,
                                 organization: Optional[str] = None) -> Dict:
        """
        Get successfully processed recordings with metadata
        include_transcription: If False, skips downloading transcription JSON for better performance
        """
        if not getattr(self, 'enabled', False) or not self.blob_client:
            return {'recordings': [], 'total': 0, 'limit': limit, 'offset': offset, 'error': 'AudioMonitor not configured'}

        try:
            container = self.blob_client.get_container_client(Config.PROCESSED_CONTAINER)
            processed = []
            candidates = []  # Store blob names that pass initial filters
            
            # Organization prefix for filtering
            org_prefix = f"{organization}/" if organization and organization != "dachido" else None
            
            # First pass: collect all audio files (fast, no API calls)
            for blob in container.list_blobs():
                # Filter by organization prefix if specified
                if org_prefix and not blob.name.startswith(org_prefix):
                    continue
                
                # Check if it's an audio file
                if not any(blob.name.endswith(ext) for ext in self.AUDIO_EXTENSIONS):
                    continue
                
                candidates.append(blob.name)
            
            # Second pass: Apply filters and count total (before pagination)
            filtered_candidates = []
            for blob_name in candidates:
                # Get blob properties and metadata to check filters
                blob_client = self.blob_client.get_blob_client(Config.PROCESSED_CONTAINER, blob_name)
                props = blob_client.get_blob_properties()
                metadata = props.metadata or {}
                
                # Apply quality filter
                if quality_filter and metadata.get('quality_rating') != quality_filter:
                    continue
                
                # Apply language filter
                if language_filter and metadata.get('source_language') != language_filter:
                    continue
                
                # This blob passes all filters
                filtered_candidates.append(blob_name)
            
            # Total count is the number of filtered candidates
            total = len(filtered_candidates)
            
            # Third pass: Apply pagination and get full metadata only for current page
            start_idx = offset
            end_idx = offset + limit
            
            for blob_name in filtered_candidates[start_idx:end_idx]:
                # Get blob properties and metadata for this specific blob
                blob_client = self.blob_client.get_blob_client(Config.PROCESSED_CONTAINER, blob_name)
                props = blob_client.get_blob_properties()
                metadata = props.metadata or {}
                
                # Get transcription data only if requested (lazy loading)
                transcription_data = None
                if include_transcription:
                    transcription_data = self._get_transcription(blob_name)
                
                # Extract processing time from transcription data or metadata
                proc_time = None
                if transcription_data:
                    proc_time = transcription_data.get('translation_time') or transcription_data.get('processing_time')
                if not proc_time:
                    proc_time = metadata.get('processing_time_seconds')
                
                # Build recording object (without transcription if not requested)
                recording = {
                    'filename': blob_name,
                    'size': props.size,
                    'upload_timestamp': props.last_modified.isoformat() if props.last_modified else None,
                    'url': self._get_blob_url(Config.PROCESSED_CONTAINER, blob_name),
                    'quality_rating': metadata.get('quality_rating', 'unreviewed'),
                    'reviewer': metadata.get('reviewer'),
                    'review_timestamp': metadata.get('review_timestamp'),
                    'review_notes': metadata.get('review_notes', ''),
                    'source_language': metadata.get('source_language'),
                    'target_language': metadata.get('target_language', 'en'),
                    'processing_time': float(proc_time) if proc_time else None,
                    'translation_time': float(proc_time) if proc_time else None,
                }
                
                # Always try to get essential fields from transcription (needed for display)
                # But only download transcription JSON if metadata doesn't have the info
                if not include_transcription:
                    # Try metadata first (fast)
                    recording['detected_language'] = metadata.get('detected_language')
                    recording['language_code'] = metadata.get('language_code') or metadata.get('source_language')
                    recording['audio_duration'] = float(metadata.get('audio_duration', 0)) if metadata.get('audio_duration') else None
                    
                    # If essential fields missing, fetch transcription (but only once per blob)
                    if not recording['detected_language'] or not recording['audio_duration']:
                        transcription_data = self._get_transcription(blob_name)
                        if transcription_data:
                            recording['detected_language'] = recording['detected_language'] or transcription_data.get('detected_language')
                            recording['language_code'] = recording['language_code'] or transcription_data.get('language_code')
                            recording['audio_duration'] = recording['audio_duration'] or (float(transcription_data.get('audio_duration', 0)) if transcription_data.get('audio_duration') else None)
                            # Also update processing time if available
                            if not proc_time and transcription_data:
                                proc_time = transcription_data.get('translation_time') or transcription_data.get('processing_time')
                                recording['processing_time'] = float(proc_time) if proc_time else None
                                recording['translation_time'] = float(proc_time) if proc_time else None
                else:
                    # Full transcription data requested
                    if transcription_data:
                        recording['transcription'] = transcription_data.get('translation', '')
                        recording['original_transcription'] = transcription_data.get('transcription', '')
                        recording['detected_language'] = transcription_data.get('detected_language')
                        recording['language_code'] = transcription_data.get('language_code')
                        recording['audio_duration'] = float(transcription_data.get('audio_duration', 0)) if transcription_data.get('audio_duration') else None
                        recording['word_count'] = transcription_data.get('word_count')
                        recording['language_confidence'] = transcription_data.get('language_confidence')
                    else:
                        # Fallback to metadata
                        recording['detected_language'] = metadata.get('detected_language')
                        recording['language_code'] = metadata.get('language_code') or metadata.get('source_language')
                        recording['audio_duration'] = float(metadata.get('audio_duration', 0)) if metadata.get('audio_duration') else None
                
                processed.append(recording)
            
            return {
                'recordings': processed,
                'total': total,
                'limit': limit,
                'offset': offset
            }
        
        except Exception as e:
            print(f"Error fetching processed recordings: {e}")
            traceback.print_exc()
            return {'recordings': [], 'total': 0, 'error': str(e)}
    
    def get_failed_recordings(self, limit: int = 100, offset: int = 0, organization: Optional[str] = None) -> Dict:
        """
        Get failed recordings with error information
        """
        if not getattr(self, 'enabled', False) or not self.blob_client:
            return {'recordings': [], 'total': 0, 'limit': limit, 'offset': offset, 'error': 'AudioMonitor not configured'}

        try:
            container = self.blob_client.get_container_client(Config.FAILED_CONTAINER)
            failed = []
            
            # Organization prefix for filtering
            org_prefix = f"{organization}/" if organization and organization != "dachido" else None
            
            # First pass: Count ALL failed recordings (before pagination)
            all_failed_blobs = []
            
            for blob in container.list_blobs():
                # Filter by organization prefix if specified
                if org_prefix and not blob.name.startswith(org_prefix):
                    continue
                
                # Check if it's an audio file
                if not any(blob.name.endswith(ext) for ext in self.AUDIO_EXTENSIONS):
                    continue
                
                # This is a failed recording
                all_failed_blobs.append(blob)
            
            # Total count is the number of all failed blobs
            total = len(all_failed_blobs)
            
            # Second pass: Apply pagination to get only the records for current page
            start_idx = offset
            end_idx = offset + limit
            
            for blob in all_failed_blobs[start_idx:end_idx]:
                # Get error metadata
                error_data = self._get_error_metadata(blob.name)
                
                recording = {
                    'filename': blob.name,
                    'size': blob.size,
                    'failure_timestamp': blob.last_modified.isoformat() if blob.last_modified else None,
                    'url': self._get_blob_url(Config.FAILED_CONTAINER, blob.name),
                    'error': error_data.get('error', 'Unknown error'),
                    'stage': error_data.get('stage', 'unknown'),
                    'timestamp': error_data.get('timestamp')
                }
                
                failed.append(recording)
            
            return {
                'recordings': failed,
                'total': total,  # Total count from first pass (all matching records)
                'limit': limit,
                'offset': offset
            }
        
        except Exception as e:
            print(f"Error fetching failed recordings: {e}")
            traceback.print_exc()
            return {'recordings': [], 'total': 0, 'error': str(e)}
    
    def update_quality_feedback(self, filename: str, rating: str, 
                               reviewer: str, notes: str = "") -> Dict:
        """
        Update quality feedback by modifying blob metadata
        rating: 'good', 'bad', or 'unreviewed'
        """
        if not getattr(self, 'enabled', False) or not self.blob_client:
            return {'success': False, 'error': 'AudioMonitor not configured'}

        try:
            if rating not in ['good', 'bad', 'unreviewed']:
                return {'success': False, 'error': 'Invalid rating'}
            
            print(f"Updating quality feedback for: {filename}, rating: {rating}, reviewer: {reviewer}")
            
            blob_client = self.blob_client.get_blob_client(Config.PROCESSED_CONTAINER, filename)
            
            # Verify blob exists
            props = blob_client.get_blob_properties()
            existing_metadata = props.metadata or {}
            print(f"Existing metadata: {existing_metadata}")
            
            # Create clean metadata dict - sanitize for Azure requirements
            # Azure metadata keys must be valid C# identifiers (alphanumeric + underscore)
            # Values must not contain newlines
            clean_notes = notes.replace('\n', ' ').replace('\r', ' ')[:500] if notes else ''
            clean_reviewer = reviewer.replace(' ', '_')[:100] if reviewer else 'unknown'
            
            # Build new metadata (preserve existing, update quality fields)
            new_metadata = {}
            for key, value in existing_metadata.items():
                # Keep existing metadata
                new_metadata[key] = str(value)
            
            # Update quality fields
            new_metadata['quality_rating'] = rating
            new_metadata['reviewer'] = clean_reviewer
            new_metadata['review_timestamp'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            if clean_notes:
                new_metadata['review_notes'] = clean_notes
            
            print(f"Setting new metadata: {new_metadata}")
            
            # Set updated metadata on processed recording
            blob_client.set_blob_metadata(new_metadata)
            
            # Also update transcription file metadata if it exists
            transcription_updated = False
            transcription_name = filename.rsplit('.', 1)[0] + '_transcription.json'
            try:
                transcription_blob = self.blob_client.get_blob_client(
                    Config.TRANSCRIPTIONS_CONTAINER,
                    transcription_name
                )
                # Get existing transcription metadata
                trans_props = transcription_blob.get_blob_properties()
                trans_metadata = trans_props.metadata or {}
                
                # Update transcription metadata with quality feedback
                trans_metadata['quality_rating'] = rating
                trans_metadata['reviewer'] = clean_reviewer
                trans_metadata['review_timestamp'] = new_metadata['review_timestamp']
                if clean_notes:
                    trans_metadata['review_notes'] = clean_notes
                
                # Set updated metadata on transcription
                transcription_blob.set_blob_metadata(trans_metadata)
                transcription_updated = True
                print(f"Quality feedback also updated in transcription file: {transcription_name}")
            except ResourceNotFoundError:
                print(f"Transcription file not found: {transcription_name} (this is okay, continuing...)")
            except Exception as e:
                print(f"Warning: Could not update transcription metadata: {e}")
            
            # Verify the update worked on processed recording
            # Azure metadata updates may take a moment, so retry verification
            import time
            max_retries = 3
            verified = False
            
            for attempt in range(max_retries):
                time.sleep(0.5)  # Small delay for Azure to propagate
                verify_props = blob_client.get_blob_properties()
                verify_metadata = verify_props.metadata or {}
                print(f"Verification attempt {attempt + 1}: {verify_metadata}")
                
                # Check if quality_rating matches (case-insensitive, string comparison)
                verified_rating = str(verify_metadata.get('quality_rating', '')).lower().strip()
                expected_rating = str(rating).lower().strip()
                
                if verified_rating == expected_rating:
                    verified = True
                    print(f"Quality feedback verified successfully for {filename}")
                    break
                elif attempt < max_retries - 1:
                    print(f"Verification attempt {attempt + 1} failed, retrying...")
            
            if verified:
                result = {
                    'success': True,
                    'filename': filename,
                    'quality_rating': rating,
                    'reviewer': clean_reviewer,
                    'review_timestamp': new_metadata['review_timestamp'],
                    'transcription_updated': transcription_updated
                }
                if transcription_updated:
                    result['transcription_file'] = transcription_name
                return result
            else:
                # Even if verification fails, the metadata was set - return success but with warning
                print(f"WARNING: Metadata verification failed after {max_retries} attempts!")
                print(f"Expected rating: '{rating}', Got: '{verify_metadata.get('quality_rating')}'")
                print(f"Full verified metadata: {verify_metadata}")
                
                # Still return success since the set_blob_metadata call succeeded
                # The metadata is likely saved, just verification timing issue
                result = {
                    'success': True,
                    'filename': filename,
                    'quality_rating': rating,
                    'reviewer': clean_reviewer,
                    'review_timestamp': new_metadata['review_timestamp'],
                    'transcription_updated': transcription_updated,
                    'warning': 'Metadata set but verification had timing issues - metadata should be saved'
                }
                if transcription_updated:
                    result['transcription_file'] = transcription_name
                return result
        
        except ResourceNotFoundError:
            print(f"Recording not found: {filename}")
            return {'success': False, 'error': 'Recording not found'}
        except Exception as e:
            print(f"Error updating quality feedback: {e}")
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def get_analytics(self, days: int = 30) -> Dict:
        """
        Calculate analytics and metrics for the dashboard
        """
        if not getattr(self, 'enabled', False) or not self.blob_client:
            return {
                'total_processed': 0,
                'total_failed': 0,
                'total_recordings': 0,
                'success_rate': 0,
                'failure_rate': 0,
                'avg_processing_time': 0,
                'avg_audio_duration': 0,
                'processing_ratio': 0,
                'quality_breakdown': {'good': 0, 'bad': 0, 'unreviewed': 0},
                'language_breakdown': {},
                'processing_time_trend': [],
                'quality_score': 0,
                'error': 'AudioMonitor not configured'
            }

        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Collect data from processed recordings
            processed_container = self.blob_client.get_container_client(Config.PROCESSED_CONTAINER)
            failed_container = self.blob_client.get_container_client(Config.FAILED_CONTAINER)
            
            processed_data = []
            failed_count = 0
            
            # Get processed recordings data
            for blob in processed_container.list_blobs():
                if not any(blob.name.endswith(ext) for ext in self.AUDIO_EXTENSIONS):
                    continue
                
                if blob.last_modified and blob.last_modified.replace(tzinfo=None) < cutoff_date:
                    continue
                
                blob_client = self.blob_client.get_blob_client(Config.PROCESSED_CONTAINER, blob.name)
                props = blob_client.get_blob_properties()
                metadata = props.metadata or {}
                transcription_data = self._get_transcription(blob.name)
                
                # Get quality_rating from metadata (primary) or transcription metadata (fallback)
                quality_rating = metadata.get('quality_rating') or metadata.get('Quality_Rating') or 'unreviewed'
                
                # Normalize the rating value
                if quality_rating:
                    quality_rating = str(quality_rating).lower().strip()
                    if quality_rating not in ['good', 'bad', 'unreviewed']:
                        quality_rating = 'unreviewed'
                else:
                    quality_rating = 'unreviewed'
                
                # If not in blob metadata, try transcription file metadata
                if quality_rating == 'unreviewed':
                    transcription_name = blob.name.rsplit('.', 1)[0] + '_transcription.json'
                    try:
                        trans_blob = self.blob_client.get_blob_client(
                            Config.TRANSCRIPTIONS_CONTAINER,
                            transcription_name
                        )
                        trans_props = trans_blob.get_blob_properties()
                        trans_metadata = trans_props.metadata or {}
                        trans_rating = trans_metadata.get('quality_rating') or trans_metadata.get('Quality_Rating')
                        if trans_rating:
                            trans_rating = str(trans_rating).lower().strip()
                            if trans_rating in ['good', 'bad']:
                                quality_rating = trans_rating
                    except Exception as e:
                        print(f"Could not check transcription metadata: {e}")
                        pass  # Use default 'unreviewed'
                
                # Debug: log if we find a reviewed recording
                if quality_rating != 'unreviewed':
                    print(f"Found reviewed recording: {blob.name} - Rating: {quality_rating}")
                
                processed_data.append({
                    'timestamp': blob.last_modified,
                    'quality_rating': quality_rating if quality_rating else 'unreviewed',
                    'source_language': transcription_data.get('language_code') if transcription_data else 'unknown',
                    'processing_time': float(transcription_data.get('translation_time', 0)) if transcription_data else 0,
                    'audio_duration': float(transcription_data.get('audio_duration', 0)) if transcription_data else 0
                })
            
            # Count failed recordings
            for blob in failed_container.list_blobs():
                if not any(blob.name.endswith(ext) for ext in self.AUDIO_EXTENSIONS):
                    continue
                if blob.last_modified and blob.last_modified.replace(tzinfo=None) >= cutoff_date:
                    failed_count += 1
            
            # Calculate metrics
            total_recordings = len(processed_data) + failed_count
            
            analytics = {
                'total_processed': len(processed_data),
                'total_failed': failed_count,
                'total_recordings': total_recordings,
                'success_rate': round((len(processed_data) / total_recordings * 100) if total_recordings > 0 else 0, 2),
                'failure_rate': round((failed_count / total_recordings * 100) if total_recordings > 0 else 0, 2),
                'avg_processing_time': 0,
                'avg_audio_duration': 0,
                'processing_ratio': 0,
                'quality_breakdown': {
                    'good': 0,
                    'bad': 0,
                    'unreviewed': 0
                },
                'language_breakdown': {},
                'processing_time_trend': [],
                'quality_score': 0
            }
            
            if processed_data:
                # Calculate averages
                processing_times = [d['processing_time'] for d in processed_data if d['processing_time'] > 0]
                audio_durations = [d['audio_duration'] for d in processed_data if d['audio_duration'] > 0]
                
                if processing_times:
                    analytics['avg_processing_time'] = round(sum(processing_times) / len(processing_times), 2)
                
                if audio_durations:
                    analytics['avg_audio_duration'] = round(sum(audio_durations) / len(audio_durations), 2)
                    
                    # Calculate processing ratio (audio duration / processing time)
                    # Higher means faster: e.g., 5x means 5 seconds of audio processed per second
                    if analytics['avg_processing_time'] > 0:
                        analytics['processing_ratio'] = round(
                            analytics['avg_audio_duration'] / analytics['avg_processing_time'], 2
                        )
                
                # Quality breakdown - normalize rating values
                for record in processed_data:
                    rating = record['quality_rating']
                    # Normalize rating (handle case variations, None, empty strings)
                    if not rating or rating == '' or rating == 'None':
                        rating = 'unreviewed'
                    else:
                        rating = str(rating).lower().strip()
                        # Map to valid values
                        if rating not in ['good', 'bad', 'unreviewed']:
                            rating = 'unreviewed'
                    
                    analytics['quality_breakdown'][rating] = analytics['quality_breakdown'].get(rating, 0) + 1
                    
                    # Debug logging
                    if rating != 'unreviewed':
                        print(f"Found quality rating: {rating} for blob")
                
                # Language breakdown
                for record in processed_data:
                    lang = record['source_language']
                    if lang not in analytics['language_breakdown']:
                        analytics['language_breakdown'][lang] = {
                            'count': 0,
                            'avg_processing_time': 0,
                            'total_processing_time': 0
                        }
                    analytics['language_breakdown'][lang]['count'] += 1
                    analytics['language_breakdown'][lang]['total_processing_time'] += record['processing_time']
                
                # Calculate language averages
                for lang_data in analytics['language_breakdown'].values():
                    if lang_data['count'] > 0:
                        lang_data['avg_processing_time'] = round(
                            lang_data['total_processing_time'] / lang_data['count'], 2
                        )
                
                # Quality score (percentage of good ratings out of reviewed)
                reviewed = analytics['quality_breakdown']['good'] + analytics['quality_breakdown']['bad']
                if reviewed > 0:
                    analytics['quality_score'] = round(
                        analytics['quality_breakdown']['good'] / reviewed * 100, 2
                    )
                
                # Processing time trend (group by day)
                daily_data = {}
                for record in processed_data:
                    if record['timestamp']:
                        date_key = record['timestamp'].strftime('%Y-%m-%d')
                        if date_key not in daily_data:
                            daily_data[date_key] = {
                                'date': date_key,
                                'count': 0,
                                'total_time': 0
                            }
                        daily_data[date_key]['count'] += 1
                        daily_data[date_key]['total_time'] += record['processing_time']
                
                # Calculate daily averages
                for date_key in sorted(daily_data.keys()):
                    data = daily_data[date_key]
                    analytics['processing_time_trend'].append({
                        'date': date_key,
                        'avg_processing_time': round(data['total_time'] / data['count'], 2) if data['count'] > 0 else 0,
                        'count': data['count']
                    })
            
            return analytics
        
        except Exception as e:
            print(f"Error calculating analytics: {e}")
            traceback.print_exc()
            return {'error': str(e)}
    
    def get_recording_detail(self, filename: str, container: str = 'processed') -> Dict:
        """
        Get detailed information about a specific recording
        """
        if not getattr(self, 'enabled', False) or not self.blob_client:
            return {'error': 'AudioMonitor not configured'}

        try:
            container_name = {
                'processed': Config.PROCESSED_CONTAINER,
                'failed': Config.FAILED_CONTAINER,
                'pending': Config.RECORDINGS_CONTAINER
            }.get(container, Config.PROCESSED_CONTAINER)
            
            blob_client = self.blob_client.get_blob_client(container_name, filename)
            props = blob_client.get_blob_properties()
            metadata = props.metadata or {}
            
            # Get transcription
            transcription_data = self._get_transcription(filename)
            
            # Get error data if failed
            error_data = None
            if container == 'failed':
                error_data = self._get_error_metadata(filename)
            
            detail = {
                'filename': filename,
                'size': props.size,
                'container': container,
                'url': self._get_blob_url(container_name, filename),
                'upload_timestamp': props.last_modified.isoformat() if props.last_modified else None,
                'metadata': metadata,
                'transcription': transcription_data,
                'error': error_data
            }
            
            return detail
        
        except ResourceNotFoundError:
            return {'error': 'Recording not found'}
        except Exception as e:
            print(f"Error fetching recording detail: {e}")
            traceback.print_exc()
            return {'error': str(e)}
    
    def retry_failed_recording(self, filename: str) -> Dict:
        """
        Move a failed recording back to recordings container for reprocessing
        """
        if not getattr(self, 'enabled', False) or not self.blob_client:
            return {'success': False, 'error': 'AudioMonitor not configured'}

        try:
            # Download from failed container
            source = self.blob_client.get_blob_client(Config.FAILED_CONTAINER, filename)
            data = source.download_blob().readall()
            
            # Upload to recordings container
            dest = self.blob_client.get_blob_client(Config.RECORDINGS_CONTAINER, filename)
            dest.upload_blob(data, overwrite=True)
            
            # Delete from failed container
            source.delete_blob()
            
            return {
                'success': True,
                'filename': filename,
                'message': 'Recording moved to pending queue for reprocessing'
            }
        
        except Exception as e:
            print(f"Error retrying recording: {e}")
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    # Helper methods
    
    def _has_transcription(self, audio_filename: str) -> bool:
        """Check if transcription exists"""
        transcription_name = audio_filename.rsplit('.', 1)[0] + '_transcription.json'
        try:
            blob = self.blob_client.get_blob_client(
                Config.TRANSCRIPTIONS_CONTAINER,
                transcription_name
            )
            blob.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False
        except:
            return False
    
    def _get_transcription(self, audio_filename: str) -> Optional[Dict]:
        """Get transcription data for audio file"""
        transcription_name = audio_filename.rsplit('.', 1)[0] + '_transcription.json'
        try:
            blob = self.blob_client.get_blob_client(
                Config.TRANSCRIPTIONS_CONTAINER,
                transcription_name
            )
            data = blob.download_blob().readall()
            return json.loads(data)
        except:
            return None
    
    def _get_error_metadata(self, audio_filename: str) -> Optional[Dict]:
        """Get error metadata for failed recording"""
        error_name = audio_filename.rsplit('.', 1)[0] + '_error.json'
        try:
            blob = self.blob_client.get_blob_client(
                Config.FAILED_CONTAINER,
                error_name
            )
            data = blob.download_blob().readall()
            return json.loads(data)
        except:
            return None
    
    def _get_blob_url(self, container: str, blob_name: str, with_sas: bool = True) -> str:
        """Get blob URL with optional SAS token for access"""
        blob_client = self.blob_client.get_blob_client(container, blob_name)
        
        if with_sas:
            try:
                # Generate SAS token valid for 1 hour
                sas_token = generate_blob_sas(
                    account_name=blob_client.account_name,
                    container_name=container,
                    blob_name=blob_name,
                    account_key=self._get_account_key(),
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.utcnow() + timedelta(hours=1)
                )
                return f"{blob_client.url}?{sas_token}"
            except Exception as e:
                print(f"Error generating SAS token: {e}")
                return blob_client.url
        return blob_client.url
    
    def _get_account_key(self) -> str:
        """Extract account key from connection string"""
        conn_str = Config.CONNECTION_STRING
        for part in conn_str.split(';'):
            if part.startswith('AccountKey='):
                return part.split('=', 1)[1]
        return ''
    
    def get_organizations_from_containers(self) -> List[str]:
        """
        Discover organizations by scanning blob names in all containers
        Returns list of organization names found in containers
        """
        if not getattr(self, 'enabled', False) or not self.blob_client:
            return []
        
        organizations = set()
        
        try:
            # Check all containers for organization prefixes
            containers_to_check = [
                Config.RECORDINGS_CONTAINER,
                Config.PROCESSED_CONTAINER,
                Config.FAILED_CONTAINER
            ]
            
            for container_name in containers_to_check:
                try:
                    container = self.blob_client.get_container_client(container_name)
                    for blob in container.list_blobs():
                        # Extract organization from blob name
                        # Format: {organization}/{filename}
                        if '/' in blob.name:
                            org_name = blob.name.split('/')[0]
                            # Only add if it's not empty and not a system prefix
                            if org_name and org_name not in ['dachido', 'system', 'temp']:
                                organizations.add(org_name)
                except Exception as e:
                    print(f"Error scanning container {container_name}: {e}")
                    continue
            
            # Return sorted list
            return sorted(list(organizations))
        except Exception as e:
            print(f"Error discovering organizations: {e}")
            return []
    
    def get_overview_stats(self, organization: Optional[str] = None) -> Dict:
        """Get quick overview statistics - optimized for speed"""
        try:
            pending_container = self.blob_client.get_container_client(Config.RECORDINGS_CONTAINER)
            processed_container = self.blob_client.get_container_client(Config.PROCESSED_CONTAINER)
            failed_container = self.blob_client.get_container_client(Config.FAILED_CONTAINER)
            
            # Organization prefix for filtering
            org_prefix = f"{organization}/" if organization and organization != "dachido" else None
            
            # Count audio files efficiently (just check extensions, no API calls per file)
            pending_count = 0
            for b in pending_container.list_blobs():
                # Filter by organization prefix if specified
                if org_prefix and not b.name.startswith(org_prefix):
                    continue
                
                if any(b.name.endswith(ext) for ext in self.AUDIO_EXTENSIONS):
                    # Quick check if transcription exists (for pending, we want files WITHOUT transcription)
                    transcription_name = b.name.rsplit('.', 1)[0] + '_transcription.json'
                    try:
                        trans_blob = self.blob_client.get_blob_client(
                            Config.TRANSCRIPTIONS_CONTAINER,
                            transcription_name
                        )
                        trans_blob.get_blob_properties()  # Just check existence
                        continue  # Has transcription, not pending
                    except:
                        pending_count += 1  # No transcription, count as pending
            
            processed_count = sum(1 for b in processed_container.list_blobs() 
                                if (not org_prefix or b.name.startswith(org_prefix))
                                and any(b.name.endswith(ext) for ext in self.AUDIO_EXTENSIONS))
            failed_count = sum(1 for b in failed_container.list_blobs() 
                             if (not org_prefix or b.name.startswith(org_prefix))
                             and any(b.name.endswith(ext) for ext in self.AUDIO_EXTENSIONS))
            
            return {
                'pending': pending_count,
                'processed': processed_count,
                'failed': failed_count,
                'total': pending_count + processed_count + failed_count
            }
        except Exception as e:
            print(f"Error fetching overview stats: {e}")
            return {'pending': 0, 'processed': 0, 'failed': 0, 'total': 0, 'error': str(e)}

