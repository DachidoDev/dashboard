# Quick Test Guide: Customer Admin Dashboard

## 🚀 Quick Start

```bash
# Start the server
python app.py

# Open browser
http://127.0.0.1:5000
```

## 🔐 Login Credentials

**Customer Admin:**
- Username: `customer`
- Password: `customer123`

**Admin (for comparison):**
- Username: `admin`
- Password: `adminpass`

---

## ✅ Quick Test Steps

### 1. Login Test
- [ ] Login as `customer` / `customer123`
- [ ] Verify "CUSTOMER" badge in header
- [ ] Verify username displayed

### 2. Audio Monitor - Basic Access
- [ ] Click "AUDIO MONITOR" in navigation
- [ ] Verify 4 KPI cards show counts (Pending, Processed, Failed, Total)
- [ ] Verify 5 tabs visible: Processed, Pending, Failed, Language Breakdown, Analytics

### 3. Audio Monitor - Processed Recordings
- [ ] Click "Processed" tab
- [ ] Verify recordings list loads
- [ ] Click "Listen" button on any recording
- [ ] **VERIFY:** Audio player opens
- [ ] **VERIFY:** Original transcription visible
- [ ] **VERIFY:** Translation section is HIDDEN or shows "not available"

### 4. Audio Monitor - Language Breakdown
- [ ] Click "Language Breakdown" tab
- [ ] Verify bar chart displays
- [ ] Verify statistics table shows languages with counts

### 5. Audio Monitor - Pending Recordings
- [ ] Click "Pending" tab
- [ ] Verify pending recordings list loads

### 6. Admin Module Restrictions
- [ ] Click "ADMIN" module
- [ ] **VERIFY:** Active Users KPI visible
- [ ] **VERIFY:** Date Coverage KPI visible
- [ ] **VERIFY:** Total Records KPI NOT visible
- [ ] **VERIFY:** Data Completeness KPI NOT visible
- [ ] **VERIFY:** Database Statistics section NOT visible

---

## ❌ What Customer Admin CANNOT Do

1. ❌ View translations (English translations hidden)
2. ❌ Rate quality (Good/Bad buttons not visible)
3. ❌ Retry failed recordings
4. ❌ See technical metrics in ADMIN module

---

## ✅ What Customer Admin CAN Do

1. ✅ View all main modules (HOME, MARKETING, OPERATIONS, ENGAGEMENT, ADMIN)
2. ✅ Access AUDIO MONITOR module
3. ✅ View processed recordings with metadata
4. ✅ Listen to audio clips
5. ✅ View original transcriptions
6. ✅ View language breakdown
7. ✅ View pending recordings
8. ✅ View analytics

---

## 🔍 Browser Console Check

Open browser console (F12) and verify:
- No JavaScript errors
- API calls return 200 status
- No "Translation" data in API responses for customer_admin

---

## 🐛 Common Issues

**Issue:** Can't see AUDIO MONITOR
- **Fix:** Logout and login again as `customer`

**Issue:** Translations visible
- **Fix:** Clear cookies, logout, login again

**Issue:** Language Breakdown empty
- **Fix:** Check if processed recordings exist in Azure Storage

---

**Test Time:** ~5 minutes for basic verification

