"""
Audio Processing Monitor - Flask Application
Admin dashboard for monitoring audio processing pipeline
"""

import sys
import os

# Load .env file from backend directory if it exists
try:
    from dotenv import load_dotenv
    backend_dir = os.path.join(os.path.dirname(__file__), '..', 'backend')
    env_file = os.path.join(backend_dir, '.env')
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"✅ Loaded environment from: {env_file}")
except ImportError:
    print("⚠️  python-dotenv not installed. Using system environment variables.")

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from functools import wraps
import auth
from audio_monitor import AudioMonitor

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "your_audio_monitor_secret_key")

# Initialize authentication
auth.bcrypt.init_app(app)

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" not in session:
            return redirect(url_for("login"))
        # Only admin role can access audio monitor
        if session.get("user_role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function


# ==================== Authentication Routes ====================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        success, role = auth.check_password(username, password)
        if success:
            session["logged_in"] = True
            session["username"] = username
            session["user_role"] = role
            return redirect(url_for("audio_monitor_dashboard"))
        else:
            return render_template("audio_login.html", error="Invalid Credentials")
    return render_template("audio_login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    session.pop("username", None)
    session.pop("user_role", None)
    return redirect(url_for("login"))


# ==================== Dashboard Routes ====================

@app.route("/")
@admin_required
def audio_monitor_dashboard():
    """Main audio monitoring dashboard"""
    username = session.get("username", "Admin")
    return render_template("audio_monitor.html", username=username)


# ==================== API Endpoints ====================

@app.route("/api/audio/overview")
@admin_required
def get_overview():
    """Get overview statistics"""
    try:
        monitor = AudioMonitor()
        stats = monitor.get_overview_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audio/pending")
@admin_required
def get_pending():
    """Get pending recordings"""
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        
        monitor = AudioMonitor()
        result = monitor.get_pending_recordings(limit=limit, offset=offset)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audio/processed")
@admin_required
def get_processed():
    """Get processed recordings"""
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        quality_filter = request.args.get("quality")
        language_filter = request.args.get("language")
        
        monitor = AudioMonitor()
        result = monitor.get_processed_recordings(
            limit=limit,
            offset=offset,
            quality_filter=quality_filter,
            language_filter=language_filter
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audio/failed")
@admin_required
def get_failed():
    """Get failed recordings"""
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        
        monitor = AudioMonitor()
        result = monitor.get_failed_recordings(limit=limit, offset=offset)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audio/analytics")
@admin_required
def get_analytics():
    """Get analytics and metrics"""
    try:
        days = int(request.args.get("days", 30))
        
        monitor = AudioMonitor()
        analytics = monitor.get_analytics(days=days)
        return jsonify(analytics)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audio/detail/<path:filename>")
@admin_required
def get_recording_detail(filename):
    """Get detailed information about a recording"""
    try:
        container = request.args.get("container", "processed")
        
        monitor = AudioMonitor()
        detail = monitor.get_recording_detail(filename, container=container)
        return jsonify(detail)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audio/quality-feedback", methods=["POST"])
@admin_required
def update_quality_feedback():
    """Update quality feedback for a recording"""
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
            filename=filename,
            rating=rating,
            reviewer=reviewer,
            notes=notes
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audio/retry/<path:filename>", methods=["POST"])
@admin_required
def retry_failed(filename):
    """Retry a failed recording"""
    try:
        monitor = AudioMonitor()
        result = monitor.retry_failed_recording(filename)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== Export Routes ====================

@app.route("/api/audio/export/analytics")
@admin_required
def export_analytics():
    """Export analytics data as CSV"""
    try:
        import csv
        from io import StringIO
        from flask import Response
        
        days = int(request.args.get("days", 30))
        monitor = AudioMonitor()
        analytics = monitor.get_analytics(days=days)
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Write analytics summary
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Processed", analytics.get("total_processed", 0)])
        writer.writerow(["Total Failed", analytics.get("total_failed", 0)])
        writer.writerow(["Success Rate", f"{analytics.get('success_rate', 0)}%"])
        writer.writerow(["Failure Rate", f"{analytics.get('failure_rate', 0)}%"])
        writer.writerow(["Avg Processing Time (s)", analytics.get("avg_processing_time", 0)])
        writer.writerow(["Avg Audio Duration (s)", analytics.get("avg_audio_duration", 0)])
        writer.writerow(["Processing Ratio", analytics.get("processing_ratio", 0)])
        writer.writerow(["Quality Score", f"{analytics.get('quality_score', 0)}%"])
        writer.writerow([])
        
        # Write language breakdown
        writer.writerow(["Language Breakdown"])
        writer.writerow(["Language", "Count", "Avg Processing Time"])
        for lang, data in analytics.get("language_breakdown", {}).items():
            writer.writerow([lang, data["count"], data["avg_processing_time"]])
        
        # Prepare response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename=audio_analytics_{days}days.csv"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== Cron Logs Viewer (NEW) ====================

@app.route("/api/audio/cron-logs")
@admin_required
def get_cron_logs():
    """Get recent cron job logs"""
    try:
        from pathlib import Path
        import re
        from datetime import datetime
        
        # Look for logs in backend/logs directory
        log_dir = Path(__file__).parent.parent / 'backend' / 'logs'
        
        if not log_dir.exists():
            return jsonify({"logs": [], "error": "Log directory not found"})
        
        # Get all cron log files
        log_files = sorted(log_dir.glob('cron_*.log'), key=lambda x: x.stat().st_mtime, reverse=True)
        
        limit = int(request.args.get("limit", 10))
        logs = []
        
        for log_file in log_files[:limit]:
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    
                # Extract key information
                lines = content.split('\n')
                start_time = None
                end_time = None
                status = 'unknown'
                
                for line in lines:
                    if 'BATCH PROCESSING STARTED' in line:
                        match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line)
                        if match:
                            start_time = match.group()
                    elif 'BATCH PROCESSING COMPLETED' in line:
                        match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line)
                        if match:
                            end_time = match.group()
                    
                    # Detect success/failure
                    if 'SESSION COMPLETE' in line or '✓' in line:
                        status = 'success'
                    elif 'Error' in line or 'Failed' in line or '✗' in line:
                        status = 'error'
                
                logs.append({
                    'filename': log_file.name,
                    'timestamp': log_file.stat().st_mtime,
                    'size': log_file.stat().st_size,
                    'start_time': start_time,
                    'end_time': end_time,
                    'status': status,
                    'preview': '\n'.join(lines[:5])  # First 5 lines as preview
                })
            except Exception as e:
                print(f"Error reading log file {log_file}: {e}")
                continue
        
        return jsonify({"logs": logs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audio/cron-logs/<filename>")
@admin_required
def get_cron_log_detail(filename):
    """Get full content of a specific cron log"""
    try:
        from pathlib import Path
        
        # Security: only allow cron_*.log files
        if not filename.startswith('cron_') or not filename.endswith('.log'):
            return jsonify({"error": "Invalid log file"}), 400
        
        log_file = Path(__file__).parent.parent / 'backend' / 'logs' / filename
        
        if not log_file.exists():
            return jsonify({"error": "Log file not found"}), 404
        
        with open(log_file, 'r') as f:
            content = f.read()
        
        return jsonify({
            "filename": filename,
            "content": content,
            "size": log_file.stat().st_size,
            "modified": log_file.stat().st_mtime
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Initialize default admin user if doesn't exist
    existing_users = auth.load_users()
    if "admin" not in existing_users:
        auth.add_user("admin", "adminpass", role="admin")
    
    app.run(debug=True, host="0.0.0.0", port=5001)
