# How Organization-Based Data Filtering Works

## Current Implementation

### Audio Recordings (Azure Blob Storage) ✅ IMPLEMENTED

**Logic**: Filtering by blob name prefix in Azure Blob Storage containers

**How it works:**

1. **Blob Storage Convention**:
   - Recordings stored as: `{organization}/{filename}.mp3`
   - Example: `coromandel/recording1.mp3`, `coromandel/recording2.wav`
   - Example: `otherorg/recording1.mp3`

2. **Filtering Logic** (in `audio_monitor.py`):
   ```python
   # Organization prefix for filtering
   org_prefix = f"{organization}/" if organization and organization != "dachido" else None
   
   # Filter blobs by prefix
   for blob in container.list_blobs():
       if org_prefix and not blob.name.startswith(org_prefix):
           continue  # Skip this blob
   ```

3. **Dachido Admin Behavior**:
   - **No organization selected**: `organization = None` → Sees ALL recordings from all organizations
   - **Organization selected**: `organization = "coromandel"` → Sees only `coromandel/` prefixed recordings
   - Logic: `if organization != "dachido"` → Apply prefix filter, else show all

4. **Regular Organization Users**:
   - Always filtered by their organization: `organization = g.organization`
   - Example: Coromandel user always sees only `coromandel/` recordings

**Containers Filtered**:
- `recordings` (pending)
- `processed-recordings` (processed)
- `failedrecordings` (failed)

---

### SQLite Database Data ❌ NOT IMPLEMENTED YET

**Current Status**: All organizations see the SAME data from SQLite database

**Why**: SQLite database doesn't have organization columns yet. All fact tables are shared.

**What's NOT Filtered**:
- `fact_conversations` - All organizations see same conversations
- `fact_conversation_entities` - All see same entities
- `fact_conversation_semantics` - All see same sentiment data
- All dashboard modules (HOME, MARKETING, OPERATIONS, ENGAGEMENT) - Show same data

**Future Implementation** (PostgreSQL):
- Each organization will have its own database: `{organization}_db`
- OR add `organization` column to all fact tables
- Then filter queries: `WHERE organization = ?`

---

## Data Flow for Dachido Admin

### When Dachido Admin Selects Organization:

1. **Frontend (dashboard.html)**:
   ```javascript
   // User selects "Coromandel" from dropdown
   organizationSelector.value = "coromandel"
   
   // All API calls include organization parameter
   fetch('/api/audio/pending?organization=coromandel&limit=50&offset=0')
   ```

2. **Backend (app.py)**:
   ```python
   # Dachido admin can pass organization parameter
   if g.is_dachido_admin:
       view_org = request.args.get("organization")
       organization = view_org if view_org else None  # None = all orgs
   else:
       organization = g.organization  # Regular users always use their org
   ```

3. **Audio Monitor (audio_monitor.py)**:
   ```python
   # Filter by blob name prefix
   org_prefix = f"{organization}/" if organization and organization != "dachido" else None
   
   for blob in container.list_blobs():
       if org_prefix and not blob.name.startswith(org_prefix):
           continue  # Skip blobs not matching organization
   ```

---

## Where Data Comes From

### Audio Recordings ✅
- **Source**: Azure Blob Storage containers
- **Filtering**: By blob name prefix (`{organization}/filename`)
- **Method**: `container.list_blobs()` then filter by `blob.name.startswith(org_prefix)`
- **Status**: ✅ Working for Dachido admins

### Dashboard Analytics (SQLite) ❌
- **Source**: SQLite database (`fieldforce.db`)
- **Filtering**: NOT implemented yet
- **Method**: Direct SQL queries (no organization filter)
- **Status**: ❌ All organizations see same data

---

## Example: Dachido Admin Views Coromandel Data

### Step-by-Step Flow:

1. **Dachido admin logs in**:
   - JWT token contains: `organization: "dachido"`, `role: "dachido_admin"`

2. **Dashboard loads**:
   - Shows organization selector dropdown
   - Options: "All Organizations", "Coromandel", "OtherOrg", etc.

3. **User selects "Coromandel"**:
   - JavaScript: `organizationSelector.value = "coromandel"`
   - All API calls now include: `?organization=coromandel`

4. **API Request**:
   ```
   GET /api/audio/pending?organization=coromandel&limit=50&offset=0
   ```

5. **Backend Processing**:
   ```python
   # app.py
   if g.is_dachido_admin:
       view_org = request.args.get("organization")  # "coromandel"
       organization = view_org  # Pass to AudioMonitor
   
   # audio_monitor.py
   org_prefix = "coromandel/"  # Create prefix
   
   # Filter blobs
   for blob in container.list_blobs():
       if not blob.name.startswith("coromandel/"):
           continue  # Skip non-Coromandel blobs
   ```

6. **Result**:
   - Only returns recordings with `coromandel/` prefix
   - Example: `coromandel/recording1.mp3` ✅
   - Example: `otherorg/recording2.mp3` ❌ (filtered out)

---

## Current Limitations

### ✅ What Works:
- Audio recordings filtered by organization (blob prefix)
- Dachido admin can select organization from dropdown
- Organization selector visible only to Dachido admins
- All audio API endpoints support organization parameter

### ❌ What Doesn't Work Yet:
- SQLite database queries NOT filtered by organization
- All dashboard modules show same data for all organizations
- No organization column in fact tables
- Database data isolation not implemented

---

## Production Readiness Issues

### 🔴 Critical (Must Fix Before Production):

1. **Debug Mode Enabled**:
   ```python
   app.run(debug=True, host="0.0.0.0", port=5000)  # ❌ DEBUG MODE
   ```
   - **Fix**: Use production WSGI server (gunicorn) with `debug=False`

2. **Weak Secret Keys**:
   ```python
   SECRET_KEY = os.environ.get("SECRET_KEY", "your_super_secret_key")  # ❌ Weak default
   JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your_super_secret_jwt_key...")  # ❌ Weak default
   ```
   - **Fix**: Require strong keys via environment variables, fail if not set

3. **No Error Logging**:
   - Only `print()` statements, no proper logging
   - **Fix**: Use Python `logging` module with proper levels

4. **SQLite for Production**:
   - SQLite not suitable for multi-tenant production
   - **Fix**: Migrate to PostgreSQL with organization-specific databases

5. **No Rate Limiting**:
   - Login endpoint vulnerable to brute force
   - **Fix**: Add rate limiting (Flask-Limiter)

6. **No Input Validation**:
   - Organization parameter not validated
   - **Fix**: Validate organization exists before filtering

### 🟡 Important (Should Fix):

7. **No Database Connection Pooling**:
   - New connection for each request
   - **Fix**: Use connection pooling

8. **No Caching**:
   - Repeated queries hit database/Blob Storage
   - **Fix**: Add Redis caching for frequently accessed data

9. **No Monitoring/Health Checks**:
   - No health check endpoint
   - **Fix**: Add `/health` endpoint

10. **No CSRF Protection**:
    - Forms vulnerable to CSRF attacks
    - **Fix**: Add Flask-WTF CSRF tokens

### 🟢 Nice to Have:

11. **No Unit Tests**
12. **No API Documentation**
13. **No Request ID Tracking**
14. **No Structured Logging**

---

## Summary

**Organization Data Filtering**:
- ✅ **Audio Recordings**: Filtered by blob name prefix in Azure containers
- ❌ **Database Data**: NOT filtered (all organizations see same SQLite data)

**Production Readiness**:
- ❌ **NOT production-ready** - Multiple critical issues need fixing
- 🔴 Debug mode, weak secrets, no logging, SQLite limitations
- 🟡 Missing rate limiting, connection pooling, caching
- 🟢 Missing tests, documentation, monitoring

**Next Steps for Production**:
1. Disable debug mode
2. Require strong secret keys
3. Add proper logging
4. Migrate to PostgreSQL
5. Add rate limiting
6. Add input validation
7. Add health checks

