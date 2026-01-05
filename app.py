import json
import os
import sqlite3
import sys
import traceback
from datetime import datetime, timedelta
from functools import wraps

# Import audio monitor
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from dotenv import load_dotenv
    backend_dir = os.path.join(os.path.dirname(__file__), '..', 'backend')
    env_file = os.path.join(backend_dir, '.env')
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"✅ Loaded environment from: {env_file}")
except ImportError:
    print("⚠️  python-dotenv not installed")

try:
    from audio_monitor import AudioMonitor, Config as AudioConfig
    AUDIO_MONITOR_ENABLED = True
    print("✅ Audio monitoring enabled")
except ImportError as e:
    AUDIO_MONITOR_ENABLED = False
    AudioConfig = None
    print(f"⚠️  Audio monitoring not available: {e}")

# try to solve Azure issue
from urllib.parse import urlencode

from flask import Flask, jsonify, redirect, render_template, request, session, url_for, make_response, g

app = Flask(__name__)

@app.route('/favicon.ico')
def favicon():
    return '', 204  # Return empty response with No Content status
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "your_super_secret_key")

# Import Azure AD authentication
try:
    from auth_azure import (
        require_auth, require_role, require_dachido_admin,
        get_user_from_token, is_dachido_admin,
        get_login_url, get_token_from_code, get_user_info_from_token,
        get_app_roles_from_token, map_role_to_organization_and_role,
        extract_organization_from_email, generate_jwt_token
    )
    AZURE_AUTH_ENABLED = True
    print("✅ Azure AD authentication enabled")
except ImportError as e:
    AZURE_AUTH_ENABLED = False
    print(f"⚠️  Azure AD authentication not available: {e}")
    # Fallback decorators (will fail if used)
    def require_auth(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return jsonify({"error": "Azure AD authentication not configured"}), 500
        return decorated_function
    
    def require_dachido_admin(f):
        return require_auth(f)

# Use Azure AD login_required as the main decorator
login_required = require_auth

# Import auth module for organization management functions (still needed for organizations.json)
import auth

# Import auth module for organization management functions (still needed for organizations.json)
import auth


#######################################################
# Database configuration
# Determine database path once at module load time
if os.environ.get("WEBSITE_INSTANCE_ID"):  # Running on Azure
    DB_PATH = "/home/site/data/fieldforce.db"
    # Ensure directory exists
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
else:
    DB_PATH = "fieldforce.db"

COROMANDEL_COMPANY_CODE = 7007


def get_db_connection():
    """Get database connection using the configured DB_PATH"""
    # Ensure directory exists before connecting
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    _db_connection = sqlite3.connect(DB_PATH)
    _db_connection.row_factory = sqlite3.Row
    return _db_connection


def dict_from_row(row):
    return dict(zip(row.keys(), row))


# Get competitor codes dynamically or use fallback
def get_competitor_codes():
    """Get actual competitor company codes from database"""
    try:
        conn = get_db_connection()
        query = """
            SELECT company_code, company_name
            FROM dim_companies
            WHERE company_name IN ('BAYER CROP SCIENCE', 'UPL LIMITED', 'SYNGENTA INDIA LTD')
            OR company_code IN (7002, 7025, 7024)
        """
        results = conn.execute(query).fetchall()

        competitors = {}
        for row in results:
            name = row["company_name"].upper()
            if "BAYER" in name:
                competitors["BAYER"] = row["company_code"]
            elif "UPL" in name:
                competitors["UPL"] = row["company_code"]
            elif "SYNGENTA" in name:
                competitors["SYNGENTA"] = row["company_code"]

        # Fallback to default codes if not found
        if "BAYER" not in competitors:
            competitors["BAYER"] = 7002
        if "UPL" not in competitors:
            competitors["UPL"] = 7025
        if "SYNGENTA" not in competitors:
            competitors["SYNGENTA"] = 7024

        return competitors
    except Exception as e:
        print(f"Error loading competitor codes: {e}")
        # Fallback
        return {"BAYER": 7002, "UPL": 7025, "SYNGENTA": 7024}


COMPETITORS = get_competitor_codes()


def parse_date_filter(date_filter):
    """Parse date filter and return start_date, end_date"""
    end_date = datetime.now()

    if date_filter == "all":
        return None, None
    elif date_filter.isdigit():
        start_date = end_date - timedelta(days=int(date_filter))
        return start_date, end_date
    elif "-" in date_filter:  # Custom date range: "2024-01-01,2024-12-31"
        dates = date_filter.split(",")
        return dates[0], dates[1]
    else:
        start_date = end_date - timedelta(days=30)
        return start_date, end_date


# ==================== FILTER OPTIONS APIs ====================


@app.route("/api/filters/crops")
@login_required
def get_crop_options():
    conn = get_db_connection()
    try:
        query = """
            SELECT DISTINCT dc.crop_code, dc.crop_name, dc.crop_type
            FROM dim_crops dc
            JOIN fact_conversation_entities fce ON dc.crop_code = fce.entity_code
            WHERE fce.entity_type = 'crop'
            AND dc.crop_name != '_OTHERS (PLEASE SPECIFY)'
            AND dc.crop_name != 'No Crop'
            ORDER BY dc.crop_name
        """
        results = conn.execute(query).fetchall()
        return jsonify([dict_from_row(row) for row in results])
    finally:
        conn.close()


@app.route("/api/filters/crop-types")
@login_required
def get_crop_type_options():
    conn = get_db_connection()
    try:
        query = """
            SELECT DISTINCT crop_type
            FROM dim_crops
            WHERE crop_type IS NOT NULL
            AND crop_type != '(blank)'
            AND crop_type != 'No Crop'
            ORDER BY crop_type
        """
        results = conn.execute(query).fetchall()
        return jsonify([row["crop_type"] for row in results])
    finally:
        conn.close()


# ==================== HOME MODULE APIs ====================


@app.route("/api/organizations")
@login_required
def get_organizations():
    """
    Get list of organizations that have data in containers
    Only returns organizations found in Azure Blob Storage containers
    """
    if not g.is_dachido_admin:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        organizations = []
        
        if AUDIO_MONITOR_ENABLED:
            try:
                monitor = AudioMonitor()
                # Discover organizations from blob containers (only orgs with actual data)
                org_names_from_containers = monitor.get_organizations_from_containers()
                
                # Get display names from organizations.json if available
                orgs_data = auth.load_organizations()
                
                for org_name in org_names_from_containers:
                    org_info = orgs_data.get(org_name)
                    display_name = org_info.get("display_name", org_name.title()) if org_info else org_name.title()
                    organizations.append({
                        "name": org_name,
                        "display_name": display_name,
                        "created_at": org_info.get("created_at") if org_info else None
                    })
                
                # Sort by display name
                organizations.sort(key=lambda x: x["display_name"])
            except Exception as e:
                print(f"Error getting organizations from containers: {e}")
                # Fallback to organizations.json if container scan fails
                orgs_data = auth.load_organizations()
                organizations = [
                    {
                        "name": org_name,
                        "display_name": org_data.get("display_name", org_name.title()),
                        "created_at": org_data.get("created_at")
                    }
                    for org_name, org_data in orgs_data.items()
                    if org_name != "dachido"
                ]
                organizations.sort(key=lambda x: x["display_name"])
        else:
            # Fallback if audio monitor not enabled
            orgs_data = auth.load_organizations()
            organizations = [
                {
                    "name": org_name,
                    "display_name": org_data.get("display_name", org_name.title()),
                    "created_at": org_data.get("created_at")
                }
                for org_name, org_data in orgs_data.items()
                if org_name != "dachido"
            ]
            organizations.sort(key=lambda x: x["display_name"])
        
        return jsonify({"organizations": organizations})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/home/kpis")
@login_required
def get_home_kpis():
    conn = get_db_connection()
    date_filter = request.args.get("date", "30")
    crop_filter = request.args.get("crop", "all")
    
    # Dachido admins can view any organization's data via query parameter
    # Note: Currently SQLite doesn't filter by organization, but this is ready for PostgreSQL
    view_organization = None
    if g.is_dachido_admin:
        view_organization = request.args.get("organization")

    try:
        start_date, end_date = parse_date_filter(date_filter)

        date_clause = ""
        params = []
        if start_date and end_date:
            date_clause = "AND fc.created_at >= ? AND fc.created_at <= ?"
            params = [start_date, end_date]

        # Alert Count KPI
        alert_query = f"""
            SELECT COUNT(*) as alert_count
            FROM fact_conversation_metrics fcm
            JOIN fact_conversations fc ON fcm.conversation_id = fc.conversation_id
            WHERE fcm.alert_flag = 1 {date_clause}
        """

        # Market Health KPI
        health_query = f"""
            SELECT AVG(CASE
                WHEN overall_sentiment = 'positive' THEN 100
                WHEN overall_sentiment = 'neutral' THEN 50
                WHEN overall_sentiment = 'negative' THEN 0
            END) as health_score
            FROM fact_conversation_semantics fcs
            JOIN fact_conversations fc ON fcs.conversation_id = fc.conversation_id
            WHERE 1=1 {date_clause}
        """

        # Activity KPI
        activity_query = f"""
            SELECT COUNT(*) as activity_count
            FROM fact_conversations fc
            WHERE 1=1 {date_clause}
        """

        alerts = conn.execute(alert_query, params).fetchone()
        health = conn.execute(health_query, params).fetchone()
        activity = conn.execute(activity_query, params).fetchone()

        return jsonify(
            {
                "alert_count": alerts["alert_count"] or 0,
                "market_health": round(health["health_score"] or 50, 1),
                "activity_count": activity["activity_count"] or 0,
            }
        )
    finally:
        conn.close()


@app.route("/api/home/volume-sentiment")
@login_required
def get_volume_sentiment():
    conn = get_db_connection()
    date_filter = request.args.get("date", "30")

    try:
        start_date, end_date = parse_date_filter(date_filter)

        if start_date and end_date:
            query = """
                SELECT
                    DATE(fc.created_at) as date,
                    COUNT(*) as volume,
                    AVG(CASE
                        WHEN fcs.overall_sentiment = 'positive' THEN 1
                        WHEN fcs.overall_sentiment = 'neutral' THEN 0
                        WHEN fcs.overall_sentiment = 'negative' THEN -1
                    END) as sentiment_score
                FROM fact_conversations fc
                JOIN fact_conversation_semantics fcs ON fc.conversation_id = fcs.conversation_id
                WHERE fc.created_at >= ? AND fc.created_at <= ?
                GROUP BY DATE(fc.created_at)
                ORDER BY date
            """
            results = conn.execute(query, (start_date, end_date)).fetchall()
        else:
            query = """
                SELECT
                    DATE(fc.created_at) as date,
                    COUNT(*) as volume,
                    AVG(CASE
                        WHEN fcs.overall_sentiment = 'positive' THEN 1
                        WHEN fcs.overall_sentiment = 'neutral' THEN 0
                        WHEN fcs.overall_sentiment = 'negative' THEN -1
                    END) as sentiment_score
                FROM fact_conversations fc
                JOIN fact_conversation_semantics fcs ON fc.conversation_id = fcs.conversation_id
                GROUP BY DATE(fc.created_at)
                ORDER BY date
            """
            results = conn.execute(query).fetchall()

        return jsonify(
            {
                "labels": [row["date"] for row in results],
                "volume": [row["volume"] for row in results],
                "sentiment": [
                    round(row["sentiment_score"] * 100, 2)
                    if row["sentiment_score"]
                    else 0
                    for row in results
                ],
            }
        )
    finally:
        conn.close()


@app.route("/api/home/conversation-distribution")
@login_required
def get_conversation_distribution():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                primary_topic,
                COUNT(*) as count
            FROM fact_conversation_semantics
            GROUP BY primary_topic
            ORDER BY count DESC
            LIMIT 5
        """

        results = conn.execute(query).fetchall()

        return jsonify(
            {
                "labels": [row["primary_topic"] for row in results],
                "data": [row["count"] for row in results],
            }
        )
    finally:
        conn.close()


@app.route("/api/home/market-share")
@login_required
def get_market_share():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                dc.company_name,
                COUNT(DISTINCT fce.conversation_id) as mentions
            FROM fact_conversation_entities fce
            JOIN dim_brands db ON fce.entity_code = db.brand_code
            JOIN dim_companies dc ON db.company_code = dc.company_code
            WHERE fce.entity_type = 'brand'
            AND dc.company_code IN (?, ?, ?, ?)
            GROUP BY dc.company_name
            ORDER BY mentions DESC
        """

        results = conn.execute(
            query,
            (
                COROMANDEL_COMPANY_CODE,
                COMPETITORS["BAYER"],
                COMPETITORS["UPL"],
                COMPETITORS["SYNGENTA"],
            ),
        ).fetchall()

        return jsonify(
            {
                "labels": [row["company_name"] for row in results],
                "data": [row["mentions"] for row in results],
            }
        )
    finally:
        conn.close()


@app.route("/api/home/competitive-position")
@login_required
def get_competitive_position():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                dc.company_name as brand,
                COUNT(DISTINCT fce.conversation_id) as mentions,
                ROUND(COUNT(DISTINCT fce.conversation_id) * 100.0 /
                    (SELECT COUNT(DISTINCT conversation_id) FROM fact_conversation_entities WHERE entity_type = 'brand'), 1) as share,
                0 as score
            FROM fact_conversation_entities fce
            JOIN dim_brands db ON fce.entity_code = db.brand_code
            JOIN dim_companies dc ON db.company_code = dc.company_code
            WHERE fce.entity_type = 'brand'
            AND dc.company_code IN (?, ?, ?, ?)
            GROUP BY dc.company_name
            ORDER BY share DESC
            LIMIT 3
        """

        results = conn.execute(
            query,
            (
                COROMANDEL_COMPANY_CODE,
                COMPETITORS["BAYER"],
                COMPETITORS["UPL"],
                COMPETITORS["SYNGENTA"],
            ),
        ).fetchall()

        return jsonify([dict_from_row(row) for row in results])
    finally:
        conn.close()


@app.route("/api/home/conversation-drivers")
@login_required
def get_conversation_drivers():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                intent as driver,
                COUNT(*) as count
            FROM fact_conversation_semantics
            GROUP BY intent
            ORDER BY count DESC
            LIMIT 10
        """

        results = conn.execute(query).fetchall()

        return jsonify(
            {
                "labels": [row["driver"] for row in results],
                "data": [row["count"] for row in results],
            }
        )
    finally:
        conn.close()


# ==================== MARKETING MODULE APIs ====================


@app.route("/api/marketing/brand-health-trend")
@login_required
def get_brand_health_trend():
    conn = get_db_connection()
    date_filter = request.args.get("date", "30")

    try:
        start_date, end_date = parse_date_filter(date_filter)

        if start_date and end_date:
            query = """
                SELECT
                    DATE(fc.created_at) as date,
                    COUNT(*) as volume,
                    50 as health
                FROM fact_conversations fc
                JOIN fact_conversation_entities fce ON fc.conversation_id = fce.conversation_id
                JOIN dim_brands db ON fce.entity_code = db.brand_code
                WHERE db.company_code = ?
                AND fce.entity_type = 'brand'
                AND fc.created_at >= ? AND fc.created_at <= ?
                GROUP BY DATE(fc.created_at)
                ORDER BY date
            """
            results = conn.execute(
                query, (COROMANDEL_COMPANY_CODE, start_date, end_date)
            ).fetchall()
        else:
            query = """
                SELECT
                    DATE(fc.created_at) as date,
                    COUNT(*) as volume,
                    50 as health
                FROM fact_conversations fc
                JOIN fact_conversation_entities fce ON fc.conversation_id = fce.conversation_id
                JOIN dim_brands db ON fce.entity_code = db.brand_code
                WHERE db.company_code = ?
                AND fce.entity_type = 'brand'
                GROUP BY DATE(fc.created_at)
                ORDER BY date
            """
            results = conn.execute(query, (COROMANDEL_COMPANY_CODE,)).fetchall()

        return jsonify(
            {
                "labels": [row["date"] for row in results],
                "volume": [row["volume"] for row in results],
                "health": [
                    round(row["health"], 2) if row["health"] is not None else 50
                    for row in results
                ],
            }
        )
    finally:
        conn.close()


@app.route("/api/marketing/conv-volume-by-topic")
@login_required
def get_conv_volume_by_topic():
    conn = get_db_connection()
    date_filter = request.args.get("date", "30")

    try:
        start_date, end_date = parse_date_filter(date_filter)

        if start_date and end_date:
            query = """
                SELECT
                    DATE(fc.created_at) as date,
                    fcs.primary_topic,
                    COUNT(*) as count
                FROM fact_conversations fc
                JOIN fact_conversation_semantics fcs ON fc.conversation_id = fcs.conversation_id
                WHERE fc.created_at >= ? AND fc.created_at <= ?
                GROUP BY DATE(fc.created_at), fcs.primary_topic
                ORDER BY date, count DESC
            """
            results = conn.execute(query, (start_date, end_date)).fetchall()
        else:
            query = """
                SELECT
                    DATE(fc.created_at) as date,
                    fcs.primary_topic,
                    COUNT(*) as count
                FROM fact_conversations fc
                JOIN fact_conversation_semantics fcs ON fc.conversation_id = fcs.conversation_id
                GROUP BY DATE(fc.created_at), fcs.primary_topic
                ORDER BY date, count DESC
            """
            results = conn.execute(query).fetchall()

        # Reorganize data
        dates = sorted(list(set([row["date"] for row in results])))
        topics = list(set([row["primary_topic"] for row in results]))[:5]  # Top 5 topics

        datasets = {}
        for topic in topics:
            datasets[topic] = [0] * len(dates)

        for row in results:
            if row["primary_topic"] in topics:
                date_idx = dates.index(row["date"])
                datasets[row["primary_topic"]][date_idx] = row["count"]

        return jsonify(
            {
                "labels": dates,
                "datasets": [
                    {"label": topic, "data": data} for topic, data in datasets.items()
                ],
            }
        )
    finally:
        conn.close()


@app.route("/api/marketing/brand-keywords")
@login_required
def get_brand_keywords():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                db.brand_name as word,
                COUNT(*) as weight
            FROM fact_conversation_entities fce
            JOIN dim_brands db ON fce.entity_code = db.brand_code
            WHERE fce.entity_type = 'brand'
            AND db.company_code = ?
            GROUP BY db.brand_name
            ORDER BY weight DESC
            LIMIT 50
        """

        results = conn.execute(query, (COROMANDEL_COMPANY_CODE,)).fetchall()

        return jsonify(
            [{"text": row["word"], "size": row["weight"]} for row in results]
        )
    finally:
        conn.close()


@app.route("/api/marketing/market-share-trend")
@login_required
def get_market_share_trend():
    conn = get_db_connection()
    date_filter = request.args.get("date", "30")

    try:
        start_date, end_date = parse_date_filter(date_filter)

        if start_date and end_date:
            query = """
                SELECT
                    DATE(fc.created_at) as date,
                    dc.company_name,
                    COUNT(DISTINCT fce.conversation_id) as mentions
                FROM fact_conversations fc
                JOIN fact_conversation_entities fce ON fc.conversation_id = fce.conversation_id
                JOIN dim_brands db ON fce.entity_code = db.brand_code
                JOIN dim_companies dc ON db.company_code = dc.company_code
                WHERE fce.entity_type = 'brand'
                AND dc.company_code IN (?, ?, ?, ?)
                AND fc.created_at >= ? AND fc.created_at <= ?
                GROUP BY DATE(fc.created_at), dc.company_name
                ORDER BY date
            """
            results = conn.execute(
                query,
                (
                    COROMANDEL_COMPANY_CODE,
                    COMPETITORS["BAYER"],
                    COMPETITORS["UPL"],
                    COMPETITORS["SYNGENTA"],
                    start_date,
                    end_date,
                ),
            ).fetchall()
        else:
            query = """
                SELECT
                    DATE(fc.created_at) as date,
                    dc.company_name,
                    COUNT(DISTINCT fce.conversation_id) as mentions
                FROM fact_conversations fc
                JOIN fact_conversation_entities fce ON fc.conversation_id = fce.conversation_id
                JOIN dim_brands db ON fce.entity_code = db.brand_code
                JOIN dim_companies dc ON db.company_code = dc.company_code
                WHERE fce.entity_type = 'brand'
                AND dc.company_code IN (?, ?, ?, ?)
                GROUP BY DATE(fc.created_at), dc.company_name
                ORDER BY date
            """
            results = conn.execute(
                query,
                (
                    COROMANDEL_COMPANY_CODE,
                    COMPETITORS["BAYER"],
                    COMPETITORS["UPL"],
                    COMPETITORS["SYNGENTA"],
                ),
            ).fetchall()

        dates = sorted(list(set([row["date"] for row in results])))
        companies = list(set([row["company_name"] for row in results]))

        datasets = {}
        for company in companies:
            datasets[company] = [0] * len(dates)

        for row in results:
            date_idx = dates.index(row["date"])
            datasets[row["company_name"]][date_idx] = row["mentions"]

        return jsonify(
            {
                "labels": dates,
                "datasets": [
                    {"label": company, "data": data}
                    for company, data in datasets.items()
                ],
            }
        )
    finally:
        conn.close()


@app.route("/api/marketing/competitive-landscape")
@login_required
def get_competitive_landscape():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                dc.company_name,
                COUNT(DISTINCT fce.conversation_id) as x,
                0 as y,
                COUNT(DISTINCT fce.conversation_id) as r
            FROM fact_conversation_entities fce
            JOIN dim_brands db ON fce.entity_code = db.brand_code
            JOIN dim_companies dc ON db.company_code = dc.company_code
            WHERE fce.entity_type = 'brand'
            AND dc.company_code IN (?, ?, ?, ?)
            GROUP BY dc.company_name
        """

        results = conn.execute(
            query,
            (
                COROMANDEL_COMPANY_CODE,
                COMPETITORS["BAYER"],
                COMPETITORS["UPL"],
                COMPETITORS["SYNGENTA"],
            ),
        ).fetchall()

        return jsonify([dict_from_row(row) for row in results])
    finally:
        conn.close()


@app.route("/api/marketing/sentiment-by-competitor")
@login_required
def get_sentiment_by_competitor():
    conn = get_db_connection()
    date_filter = request.args.get("date", "30")

    try:
        start_date, end_date = parse_date_filter(date_filter)

        if start_date and end_date:
            query = """
                SELECT
                    DATE(fc.created_at) as date,
                    dc.company_name,
                    50 as sentiment
                FROM fact_conversations fc
                JOIN fact_conversation_entities fce ON fc.conversation_id = fce.conversation_id
                JOIN dim_brands db ON fce.entity_code = db.brand_code
                JOIN dim_companies dc ON db.company_code = dc.company_code
                WHERE fce.entity_type = 'brand'
                AND dc.company_code IN (?, ?, ?, ?)
                AND fc.created_at >= ? AND fc.created_at <= ?
                GROUP BY DATE(fc.created_at), dc.company_name
                ORDER BY date
            """
            results = conn.execute(
                query,
                (
                    COROMANDEL_COMPANY_CODE,
                    COMPETITORS["BAYER"],
                    COMPETITORS["UPL"],
                    COMPETITORS["SYNGENTA"],
                    start_date,
                    end_date,
                ),
            ).fetchall()
        else:
            query = """
                SELECT
                    DATE(fc.created_at) as date,
                    dc.company_name,
                    50 as sentiment
                FROM fact_conversations fc
                JOIN fact_conversation_entities fce ON fc.conversation_id = fce.conversation_id
                JOIN dim_brands db ON fce.entity_code = db.brand_code
                JOIN dim_companies dc ON db.company_code = dc.company_code
                WHERE fce.entity_type = 'brand'
                AND dc.company_code IN (?, ?, ?, ?)
                AND fce.overall_sentiment IS NOT NULL
                GROUP BY DATE(fc.created_at), dc.company_name
                ORDER BY date
            """
            results = conn.execute(
                query,
                (
                    COROMANDEL_COMPANY_CODE,
                    COMPETITORS["BAYER"],
                    COMPETITORS["UPL"],
                    COMPETITORS["SYNGENTA"],
                ),
            ).fetchall()

        # Get all unique dates and companies
        dates = sorted(list(set([row["date"] for row in results])))

        # Create datasets for each company
        company_data = {}
        for row in results:
            if row["company_name"] not in company_data:
                company_data[row["company_name"]] = {}
            company_data[row["company_name"]][row["date"]] = (
                round(row["sentiment"], 2) if row["sentiment"] is not None else 50
            )

        # Fill in missing dates with null or previous value
        datasets = []
        for company_name, data in company_data.items():
            dataset_values = []
            for date in dates:
                dataset_values.append(data.get(date, None))
            datasets.append({"label": company_name, "data": dataset_values})

        return jsonify({"labels": dates, "datasets": datasets})
    finally:
        conn.close()


@app.route("/api/marketing/brand-crop-association")
@login_required
def get_brand_crop_association():
    conn = get_db_connection()

    try:
        # Get ALL Rallis brands with crop associations
        query = """
            SELECT
                db.brand_name as parent,
                mbcm.crop_name as label,
                mbcm.co_mentions as value
            FROM mart_brand_crop_matrix mbcm
            JOIN dim_brands db ON mbcm.brand_code = db.brand_code
            WHERE db.company_code = ?
            AND mbcm.co_mentions > 0
            ORDER BY db.brand_name, mbcm.co_mentions DESC
        """

        results = conn.execute(query, (COROMANDEL_COMPANY_CODE,)).fetchall()

        return jsonify([dict_from_row(row) for row in results])
    finally:
        conn.close()


# ==================== OPERATIONS MODULE APIs ====================


@app.route("/api/operations/urgent-issues")
@login_required
def get_urgent_issues():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                fc.conversation_id,
                fc.created_at,
                fc.user_text,
                fcs.urgency,
                fcs.primary_topic,
                fcs.overall_sentiment
            FROM fact_conversations fc
            JOIN fact_conversation_semantics fcs ON fc.conversation_id = fcs.conversation_id
            WHERE fcs.urgency IN ('high', 'critical')
            ORDER BY fc.created_at DESC
            LIMIT 50
        """

        results = conn.execute(query).fetchall()

        return jsonify([dict_from_row(row) for row in results])
    finally:
        conn.close()


@app.route("/api/operations/demand-signal-trend")
@login_required
def get_demand_signal_trend():
    conn = get_db_connection()
    date_filter = request.args.get("date", "30")

    try:
        start_date, end_date = parse_date_filter(date_filter)

        if start_date and end_date:
            query = """
                SELECT
                    DATE(fc.created_at) as date,
                    COUNT(CASE WHEN fcs.intent IN ('purchase', 'request_info', 'seek_advice') THEN 1 END) as demand_signal
                FROM fact_conversations fc
                JOIN fact_conversation_semantics fcs ON fc.conversation_id = fcs.conversation_id
                WHERE fc.created_at >= ? AND fc.created_at <= ?
                GROUP BY DATE(fc.created_at)
                ORDER BY date
            """
            results = conn.execute(query, (start_date, end_date)).fetchall()
        else:
            query = """
                SELECT
                    DATE(fc.created_at) as date,
                    COUNT(CASE WHEN fcs.intent IN ('purchase', 'request_info', 'seek_advice') THEN 1 END) as demand_signal
                FROM fact_conversations fc
                JOIN fact_conversation_semantics fcs ON fc.conversation_id = fcs.conversation_id
                GROUP BY DATE(fc.created_at)
                ORDER BY date
            """
            results = conn.execute(query).fetchall()

        return jsonify(
            {
                "labels": [row["date"] for row in results],
                "data": [row["demand_signal"] for row in results],
            }
        )
    finally:
        conn.close()


@app.route("/api/operations/demand-change-alert")
@login_required
def get_demand_change_alert():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                dc.crop_name,
                COUNT(*) as current_demand,
                'stable' as trend,
                0 as change_pct
            FROM fact_conversation_entities fce
            JOIN dim_crops dc ON fce.entity_code = dc.crop_code
            WHERE fce.entity_type = 'crop'
            GROUP BY dc.crop_name
            ORDER BY current_demand DESC
            LIMIT 10
        """

        results = conn.execute(query).fetchall()
        return jsonify([dict_from_row(row) for row in results])
    finally:
        conn.close()


@app.route("/api/operations/crop-pest-heatmap")
@login_required
def get_crop_pest_heatmap():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                crop_name,
                pest_name,
                co_mentions
            FROM mart_crop_pest_matrix
            ORDER BY co_mentions DESC
            LIMIT 100
        """

        results = conn.execute(query).fetchall()

        return jsonify([dict_from_row(row) for row in results])
    finally:
        conn.close()


@app.route("/api/operations/problem-trend")
@login_required
def get_problem_trend():
    conn = get_db_connection()
    date_filter = request.args.get("date", "30")

    try:
        start_date, end_date = parse_date_filter(date_filter)

        if start_date and end_date:
            query = """
                SELECT
                    DATE(fc.created_at) as date,
                    fcs.primary_topic as topic,
                    COUNT(*) as count
                FROM fact_conversations fc
                JOIN fact_conversation_semantics fcs ON fc.conversation_id = fcs.conversation_id
                WHERE fcs.primary_topic IN ('pest', 'disease', 'weed', 'crop_damage')
                AND fc.created_at >= ? AND fc.created_at <= ?
                GROUP BY DATE(fc.created_at), fcs.primary_topic
                ORDER BY date
            """
            results = conn.execute(query, (start_date, end_date)).fetchall()
        else:
            query = """
                SELECT
                    DATE(fc.created_at) as date,
                    fcs.primary_topic as topic,
                    COUNT(*) as count
                FROM fact_conversations fc
                JOIN fact_conversation_semantics fcs ON fc.conversation_id = fcs.conversation_id
                WHERE fcs.primary_topic IN ('pest', 'disease', 'weed', 'crop_damage')
                GROUP BY DATE(fc.created_at), fcs.primary_topic
                ORDER BY date
            """
            results = conn.execute(query).fetchall()

        dates = sorted(list(set([row["date"] for row in results])))
        topics = ["pest", "disease", "weed", "crop_damage"]

        datasets = {}
        for topic in topics:
            datasets[topic] = [0] * len(dates)

        for row in results:
            if row["topic"] in topics and row["date"] in dates:
                date_idx = dates.index(row["date"])
                datasets[row["topic"]][date_idx] = row["count"]

        return jsonify(
            {
                "labels": dates,
                "datasets": [
                    {"label": topic.capitalize(), "data": data}
                    for topic, data in datasets.items()
                ],
            }
        )
    finally:
        conn.close()


@app.route("/api/operations/problem-sentiment")
@login_required
def get_problem_sentiment():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                fcs.primary_topic as topic,
                fcs.overall_sentiment as sentiment,
                COUNT(*) as count
            FROM fact_conversation_semantics fcs
            WHERE fcs.primary_topic IN ('pest', 'disease', 'weed')
            GROUP BY fcs.primary_topic, fcs.overall_sentiment
            ORDER BY count DESC
        """

        results = conn.execute(query).fetchall()

        topics = sorted(list(set([row["topic"] for row in results])))

        positive = [0] * len(topics)
        neutral = [0] * len(topics)
        negative = [0] * len(topics)

        for row in results:
            if row["topic"] in topics:
                idx = topics.index(row["topic"])
                if row["sentiment"] == "positive":
                    positive[idx] = row["count"]
                elif row["sentiment"] == "neutral":
                    neutral[idx] = row["count"]
                elif row["sentiment"] == "negative":
                    negative[idx] = row["count"]

        return jsonify(
            {
                "labels": topics,
                "datasets": [
                    {"label": "Positive", "data": positive},
                    {"label": "Neutral", "data": neutral},
                    {"label": "Negative", "data": negative},
                ],
            }
        )
    finally:
        conn.close()


@app.route("/api/operations/crop-keywords")
@login_required
def get_crop_keywords():
    conn = get_db_connection()

    try:
        # Get all crops with their mention counts
        query = """
            SELECT
                dc.crop_name as word,
                COUNT(DISTINCT fce.conversation_id) as weight
            FROM fact_conversation_entities fce
            JOIN dim_crops dc ON fce.entity_code = dc.crop_code
            WHERE fce.entity_type = 'crop'
            AND dc.crop_name NOT IN ('_OTHERS (PLEASE SPECIFY)', 'No Crop')
            AND dc.crop_name IS NOT NULL
            GROUP BY dc.crop_name
            ORDER BY weight DESC
            LIMIT 50
        """

        results = conn.execute(query).fetchall()

        if len(results) == 0:
            # Fallback: get from dim_crops directly
            query2 = """
                SELECT DISTINCT crop_name as word, 1 as weight
                FROM dim_crops
                WHERE crop_name NOT IN ('_OTHERS (PLEASE SPECIFY)', 'No Crop')
                AND crop_name IS NOT NULL
                AND crop_type != '(blank)'
                LIMIT 50
            """
            results = conn.execute(query2).fetchall()

        return jsonify(
            [
                {"text": row["word"], "size": row["weight"]}
                for row in results
                if row["word"]
            ]
        )
    finally:
        conn.close()


@app.route("/api/operations/solution-flow")
@login_required
def get_solution_flow():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                crop_name,
                pest_name,
                brand_name,
                flow_count
            FROM mart_crop_pest_brand_flow
            ORDER BY flow_count DESC
            LIMIT 50
        """

        results = conn.execute(query).fetchall()

        return jsonify([dict_from_row(row) for row in results])
    finally:
        conn.close()


@app.route("/api/operations/solution-effectiveness")
@login_required
def get_solution_effectiveness():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                db.brand_name as solution,
                COUNT(DISTINCT fce.conversation_id) as effectiveness
            FROM fact_conversation_entities fce
            JOIN dim_brands db ON fce.entity_code = db.brand_code
            WHERE fce.entity_type = 'brand'
            GROUP BY db.brand_name
            ORDER BY effectiveness DESC
            LIMIT 10
        """

        results = conn.execute(query).fetchall()

        return jsonify(
            {
                "labels": [row["solution"] for row in results],
                "data": [row["effectiveness"] for row in results],
            }
        )
    finally:
        conn.close()


@app.route("/api/operations/solution-sentiment")
@login_required
def get_solution_sentiment():
    conn = get_db_connection()
    date_filter = request.args.get("date", "30")

    try:
        start_date, end_date = parse_date_filter(date_filter)

        if start_date and end_date:
            query = """
                SELECT
                    DATE(fc.created_at) as date,
                    50 as sentiment
                FROM fact_conversations fc
                JOIN fact_conversation_entities fce ON fc.conversation_id = fce.conversation_id
                WHERE fce.entity_type = 'brand'
                AND fc.created_at >= ? AND fc.created_at <= ?
                GROUP BY DATE(fc.created_at)
                HAVING COUNT(*) > 0
                ORDER BY date
            """
            results = conn.execute(query, (start_date, end_date)).fetchall()
        else:
            query = """
                SELECT
                    DATE(fc.created_at) as date,
                    50 as sentiment
                FROM fact_conversations fc
                JOIN fact_conversation_entities fce ON fc.conversation_id = fce.conversation_id
                WHERE fce.entity_type = 'brand'
                GROUP BY DATE(fc.created_at)
                HAVING COUNT(*) > 0
                ORDER BY date
            """
            results = conn.execute(query).fetchall()

        return jsonify(
            {
                "labels": [row["date"] for row in results],
                "data": [
                    round(row["sentiment"], 2) if row["sentiment"] is not None else None
                    for row in results
                ],
            }
        )
    finally:
        conn.close()


@app.route("/api/operations/sentiment-by-crop")
@login_required
def get_sentiment_by_crop():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                dc.crop_name,
                COUNT(*) as count
            FROM fact_conversation_entities fce
            JOIN dim_crops dc ON fce.entity_code = dc.crop_code
            WHERE fce.entity_type = 'crop'
            AND dc.crop_name NOT IN ('_OTHERS (PLEASE SPECIFY)', 'No Crop')
            GROUP BY dc.crop_name
            ORDER BY count DESC
        """

        results = conn.execute(query).fetchall()

        # Get top 10 crops by total mentions
        crop_totals = {}
        for row in results:
            if row["crop_name"] not in crop_totals:
                crop_totals[row["crop_name"]] = 0
            crop_totals[row["crop_name"]] += row["count"]

        top_crops = sorted(crop_totals.items(), key=lambda x: x[1], reverse=True)[:10]
        crops = [c[0] for c in top_crops]

        positive = [0] * len(crops)
        neutral = [0] * len(crops)
        negative = [0] * len(crops)

        return jsonify(
            {
                "labels": crops,
                "datasets": [
                    {"label": "Positive", "data": positive},
                    {"label": "Neutral", "data": neutral},
                    {"label": "Negative", "data": negative},
                ],
            }
        )
    finally:
        conn.close()


# ==================== ENGAGEMENT MODULE APIs ====================


@app.route("/api/engagement/conv-by-region")
@login_required
def get_conv_by_region():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                du.district as region,
                COUNT(*) as count
            FROM fact_conversations fc
            JOIN dim_user du ON fc.user_id = du.user_id
            GROUP BY du.district
            ORDER BY count DESC
            LIMIT 20
        """

        results = conn.execute(query).fetchall()

        return jsonify(
            {
                "labels": [row["region"] for row in results],
                "data": [row["count"] for row in results],
            }
        )
    finally:
        conn.close()


@app.route("/api/engagement/team-urgency")
@login_required
def get_team_urgency():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                urgency,
                COUNT(*) as count
            FROM fact_conversation_semantics
            GROUP BY urgency
        """

        results = conn.execute(query).fetchall()

        return jsonify(
            {
                "labels": [row["urgency"] for row in results],
                "data": [row["count"] for row in results],
            }
        )
    finally:
        conn.close()


@app.route("/api/engagement/team-intent")
@login_required
def get_team_intent():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                intent,
                COUNT(*) as count
            FROM fact_conversation_semantics
            GROUP BY intent
            ORDER BY count DESC
            LIMIT 5
        """

        results = conn.execute(query).fetchall()

        return jsonify(
            {
                "labels": [row["intent"] for row in results],
                "data": [row["count"] for row in results],
            }
        )
    finally:
        conn.close()


@app.route("/api/engagement/quality-by-region")
@login_required
def get_quality_by_region():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                du.district as region,
                fcs.overall_sentiment as sentiment,
                COUNT(*) as count
            FROM fact_conversations fc
            JOIN dim_user du ON fc.user_id = du.user_id
            JOIN fact_conversation_semantics fcs ON fc.conversation_id = fcs.conversation_id
            GROUP BY du.district, fcs.overall_sentiment
            ORDER BY count DESC
            LIMIT 60
        """

        results = conn.execute(query).fetchall()

        regions = sorted(list(set([row["region"] for row in results])))[:10]

        positive = [0] * len(regions)
        neutral = [0] * len(regions)
        negative = [0] * len(regions)

        for row in results:
            if row["region"] in regions:
                idx = regions.index(row["region"])
                if row["sentiment"] == "positive":
                    positive[idx] = row["count"]
                elif row["sentiment"] == "neutral":
                    neutral[idx] = row["count"]
                elif row["sentiment"] == "negative":
                    negative[idx] = row["count"]

        return jsonify(
            {
                "labels": regions,
                "datasets": [
                    {"label": "Positive", "data": positive},
                    {"label": "Neutral", "data": neutral},
                    {"label": "Negative", "data": negative},
                ],
            }
        )
    finally:
        conn.close()


@app.route("/api/engagement/agent-scorecard")
@login_required
def get_agent_scorecard():
    conn = get_db_connection()

    try:
        # Simulated agent performance data
        query = """
            SELECT
                du.full_name as agent_name,
                COUNT(fc.conversation_id) as total_convs,
                AVG(CASE
                    WHEN fcs.overall_sentiment = 'positive' THEN 100
                    WHEN fcs.overall_sentiment = 'neutral' THEN 50
                    WHEN fcs.overall_sentiment = 'negative' THEN 0
                END) as avg_sentiment,
                COUNT(CASE WHEN fcs.urgency IN ('high', 'critical') THEN 1 END) as urgent_handled
            FROM fact_conversations fc
            JOIN dim_user du ON fc.user_id = du.user_id
            JOIN fact_conversation_semantics fcs ON fc.conversation_id = fcs.conversation_id
            GROUP BY du.full_name
            ORDER BY total_convs DESC
            LIMIT 20
        """

        results = conn.execute(query).fetchall()
        return jsonify([dict_from_row(row) for row in results])
    finally:
        conn.close()


@app.route("/api/engagement/agent-leaderboard")
def get_agent_leaderboard():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                du.full_name as agent_name,
                COUNT(fc.conversation_id) as conversations,
                AVG(CASE
                    WHEN fcs.overall_sentiment = 'positive' THEN 3
                    WHEN fcs.overall_sentiment = 'neutral' THEN 2
                    WHEN fcs.overall_sentiment = 'negative' THEN 1
                END) as performance_score
            FROM fact_conversations fc
            JOIN dim_user du ON fc.user_id = du.user_id
            JOIN fact_conversation_semantics fcs ON fc.conversation_id = fcs.conversation_id
            GROUP BY du.full_name
            ORDER BY performance_score DESC, conversations DESC
            LIMIT 10
        """

        results = conn.execute(query).fetchall()
        return jsonify([dict_from_row(row) for row in results])
    finally:
        conn.close()


@app.route("/api/engagement/agent-perf-trend")
def get_agent_perf_trend():
    conn = get_db_connection()
    date_filter = request.args.get("date", "30")

    try:
        start_date, end_date = parse_date_filter(date_filter)

        if start_date and end_date:
            query = """
                SELECT
                    DATE(fc.created_at) as date,
                    du.full_name as agent,
                    COUNT(*) as conversations
                FROM fact_conversations fc
                JOIN dim_user du ON fc.user_id = du.user_id
                WHERE fc.created_at >= ? AND fc.created_at <= ?
                GROUP BY DATE(fc.created_at), du.full_name
                ORDER BY date
            """
            results = conn.execute(query, (start_date, end_date)).fetchall()
        else:
            query = """
                SELECT
                    DATE(fc.created_at) as date,
                    du.full_name as agent,
                    COUNT(*) as conversations
                FROM fact_conversations fc
                JOIN dim_user du ON fc.user_id = du.user_id
                GROUP BY DATE(fc.created_at), du.full_name
                ORDER BY date
            """
            results = conn.execute(query).fetchall()

        dates = sorted(list(set([row["date"] for row in results])))
        agents = list(set([row["agent"] for row in results]))[:5]  # Top 5 agents

        datasets = {}
        for agent in agents:
            datasets[agent] = [0] * len(dates)

        for row in results:
            if row["agent"] in agents and row["date"] in dates:
                date_idx = dates.index(row["date"])
                datasets[row["agent"]][date_idx] = row["conversations"]

        return jsonify(
            {
                "labels": dates,
                "datasets": [
                    {"label": agent, "data": data} for agent, data in datasets.items()
                ],
            }
        )
    finally:
        conn.close()


@app.route("/api/engagement/field-leaders")
def get_field_leaders():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                du.full_name as name,
                COUNT(fc.conversation_id) as x,
                AVG(CASE
                    WHEN fcs.overall_sentiment = 'positive' THEN 100
                    WHEN fcs.overall_sentiment = 'neutral' THEN 50
                    WHEN fcs.overall_sentiment = 'negative' THEN 0
                END) as y,
                COUNT(fc.conversation_id) as r
            FROM fact_conversations fc
            JOIN dim_user du ON fc.user_id = du.user_id
            JOIN fact_conversation_semantics fcs ON fc.conversation_id = fcs.conversation_id
            GROUP BY du.full_name
            ORDER BY x DESC
            LIMIT 20
        """

        results = conn.execute(query).fetchall()
        return jsonify([dict_from_row(row) for row in results])
    finally:
        conn.close()


@app.route("/api/engagement/sentiment-by-entity")
def get_sentiment_by_entity():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                fce.entity_type,
                COUNT(*) as count
            FROM fact_conversation_entities fce
            WHERE fce.entity_type IN ('brand', 'crop', 'pest')
            GROUP BY fce.entity_type
            ORDER BY count DESC
        """

        results = conn.execute(query).fetchall()

        entities = sorted(list(set([row["entity_type"] for row in results])))

        positive = [0] * len(entities)
        neutral = [0] * len(entities)
        negative = [0] * len(entities)

        return jsonify(
            {
                "labels": [e.capitalize() for e in entities],
                "datasets": [
                    {"label": "Positive", "data": positive},
                    {"label": "Neutral", "data": neutral},
                    {"label": "Negative", "data": negative},
                ],
            }
        )
    finally:
        conn.close()


@app.route("/api/engagement/topic-distribution")
def get_topic_distribution():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                primary_topic as label,
                COUNT(*) as value
            FROM fact_conversation_semantics
            GROUP BY primary_topic
            ORDER BY value DESC
        """

        results = conn.execute(query).fetchall()
        return jsonify([dict_from_row(row) for row in results])
    finally:
        conn.close()


@app.route("/api/engagement/training-needs")
def get_training_needs():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                du.full_name as agent_name,
                fcs.primary_topic as weak_area,
                COUNT(CASE WHEN fcs.overall_sentiment = 'negative' THEN 1 END) as negative_count,
                'Needs training in ' || fcs.primary_topic as recommendation
            FROM fact_conversations fc
            JOIN dim_user du ON fc.user_id = du.user_id
            JOIN fact_conversation_semantics fcs ON fc.conversation_id = fcs.conversation_id
            WHERE fcs.overall_sentiment = 'negative'
            GROUP BY du.full_name, fcs.primary_topic
            HAVING COUNT(CASE WHEN fcs.overall_sentiment = 'negative' THEN 1 END) > 2
            ORDER BY negative_count DESC
            LIMIT 20
        """

        results = conn.execute(query).fetchall()
        return jsonify([dict_from_row(row) for row in results])
    finally:
        conn.close()


# ==================== ADMIN MODULE APIs ====================


@app.route("/api/admin/users")
def get_users():
    conn = get_db_connection()

    try:
        query = "SELECT * FROM dim_dashboard_users"
        results = conn.execute(query).fetchall()

        return jsonify([dict_from_row(row) for row in results])
    finally:
        conn.close()


@app.route("/api/admin/user-activity-log")
def get_user_activity_log():
    conn = get_db_connection()

    try:
        query = """
            SELECT
                du.full_name as user_name,
                COUNT(fc.conversation_id) as activity_count,
                MAX(fc.created_at) as last_active,
                du.district as location
            FROM dim_user du
            LEFT JOIN fact_conversations fc ON du.user_id = fc.user_id
            GROUP BY du.full_name, du.district
            ORDER BY activity_count DESC
            LIMIT 50
        """

        results = conn.execute(query).fetchall()
        return jsonify([dict_from_row(row) for row in results])
    finally:
        conn.close()


@app.route("/api/admin/completeness-kpi")
def get_completeness_kpi():
    conn = get_db_connection()

    try:
        # Calculate data completeness metrics
        total_convs = conn.execute(
            "SELECT COUNT(*) as count FROM fact_conversations"
        ).fetchone()["count"]

        with_semantics = conn.execute("""
            SELECT COUNT(DISTINCT conversation_id) as count
            FROM fact_conversation_semantics
        """).fetchone()["count"]

        with_entities = conn.execute("""
            SELECT COUNT(DISTINCT conversation_id) as count
            FROM fact_conversation_entities
        """).fetchone()["count"]

        with_metrics = conn.execute("""
            SELECT COUNT(DISTINCT conversation_id) as count
            FROM fact_conversation_metrics
        """).fetchone()["count"]

        semantics_pct = (
            round((with_semantics / total_convs * 100), 1) if total_convs > 0 else 0
        )
        entities_pct = (
            round((with_entities / total_convs * 100), 1) if total_convs > 0 else 0
        )
        metrics_pct = (
            round((with_metrics / total_convs * 100), 1) if total_convs > 0 else 0
        )
        overall_pct = round((semantics_pct + entities_pct + metrics_pct) / 3, 1)

        return jsonify(
            {
                "total_conversations": total_convs,
                "semantics_completeness": semantics_pct,
                "entities_completeness": entities_pct,
                "metrics_completeness": metrics_pct,
                "overall_completeness": overall_pct,
            }
        )
    finally:
        conn.close()


@app.route("/api/admin/db-stats")
def get_db_stats():
    conn = get_db_connection()

    try:
        stats = {}

        tables = [
            "fact_conversations",
            "fact_conversation_entities",
            "fact_conversation_semantics",
            "dim_brands",
            "dim_crops",
            "dim_pests",
            "dim_user",
        ]

        for table in tables:
            count = conn.execute(f"SELECT COUNT(*) as count FROM {table}").fetchone()
            stats[table] = count["count"]

        date_range = conn.execute("""
            SELECT
                MIN(created_at) as min_date,
                MAX(created_at) as max_date
            FROM fact_conversations
        """).fetchone()

        stats["date_range"] = {
            "min": date_range["min_date"],
            "max": date_range["max_date"],
        }

        return jsonify(stats)
    finally:
        conn.close()


@app.route("/api/debug/companies")
def debug_companies():
    """Debug endpoint to check company data"""
    conn = get_db_connection()
    try:
        # Get all companies
        companies = conn.execute("""
            SELECT company_code, company_name, COUNT(db.brand_code) as brand_count
            FROM dim_companies dc
            LEFT JOIN dim_brands db ON dc.company_code = db.company_code
            GROUP BY dc.company_code, dc.company_name
            ORDER BY brand_count DESC
        """).fetchall()

        # Get companies with sentiment data
        companies_with_data = conn.execute("""
            SELECT DISTINCT dc.company_code, dc.company_name, COUNT(DISTINCT fce.conversation_id) as mentions
            FROM dim_companies dc
            JOIN dim_brands db ON dc.company_code = db.company_code
            JOIN fact_conversation_entities fce ON db.brand_code = fce.entity_code
            WHERE fce.entity_type = 'brand'
            GROUP BY dc.company_code, dc.company_name
            ORDER BY mentions DESC
        """).fetchall()

        return jsonify(
            {
                "all_companies": [dict_from_row(c) for c in companies],
                "companies_with_data": [dict_from_row(c) for c in companies_with_data],
                "configured_competitors": COMPETITORS,
                "rallis_code": COROMANDEL_COMPANY_CODE,
            }
        )
    finally:
        conn.close()


################################################
# User management routes
@app.route("/login")
def azure_login():
    """
    Azure AD login route - redirects to Microsoft login
    """
    if not AZURE_AUTH_ENABLED:
        return render_template("error.html", error="Azure AD authentication is not configured. Please contact administrator."), 500
    
    try:
        login_url = get_login_url()
        return redirect(login_url)
    except Exception as e:
        print(f"⚠️  Error generating login URL: {e}")
        return render_template("error.html", error=f"Authentication error: {e}"), 500


@app.route("/auth/callback")
def azure_auth_callback():
    """
    Azure AD OAuth callback - handles authentication response
    """
    if not AZURE_AUTH_ENABLED:
        return redirect(url_for("azure_login"))
    
    # Get authorization code from query parameters
    auth_code = request.args.get("code")
    error = request.args.get("error")
    
    if error:
        error_description = request.args.get("error_description", error)
        print(f"⚠️  Azure AD authentication error: {error} - {error_description}")
        return render_template("error.html", error=f"Authentication failed: {error_description}"), 400
    
    if not auth_code:
        return redirect(url_for("azure_login"))
    
    try:
        # Exchange code for tokens
        access_token, id_token = get_token_from_code(auth_code)
        
        if not access_token or not id_token:
            return render_template("error.html", error="Failed to obtain access token"), 500
        
        # Get user information from Microsoft Graph
        user_info = get_user_info_from_token(access_token)
        if not user_info:
            return render_template("error.html", error="Failed to retrieve user information"), 500
        
        # Extract app roles from ID token
        azure_roles = get_app_roles_from_token(id_token)
        
        # Map Azure roles to our organization/role system
        organization, role, _ = map_role_to_organization_and_role(azure_roles)
        
        # If organization not determined from role, extract from email
        if not organization:
            email = user_info.get("mail") or user_info.get("userPrincipalName")
            organization = extract_organization_from_email(email)
        
        # If still no organization, use email domain as fallback
        if not organization:
            email = user_info.get("mail") or user_info.get("userPrincipalName")
            if email:
                organization = extract_organization_from_email(email)
        
        # Get username from user info
        username = user_info.get("mail") or user_info.get("userPrincipalName") or user_info.get("displayName", "").replace(" ", ".")
        
        # If no role found, default to customer_admin
        if not role:
            role = "customer_admin"
        
        # If no organization found, use email domain
        if not organization:
            email = user_info.get("mail") or user_info.get("userPrincipalName")
            organization = extract_organization_from_email(email) or "default"
        
        print(f"✅ Azure AD login successful: {organization}:{username} (role: {role})")
        
        # Generate JWT token
        token = generate_jwt_token(username, organization, role)
        
        # Set JWT cookie and redirect to dashboard
        response = make_response(redirect(url_for("index")))
        is_production = bool(os.environ.get("WEBSITE_INSTANCE_ID"))
        response.set_cookie(
            "auth_token",
            token,
            max_age=8 * 60 * 60,  # 8 hours
            httponly=True,
            secure=is_production,
            samesite="Lax",
            path="/"
        )
        
        return response
        
    except Exception as e:
        print(f"⚠️  Azure AD callback error: {e}")
        import traceback
        traceback.print_exc()
        return render_template("error.html", error=f"Authentication error: {str(e)}"), 500


# Registration route removed - users are now managed in Azure AD
# To add users: Azure AD → Enterprise applications → Your app → Users and groups


@app.route("/logout")
def logout():
    """Logout by clearing JWT cookie and redirecting to Azure AD logout"""
    response = make_response(redirect(url_for("azure_login")))
    response.set_cookie("auth_token", "", expires=0)
    
    # Optional: Redirect to Azure AD logout endpoint for complete sign-out
    # Uncomment if you want users to be signed out of Microsoft as well
    # azure_logout_url = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/logout?post_logout_redirect_uri={request.url_root}"
    # return redirect(azure_logout_url)
    
    return response


# Easy Auth routes removed - using local authentication only
# If you need Easy Auth in the future, uncomment these routes


################################################
# User Management API Routes
################################################

@app.route("/api/users", methods=["GET"])
@login_required
@require_dachido_admin
def list_users():
    """List all users (Dachido admin only)"""
    users = auth.load_users()
    organizations = auth.load_organizations()
    
    user_list = []
    for user_key, user_data in users.items():
        if isinstance(user_data, dict):
            org = user_data.get("organization", "")
            username = user_data.get("username", "")
            role = user_data.get("role", "customer_admin")
            org_display = organizations.get(org, {}).get("display_name", org.title()) if org in organizations else org.title()
            
            user_list.append({
                "key": user_key,
                "organization": org,
                "organization_display": org_display,
                "username": username,
                "role": role,
                "created_at": user_data.get("created_at")
            })
    
    return jsonify({"users": user_list})


@app.route("/api/users", methods=["POST"])
@login_required
@require_dachido_admin
def create_user():
    """Create a new user (Dachido admin only)"""
    data = request.get_json()
    organization = data.get("organization", "").strip().lower()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    role = data.get("role", "customer_admin")
    email = data.get("email", "").strip() if data.get("email") else None
    
    if not organization or not username or not password:
        return jsonify({"error": "Organization, username, and password are required"}), 400
    
    if role not in ["admin", "customer_admin", "dachido_admin"]:
        return jsonify({"error": "Invalid role"}), 400
    
    # Validate email if provided
    if email:
        import re
        email_pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}"
        if not re.match(email_pattern, email):
            return jsonify({"error": "Invalid email format"}), 400
    
    # Create organization if it doesn't exist
    auth.add_organization(organization)
    
    try:
        if auth.add_user(organization, username, password, role, email=email):
            return jsonify({"success": True, "message": "User created successfully"}), 201
        else:
            return jsonify({"error": "User already exists"}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/users/<path:user_key>", methods=["PUT"])
@login_required
@require_dachido_admin
def update_user(user_key):
    """Update user (Dachido admin only)"""
    data = request.get_json()
    users = auth.load_users()
    
    if user_key not in users:
        return jsonify({"error": "User not found"}), 404
    
    user_data = users[user_key]
    if not isinstance(user_data, dict):
        return jsonify({"error": "Invalid user format"}), 400
    
    # Update role if provided
    if "role" in data:
        new_role = data["role"]
        if new_role not in ["admin", "customer_admin", "dachido_admin"]:
            return jsonify({"error": "Invalid role"}), 400
        user_data["role"] = new_role
    
    # Update password if provided
    if "password" in data and data["password"]:
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt()
        user_data["password"] = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    
    # Update email if provided
    if "email" in data:
        email = data["email"].strip() if data.get("email") else None
        if email:
            import re
            email_pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}"
            if not re.match(email_pattern, email):
                return jsonify({"error": "Invalid email format"}), 400
        user_data["email"] = email
    
    users[user_key] = user_data
    auth.save_users(users)
    
    return jsonify({"success": True, "message": "User updated successfully"})


@app.route("/api/users/<path:user_key>", methods=["DELETE"])
@login_required
@require_dachido_admin
def delete_user(user_key):
    """Delete user (Dachido admin only)"""
    users = auth.load_users()
    
    if user_key not in users:
        return jsonify({"error": "User not found"}), 404
    
    # Don't allow deleting yourself
    current_user_key = f"{g.organization}:{g.username}"
    if user_key == current_user_key:
        return jsonify({"error": "Cannot delete your own account"}), 400
    
    del users[user_key]
    auth.save_users(users)
    
    return jsonify({"success": True, "message": "User deleted successfully"})


@app.route("/admin/users")
@login_required
@require_dachido_admin
def manage_users():
    """User management page (Dachido admin only)"""
    return render_template("manage_users.html")


# ==================== MAIN ROUTE ====================


@app.route("/")
@login_required
def index():
    """Main dashboard route - routes to organization or Dachido dashboard"""
    organization = g.organization
    role = g.role
    username = g.username
    is_dachido_admin = g.is_dachido_admin
    
    # Get organization display name
    org_info = auth.get_organization(organization)
    org_display_name = org_info.get("display_name", organization.title()) if org_info else organization.title()
    
    # Get all organizations for Dachido admin selector
    # For Dachido admins: Get organizations from containers (only show orgs with data)
    all_organizations = []
    if is_dachido_admin:
        if AUDIO_MONITOR_ENABLED:
            try:
                monitor = AudioMonitor()
                # Discover organizations from blob containers
                org_names_from_containers = monitor.get_organizations_from_containers()
                
                # Get display names from organizations.json if available
                orgs_data = auth.load_organizations()
                
                for org_name in org_names_from_containers:
                    org_info = orgs_data.get(org_name)
                    display_name = org_info.get("display_name", org_name.title()) if org_info else org_name.title()
                    all_organizations.append({
                        "name": org_name,
                        "display_name": display_name
                    })
                
                # Sort by display name
                all_organizations.sort(key=lambda x: x["display_name"])
            except Exception as e:
                print(f"Error getting organizations from containers: {e}")
                # Fallback to organizations.json if container scan fails
                orgs_data = auth.load_organizations()
                all_organizations = [
                    {
                        "name": org_name,
                        "display_name": org_data.get("display_name", org_name.title())
                    }
                    for org_name, org_data in orgs_data.items()
                    if org_name != "dachido"
                ]
                all_organizations.sort(key=lambda x: x["display_name"])
        else:
            # Fallback if audio monitor not enabled
            orgs_data = auth.load_organizations()
            all_organizations = [
                {
                    "name": org_name,
                    "display_name": org_data.get("display_name", org_name.title())
                }
                for org_name, org_data in orgs_data.items()
                if org_name != "dachido"
            ]
            all_organizations.sort(key=lambda x: x["display_name"])
    
    # Route to appropriate dashboard
    if is_dachido_admin:
        # Dachido admin sees Dachido dashboard with organization selector
        return render_template(
            "dashboard.html",
            user_role=role,
            organization=organization,
            organization_display_name="Dachido",
            username=username,
            is_dachido_admin=True,
            all_organizations=all_organizations
        )
    else:
        # Organization users see their organization dashboard
        return render_template(
            "dashboard.html",
            user_role=role,
            organization=organization,
            organization_display_name=org_display_name,
            username=username,
            is_dachido_admin=False,
            all_organizations=[]
        )


################################################

# ==================== AUDIO MONITORING MODULE APIs ====================

@app.route("/api/audio/overview")
@login_required
def get_audio_overview():
    if not AUDIO_MONITOR_ENABLED:
        return jsonify({"error": "Audio monitoring not enabled", "pending": 0, "processed": 0, "failed": 0}), 503
    try:
        # Dachido admins can view any organization's data via query parameter
        if g.is_dachido_admin:
            view_org = request.args.get("organization")
            # Empty string or None means all organizations
            organization = view_org if view_org and view_org.strip() else None
            print(f"🔍 Audio overview - Dachido admin, view_org param: {view_org}, using: {organization}")
        else:
            organization = g.organization
            print(f"🔍 Audio overview - Regular user, organization from JWT: {organization}")
        
        if not organization:
            print(f"⚠️  Warning: No organization specified, returning empty stats")
            return jsonify({"pending": 0, "processed": 0, "failed": 0})
        
        print(f"🔍 Creating AudioMonitor instance...")
        monitor = AudioMonitor()
        if not monitor.enabled:
            print(f"⚠️  AudioMonitor is disabled (missing Azure config)")
            return jsonify({"error": "Audio monitoring not configured", "pending": 0, "processed": 0, "failed": 0}), 503
        
        print(f"🔍 Calling get_overview_stats for organization: {organization}")
        stats = monitor.get_overview_stats(organization=organization)
        print(f"✅ Audio overview stats for {organization}: pending={stats.get('pending')}, processed={stats.get('processed')}, failed={stats.get('failed')}")
        return jsonify(stats)
    except Exception as e:
        import traceback
        print(f"❌ Audio overview error: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e), "pending": 0, "processed": 0, "failed": 0}), 500

@app.route("/api/audio/pending")
@login_required
def get_audio_pending():
    if not AUDIO_MONITOR_ENABLED:
        return jsonify({"error": "Audio monitoring not enabled"}), 503
    try:
        # Dachido admins can view any organization's data via query parameter
        if g.is_dachido_admin:
            view_org = request.args.get("organization")
            # Empty string or None means all organizations
            organization = view_org if view_org and view_org.strip() else None
        else:
            organization = g.organization
        
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        monitor = AudioMonitor()
        result = monitor.get_pending_recordings(limit=limit, offset=offset, organization=organization)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audio/processed")
@login_required
def get_audio_processed():
    if not AUDIO_MONITOR_ENABLED:
        return jsonify({"error": "Audio monitoring not enabled"}), 503
    try:
        # Dachido admins can view any organization's data via query parameter
        if g.is_dachido_admin:
            view_org = request.args.get("organization")
            # Empty string or None means all organizations
            organization = view_org if view_org and view_org.strip() else None
            print(f"🔍 Audio processed - Dachido admin, view_org param: {view_org}, using: {organization}")
        else:
            organization = g.organization
            print(f"🔍 Audio processed - Regular user, organization from JWT: {organization}")
        
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        quality_filter = request.args.get("quality")
        language_filter = request.args.get("language")
        # Only include transcription data if explicitly requested (for detail view)
        include_transcription = request.args.get("include_transcription", "false").lower() == "true"
        
        # Try cache first if organization is specified (faster)
        use_cache = request.args.get("use_cache", "true").lower() == "true"
        if use_cache and organization and organization != "dachido":
            try:
                from audio_cache import get_recordings_from_cache, should_sync_cache, sync_recordings_to_cache
                
                # Check if cache needs sync (every 5 minutes)
                if should_sync_cache(organization, "processed-recordings", max_age_minutes=5):
                    # Sync in background (don't wait)
                    import threading
                    threading.Thread(target=sync_recordings_to_cache, args=(organization, False), daemon=True).start()
                
                # Get from cache
                cache_result = get_recordings_from_cache(organization, "processed", limit, offset)
                if cache_result.get("recordings"):
                    # Apply filters
                    recordings = cache_result["recordings"]
                    if quality_filter:
                        recordings = [r for r in recordings if r.get("quality_rating") == quality_filter]
                    if language_filter:
                        recordings = [r for r in recordings if r.get("language_code") == language_filter or r.get("detected_language") == language_filter]
                    
                    # Hide translations for customer_admin
                    user_role = g.role
                    if user_role == "customer_admin":
                        for recording in recordings:
                            recording.pop("translation", None)
                    
                    return jsonify({
                        "recordings": recordings[:limit],
                        "total": len(recordings),
                        "limit": limit,
                        "offset": offset,
                        "cached": True
                    })
            except ImportError:
                pass  # Cache module not available, fall through to direct query
            except Exception as e:
                print(f"Cache error: {e}")  # Log but continue with direct query
        
        # Fallback to direct Azure query
        print(f"🔍 Creating AudioMonitor for processed recordings (fallback)...")
        monitor = AudioMonitor()
        if not monitor.enabled:
            return jsonify({"error": "Audio monitoring not configured", "recordings": [], "total": 0}), 503
        print(f"🔍 Getting processed recordings for organization: {organization}, limit: {limit}, offset: {offset}")
        result = monitor.get_processed_recordings(
            limit=limit, offset=offset,
            quality_filter=quality_filter,
            language_filter=language_filter,
            include_transcription=include_transcription,
            organization=organization
        )
        print(f"✅ Processed recordings result: {len(result.get('recordings', []))} records, total: {result.get('total', 0)}")
        
        # Hide translations for customer_admin
        user_role = g.role
        if user_role == "customer_admin":
            for recording in result.get("recordings", []):
                # Remove translation but keep transcription
                recording.pop("translation", None)
                # Keep original_transcription but remove translation
                if "transcription" in recording:
                    # transcription field contains the translation, remove it
                    recording["transcription"] = ""
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audio/failed")
@login_required
def get_audio_failed():
    if not AUDIO_MONITOR_ENABLED:
        return jsonify({"error": "Audio monitoring not enabled"}), 503
    try:
        # Dachido admins can view any organization's data via query parameter
        if g.is_dachido_admin:
            view_org = request.args.get("organization")
            # Empty string or None means all organizations
            organization = view_org if view_org and view_org.strip() else None
        else:
            organization = g.organization
        
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        
        # Try cache first if organization is specified
        use_cache = request.args.get("use_cache", "true").lower() == "true"
        if use_cache and organization and organization != "dachido":
            try:
                from audio_cache import get_recordings_from_cache, should_sync_cache, sync_recordings_to_cache
                
                if should_sync_cache(organization, "failedrecordings", max_age_minutes=5):
                    import threading
                    threading.Thread(target=sync_recordings_to_cache, args=(organization, False), daemon=True).start()
                
                cache_result = get_recordings_from_cache(organization, "failed", limit, offset)
                if cache_result.get("recordings"):
                    return jsonify({**cache_result, "cached": True})
            except:
                pass  # Fall through to direct query
        
        monitor = AudioMonitor()
        result = monitor.get_failed_recordings(limit=limit, offset=offset, organization=organization)
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
        
        # Dachido admins can view any organization's data via query parameter
        if g.is_dachido_admin:
            view_org = request.args.get("organization")
            # Empty string or None means all organizations
            organization = view_org if view_org and view_org.strip() else None
        else:
            organization = g.organization
        
        monitor = AudioMonitor()
        analytics = monitor.get_analytics(days=days, organization=organization)
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
        
        # Validate organization access - ensure user can only access their organization's files
        if not g.is_dachido_admin:
            # For regular users, ensure filename starts with their organization prefix
            org_prefix = f"{g.organization}/"
            if not filename.startswith(org_prefix):
                return jsonify({"error": "Access denied: File does not belong to your organization"}), 403
        
        monitor = AudioMonitor()
        detail = monitor.get_recording_detail(filename, container=container)
        
        # NOTE: For customer_admin, the "translation" field contains the original transcription text
        # We should NOT remove it - it's the actual transcription they need to see
        # The field name is confusing, but "translation" = original transcription text
        user_role = g.role
        # No need to hide anything - the "translation" field IS the transcription text
        
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
        reviewer = g.username or "admin"
        
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

@app.route("/api/audio/language-breakdown")
@login_required
def get_audio_language_breakdown():
    """Get language breakdown for customer_admin - optimized to use metadata only"""
    if not AUDIO_MONITOR_ENABLED:
        return jsonify({"error": "Audio monitoring not enabled"}), 503
    try:
        # Dachido admins can view any organization's data via query parameter
        if g.is_dachido_admin:
            view_org = request.args.get("organization")
            # Empty string or None means all organizations
            organization = view_org if view_org and view_org.strip() else None
        else:
            organization = g.organization
        
        monitor = AudioMonitor()
        
        # Use optimized method - get metadata only, no transcription downloads
        # Fetch in batches to avoid memory issues
        language_counts = {}
        language_details = {}
        total_recordings = 0
        batch_size = 500
        offset = 0
        
        while True:
            # Get batch without transcription data (much faster)
            processed_result = monitor.get_processed_recordings(
                limit=batch_size, 
                offset=offset,
                include_transcription=False,  # Don't download transcription JSON
                organization=organization
            )
            recordings = processed_result.get("recordings", [])
            
            if not recordings:
                break
            
            # Process batch
            for rec in recordings:
                lang = rec.get("source_language") or rec.get("detected_language") or rec.get("language_code") or "Unknown"
                
                if lang not in language_counts:
                    language_counts[lang] = 0
                    language_details[lang] = {
                        "count": 0,
                        "total_duration": 0,
                        "avg_processing_time": 0,
                        "processing_times": []
                    }
                
                language_counts[lang] += 1
                language_details[lang]["count"] += 1
                total_recordings += 1
                
                if rec.get("audio_duration"):
                    language_details[lang]["total_duration"] += rec.get("audio_duration", 0)
                
                if rec.get("processing_time"):
                    language_details[lang]["processing_times"].append(rec.get("processing_time", 0))
            
            # Check if we got all records
            if len(recordings) < batch_size:
                break
            
            offset += batch_size
        
        # Calculate averages
        for lang, details in language_details.items():
            if details["count"] > 0:
                details["avg_duration"] = round(details["total_duration"] / details["count"], 2)
            if details["processing_times"]:
                details["avg_processing_time"] = round(
                    sum(details["processing_times"]) / len(details["processing_times"]), 2
                )
            del details["processing_times"]  # Remove temporary list
        
        return jsonify({
            "languages": language_counts,
            "language_details": language_details,
            "total_recordings": total_recordings
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audio/sync-cache", methods=["POST"])
@login_required
def sync_audio_cache():
    """Manually trigger cache sync (admin only)"""
    if not g.is_dachido_admin:
        return jsonify({"error": "Unauthorized"}), 403
    
    if not AUDIO_MONITOR_ENABLED:
        return jsonify({"error": "Audio monitoring not enabled"}), 503
    
    try:
        from audio_cache import sync_recordings_to_cache, init_cache_tables
        
        init_cache_tables()
        organization = request.json.get("organization") if request.json else None
        force = request.json.get("force", False) if request.json else False
        
        result = sync_recordings_to_cache(organization=organization, force=force)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audio/debug-transcription/<path:filename>")
@login_required
def debug_transcription(filename):
    """Debug endpoint to check transcription file availability"""
    if not AUDIO_MONITOR_ENABLED:
        return jsonify({"error": "Audio monitoring not enabled"}), 503
    
    try:
        monitor = AudioMonitor()
        
        # Validate organization access
        if not g.is_dachido_admin:
            org_prefix = f"{g.organization}/"
            if not filename.startswith(org_prefix):
                return jsonify({"error": "Access denied"}), 403
        
        # Try to get transcription
        transcription_data = monitor._get_transcription(filename)
        
        # List container to see what files exist
        from audio_monitor import Config as AudioConfig
        container = monitor.blob_client.get_container_client(AudioConfig.TRANSCRIPTIONS_CONTAINER)
        base_name = filename.rsplit('.', 1)[0]
        search_base = base_name.split('/')[-1] if '/' in base_name else base_name
        
        all_json_files = []
        matching_files = []
        for blob in container.list_blobs():
            if blob.name.endswith('.json'):
                all_json_files.append(blob.name)
                if search_base in blob.name:
                    matching_files.append(blob.name)
        
        return jsonify({
            "filename": filename,
            "transcription_found": transcription_data is not None,
            "transcription_data": transcription_data if transcription_data else None,
            "expected_names": [
                base_name + '_transcription.json',
                base_name.split('/')[-1] + '_transcription.json' if '/' in base_name else None,
                base_name + '.json',
                base_name.split('/')[-1] + '.json' if '/' in base_name else None,
            ],
            "matching_files": matching_files[:10],  # First 10 matches
            "total_json_files_in_container": len(all_json_files),
            "sample_json_files": all_json_files[:10]  # First 10 files
        })
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

################################################

# Initialize audio cache tables on startup
try:
    from audio_cache import init_cache_tables
    init_cache_tables()
except Exception as e:
    print(f"⚠️  Could not initialize audio cache: {e}")

# Initialize default organizations and users on app startup
# This runs when the module is imported, ensuring data directories exist
try:
    # Create Dachido organization
    auth.add_organization("dachido", display_name="Dachido")
    
    # Create a sample organization (Coromandel)
    auth.add_organization("coromandel", display_name="Coromandel")
    
    # Initialize default users if they don't exist
    existing_users = auth.load_users()
    
    # Create Dachido admin user
    if "dachido:admin" not in existing_users:
        auth.add_user("dachido", "admin", "adminpass", role="dachido_admin")
    
    # Create sample organization admin
    if "coromandel:admin" not in existing_users:
        auth.add_user("coromandel", "admin", "adminpass", role="admin")
    
    # Create sample organization customer
    if "coromandel:customer" not in existing_users:
        auth.add_user("coromandel", "customer", "customer123", role="customer_admin")
except Exception as e:
    # Log error but don't crash the app
    print(f"⚠️  Warning: Could not initialize default users/organizations: {e}")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
