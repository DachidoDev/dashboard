#!/usr/bin/env python3
"""
Automated Integration Script
Adds Audio Monitor module to existing Coromandel FieldForce Dashboard
"""

import os
import sys
from pathlib import Path

def backup_file(filepath):
    """Create backup of file"""
    backup_path = f"{filepath}.backup"
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Backed up: {filepath} → {backup_path}")
        return True
    return False

def integrate_dashboard_html():
    """Add audio monitor to dashboard.html"""
    filepath = "customer_dashboard-main/templates/dashboard.html"
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    backup_file(filepath)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already integrated
    if '🎙️ AUDIO MONITOR' in content:
        print("⚠️  Audio Monitor already integrated in dashboard.html")
        return True
    
    # Step 1: Add navigation item
    nav_original = '''<div class="nav-item" data-module="admin">ADMIN</div>
        </nav>'''
    
    nav_new = '''<div class="nav-item" data-module="admin">ADMIN</div>
            <div class="nav-item" data-module="audio">🎙️ AUDIO MONITOR</div>
        </nav>'''
    
    if nav_original in content:
        content = content.replace(nav_original, nav_new)
        print("✅ Added navigation item")
    else:
        print("⚠️  Could not find navigation section to modify")
    
    # Step 2: Add loadAudioData() to module loading
    # Find where loadAdminData() is called and add loadAudioData
    admin_load = "case 'admin': loadAdminData(); break;"
    audio_load = admin_load + "\n                    case 'audio': loadAudioData(); break;"
    
    if admin_load in content and "case 'audio':" not in content:
        content = content.replace(admin_load, audio_load)
        print("✅ Added audio module loading")
    
    # Step 3: Save modified content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Updated: {filepath}")
    return True

def integrate_app_py():
    """Add audio monitoring APIs to app.py"""
    filepath = "customer_dashboard-main/app.py"
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    backup_file(filepath)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already integrated
    if 'AUDIO_MONITOR_ENABLED' in content:
        print("⚠️  Audio monitoring already integrated in app.py")
        return True
    
    # Add imports after "import auth"
    import_section = """import auth

# Import audio monitor - LOAD .env BEFORE importing AudioMonitor
import sys
import os

# Add backend to path
backend_dir = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.append(backend_dir)

# Load .env BEFORE importing AudioMonitor
try:
    from dotenv import load_dotenv
    env_file = os.path.join(backend_dir, '.env')
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"✅ Loaded environment from: {env_file}")
        # Debug: Print what was loaded
        print(f"🔍 CONNECTION_STRING set: {bool(os.environ.get('AZURE_STORAGE_CONNECTION_STRING'))}")
        print(f"🔍 RECORDINGS_CONTAINER: {os.environ.get('RECORDINGS_CONTAINER', 'NOT SET')}")
        print(f"🔍 TRANSCRIPTIONS_CONTAINER: {os.environ.get('TRANSCRIPTIONS_CONTAINER', 'NOT SET')}")
        print(f"🔍 PROCESSED_RECORDINGS_CONTAINER: {os.environ.get('PROCESSED_RECORDINGS_CONTAINER', 'NOT SET')}")
        print(f"🔍 FAILED_RECORDINGS_CONTAINER: {os.environ.get('FAILED_RECORDINGS_CONTAINER', 'NOT SET')}")
    else:
        print(f"⚠️  .env file not found at: {env_file}")
except ImportError:
    print("⚠️  python-dotenv not installed, run: pip install python-dotenv")

# NOW import AudioMonitor (Config will read from already-loaded environment)
try:
    from audio_monitor import AudioMonitor
    AUDIO_MONITOR_ENABLED = True
    print("✅ Audio monitoring enabled")
except ImportError as e:
    AUDIO_MONITOR_ENABLED = False
    print(f"⚠️  Audio monitoring not available: {e}")
"""
    
    content = content.replace("import auth", import_section)
    print("✅ Added audio monitor imports")
    
    # Add API routes before if __name__ == "__main__":
    audio_apis = '''

# ==================== AUDIO MONITORING MODULE APIs ====================

@app.route("/api/audio/overview")
@login_required
def get_audio_overview():
    if not AUDIO_MONITOR_ENABLED:
        return jsonify({"error": "Audio monitoring not enabled", "pending": 0, "processed": 0, "failed": 0}), 503
    try:
        monitor = AudioMonitor()
        stats = monitor.get_overview_stats()
        return jsonify(stats)
    except Exception as e:
        print(f"Audio overview error: {e}")
        return jsonify({"error": str(e), "pending": 0, "processed": 0, "failed": 0}), 500

@app.route("/api/audio/pending")
@login_required
def get_audio_pending():
    if not AUDIO_MONITOR_ENABLED:
        return jsonify({"error": "Audio monitoring not enabled"}), 503
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        monitor = AudioMonitor()
        result = monitor.get_pending_recordings(limit=limit, offset=offset)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audio/processed")
@login_required
def get_audio_processed():
    if not AUDIO_MONITOR_ENABLED:
        return jsonify({"error": "Audio monitoring not enabled"}), 503
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        quality_filter = request.args.get("quality")
        language_filter = request.args.get("language")
        monitor = AudioMonitor()
        result = monitor.get_processed_recordings(
            limit=limit, offset=offset,
            quality_filter=quality_filter,
            language_filter=language_filter
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audio/failed")
@login_required
def get_audio_failed():
    if not AUDIO_MONITOR_ENABLED:
        return jsonify({"error": "Audio monitoring not enabled"}), 503
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        monitor = AudioMonitor()
        result = monitor.get_failed_recordings(limit=limit, offset=offset)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audio/analytics")
@login_required
def get_audio_analytics():
    if not AUDIO_MONITOR_ENABLED:
        return jsonify({"error": "Audio monitoring not enabled"}), 503
    try:
        days = int(request.args.get("days", 30))
        monitor = AudioMonitor()
        analytics = monitor.get_analytics(days=days)
        return jsonify(analytics)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audio/detail/<path:filename>")
@login_required
def get_audio_recording_detail(filename):
    if not AUDIO_MONITOR_ENABLED:
        return jsonify({"error": "Audio monitoring not enabled"}), 503
    try:
        container = request.args.get("container", "processed")
        monitor = AudioMonitor()
        detail = monitor.get_recording_detail(filename, container=container)
        return jsonify(detail)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audio/quality-feedback", methods=["POST"])
@login_required
def update_audio_quality_feedback():
    if not AUDIO_MONITOR_ENABLED:
        return jsonify({"error": "Audio monitoring not enabled"}), 503
    try:
        data = request.json
        filename = data.get("filename")
        rating = data.get("rating")
        notes = data.get("notes", "")
        reviewer = session.get("username", "admin")
        
        if not filename or not rating:
            return jsonify({"error": "filename and rating are required"}), 400
        
        monitor = AudioMonitor()
        result = monitor.update_quality_feedback(
            filename=filename, rating=rating,
            reviewer=reviewer, notes=notes
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audio/retry/<path:filename>", methods=["POST"])
@login_required
def retry_audio_failed(filename):
    if not AUDIO_MONITOR_ENABLED:
        return jsonify({"error": "Audio monitoring not enabled"}), 503
    try:
        monitor = AudioMonitor()
        result = monitor.retry_failed_recording(filename)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

'''
    
    # Insert before if __name__ == "__main__":
    if_main_marker = 'if __name__ == "__main__":'
    if if_main_marker in content:
        content = content.replace(if_main_marker, audio_apis + if_main_marker)
        print("✅ Added audio monitoring API routes")
    else:
        # Add at the end
        content += audio_apis
        print("✅ Added audio monitoring API routes at end")
    
    # Save modified content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Updated: {filepath}")
    return True

def main():
    print("\n" + "="*70)
    print("  AUDIO MONITOR INTEGRATION SCRIPT")
    print("="*70 + "\n")
    
    print("This script will integrate Audio Monitor into your existing dashboard.")
    print("Backups will be created before modifying files.\n")
    
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Aborted.")
        return
    
    print("\n[1/2] Integrating app.py...")
    if not integrate_app_py():
        print("❌ Failed to integrate app.py")
        return 1
    
    print("\n[2/2] Note: dashboard.html requires manual integration")
    print("Please follow INTEGRATE_AUDIO_TO_DASHBOARD.md for HTML changes")
    
    print("\n" + "="*70)
    print("  ✅ INTEGRATION COMPLETE!")
    print("="*70)
    print("\nNext steps:")
    print("1. Review INTEGRATE_AUDIO_TO_DASHBOARD.md for HTML changes")
    print("2. Run: python customer_dashboard-main/app.py")
    print("3. Open: http://localhost:5000")
    print("4. Click: 🎙️ AUDIO MONITOR tab")
    print("="*70 + "\n")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)