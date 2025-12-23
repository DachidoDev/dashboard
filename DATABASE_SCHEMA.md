# SQLite Database Schema - fieldforce.db

## Overview

The SQLite database (`fieldforce.db`) stores **agricultural fieldforce conversation data** and analytics for market intelligence, competitive analysis, and operational insights.

**Note**: Currently, the database is **NOT organization-specific**. All organizations share the same database. When migrating to PostgreSQL, each organization will have its own database.

---

## Database Structure

The database follows a **star schema** pattern with:
- **Fact Tables**: Transaction/event data (conversations, metrics)
- **Dimension Tables**: Master/reference data (brands, crops, users, companies)
- **Mart Tables**: Pre-aggregated analytics data

---

## 📊 Fact Tables (Transaction Data)

### 1. `fact_conversations`
**Purpose**: Core conversation records from fieldforce interactions

**Typical Columns**:
- `conversation_id` (Primary Key)
- `user_id` (Foreign Key → dim_user)
- `created_at` (Timestamp)
- `user_text` (Conversation content)
- Other conversation metadata

**Usage**: 
- Tracks all conversations between fieldforce and customers
- Used for volume metrics, activity counts, time-series analysis
- Base table for most analytics queries

**Example Queries**:
```sql
-- Get conversation count by date
SELECT DATE(created_at) as date, COUNT(*) as volume
FROM fact_conversations
GROUP BY DATE(created_at)
```

---

### 2. `fact_conversation_entities`
**Purpose**: Extracted entities (brands, crops, pests) mentioned in conversations

**Typical Columns**:
- `conversation_id` (Foreign Key)
- `entity_code` (Code for the entity)
- `entity_type` ('brand', 'crop', 'pest')
- Other entity metadata

**Usage**:
- Tracks which brands, crops, and pests are mentioned in conversations
- Used for market share analysis, brand-crop associations
- Entity extraction from conversation text

**Example Queries**:
```sql
-- Get brand mentions
SELECT entity_code, COUNT(*) as mentions
FROM fact_conversation_entities
WHERE entity_type = 'brand'
GROUP BY entity_code
```

---

### 3. `fact_conversation_semantics`
**Purpose**: Sentiment, intent, urgency, and topic analysis of conversations

**Typical Columns**:
- `conversation_id` (Foreign Key)
- `overall_sentiment` ('positive', 'neutral', 'negative')
- `intent` (e.g., 'purchase', 'request_info', 'seek_advice')
- `urgency` ('low', 'medium', 'high', 'critical')
- `primary_topic` (e.g., 'pest', 'disease', 'weed', 'crop_damage')
- Other semantic analysis fields

**Usage**:
- Sentiment analysis for market health scores
- Intent detection for demand signals
- Urgency classification for operations alerts
- Topic classification for problem trends

**Example Queries**:
```sql
-- Get sentiment distribution
SELECT overall_sentiment, COUNT(*) as count
FROM fact_conversation_semantics
GROUP BY overall_sentiment
```

---

### 4. `fact_conversation_metrics`
**Purpose**: Alert flags and calculated metrics per conversation

**Typical Columns**:
- `conversation_id` (Foreign Key)
- `alert_flag` (0 or 1 - indicates urgent issues)
- Other calculated metrics

**Usage**:
- Alert detection for urgent issues
- KPI calculations
- Quality metrics

**Example Queries**:
```sql
-- Get alert count
SELECT COUNT(*) as alert_count
FROM fact_conversation_metrics
WHERE alert_flag = 1
```

---

## 📚 Dimension Tables (Master Data)

### 5. `dim_brands`
**Purpose**: Brand catalog - all agricultural brands/products

**Typical Columns**:
- `brand_code` (Primary Key)
- `brand_name`
- `company_code` (Foreign Key → dim_companies)
- Other brand metadata

**Usage**:
- Brand lookup and reference
- Company-brand relationships
- Brand filtering and analysis

**Example Queries**:
```sql
-- Get brands by company
SELECT brand_name, company_code
FROM dim_brands
WHERE company_code = 7007  -- Coromandel
```

---

### 6. `dim_companies`
**Purpose**: Company information (Coromandel and competitors)

**Typical Columns**:
- `company_code` (Primary Key)
- `company_name`
- Other company metadata

**Companies Tracked**:
- **Coromandel** (Code: 7007) - Primary company
- **Bayer Crop Science** (Code: 7002) - Competitor
- **UPL Limited** (Code: 7025) - Competitor
- **Syngenta India Ltd** (Code: 7024) - Competitor

**Usage**:
- Competitive analysis
- Market share calculations
- Company filtering

**Example Queries**:
```sql
-- Get all tracked companies
SELECT company_code, company_name
FROM dim_companies
WHERE company_code IN (7007, 7002, 7025, 7024)
```

---

### 7. `dim_crops`
**Purpose**: Crop catalog with crop types

**Typical Columns**:
- `crop_code` (Primary Key)
- `crop_name`
- `crop_type` (e.g., 'Cereals', 'Pulses', 'Vegetables')
- Other crop metadata

**Usage**:
- Crop filtering and analysis
- Crop-pest associations
- Crop type grouping

**Example Queries**:
```sql
-- Get crops by type
SELECT crop_name, crop_type
FROM dim_crops
WHERE crop_type = 'Cereals'
```

---

### 8. `dim_pests`
**Purpose**: Pest catalog

**Typical Columns**:
- `pest_code` (Primary Key)
- `pest_name`
- Other pest metadata

**Usage**:
- Pest identification
- Crop-pest problem analysis
- Pest trend tracking

---

### 9. `dim_user`
**Purpose**: Field force user information

**Typical Columns**:
- `user_id` (Primary Key)
- `full_name`
- `district` (Geographic region)
- Other user metadata

**Usage**:
- User activity tracking
- Regional analysis
- Agent performance metrics
- Geographic insights

**Example Queries**:
```sql
-- Get conversations by region
SELECT du.district, COUNT(*) as count
FROM fact_conversations fc
JOIN dim_user du ON fc.user_id = du.user_id
GROUP BY du.district
```

---

### 10. `dim_dashboard_users`
**Purpose**: Dashboard login users (separate from fieldforce users)

**Typical Columns**:
- User credentials and roles
- Dashboard access information

**Usage**:
- Dashboard authentication
- User management in ADMIN module

**Note**: This is separate from `dim_user` (fieldforce users) and `users.json` (JWT auth users)

---

## 📈 Mart Tables (Pre-aggregated Analytics)

### 11. `mart_brand_crop_matrix`
**Purpose**: Pre-calculated brand-crop co-mentions for performance

**Typical Columns**:
- `brand_code`
- `crop_code` / `crop_name`
- `co_mentions` (Count of times brand and crop mentioned together)
- Other aggregated metrics

**Usage**:
- Brand-crop association analysis
- Sunburst diagram data
- Fast lookups for brand recommendations

**Example Queries**:
```sql
-- Get top brand-crop associations
SELECT brand_name, crop_name, co_mentions
FROM mart_brand_crop_matrix
ORDER BY co_mentions DESC
LIMIT 10
```

---

### 12. `mart_crop_pest_matrix`
**Purpose**: Pre-calculated crop-pest co-mentions

**Typical Columns**:
- `crop_name`
- `pest_name`
- `co_mentions` (Count of times crop and pest mentioned together)

**Usage**:
- Crop-pest heatmap
- Problem identification
- Solution recommendations

---

### 13. `mart_crop_pest_brand_flow`
**Purpose**: Complete solution flow analysis (crop → pest → brand)

**Typical Columns**:
- `crop_name`
- `pest_name`
- `brand_name`
- `flow_count` (Count of complete solution flows)

**Usage**:
- Sankey diagram data
- Solution effectiveness analysis
- End-to-end problem-solution tracking

---

## 🔄 Data Flow

```
Fieldforce Conversations
    ↓
fact_conversations (raw conversation data)
    ↓
Entity Extraction → fact_conversation_entities (brands, crops, pests)
Sentiment Analysis → fact_conversation_semantics (sentiment, intent, topics)
Metrics Calculation → fact_conversation_metrics (alerts, KPIs)
    ↓
Pre-aggregation → mart_* tables (for fast analytics)
    ↓
Dashboard Visualization
```

---

## 📊 What Data is Analyzed

### 1. **Conversation Analytics**
- Volume trends over time
- Conversation distribution by topic
- Activity counts by region/user

### 2. **Market Intelligence**
- Brand health and sentiment
- Market share trends
- Competitive positioning
- Brand-crop associations

### 3. **Operations Insights**
- Urgent issues and alerts
- Demand signals
- Crop-pest problems
- Solution effectiveness

### 4. **Engagement Metrics**
- Agent performance
- Regional quality metrics
- Training needs
- Team urgency distribution

---

## 🚨 Current Limitations

### Organization Isolation
- **Current**: All organizations share the same database
- **Future**: When migrating to PostgreSQL, each organization will have:
  - Its own database: `{organization}_db`
  - Or schema-based isolation: `{organization}_schema`
  - Organization column added to fact tables

### Data Filtering
- Currently, data is **NOT filtered by organization** in SQLite
- All organizations see the same data
- Organization filtering will be added during PostgreSQL migration

---

## 🔮 Future PostgreSQL Migration

### Proposed Structure

**Option 1: Separate Databases**
```
coromandel_db/
  ├── fact_conversations
  ├── fact_conversation_entities
  └── ...

dachido_db/
  ├── fact_conversations
  └── ...

other_org_db/
  └── ...
```

**Option 2: Schema-Based**
```
fieldforce_db/
  ├── coromandel_schema/
  │   ├── fact_conversations
  │   └── ...
  ├── dachido_schema/
  │   └── ...
  └── shared_schema/
      └── dim_* (shared dimensions)
```

**Option 3: Organization Column**
```
fieldforce_db/
  ├── fact_conversations (with organization column)
  ├── fact_conversation_entities (with organization column)
  └── ...
```

---

## 📝 Sample Queries by Module

### HOME Module
```sql
-- Alert Count KPI
SELECT COUNT(*) as alert_count
FROM fact_conversation_metrics
WHERE alert_flag = 1

-- Market Health Score
SELECT AVG(CASE
    WHEN overall_sentiment = 'positive' THEN 100
    WHEN overall_sentiment = 'neutral' THEN 50
    WHEN overall_sentiment = 'negative' THEN 0
END) as health_score
FROM fact_conversation_semantics
```

### MARKETING Module
```sql
-- Brand Health Trend
SELECT DATE(created_at) as date, COUNT(*) as volume
FROM fact_conversations fc
JOIN fact_conversation_entities fce ON fc.conversation_id = fce.conversation_id
JOIN dim_brands db ON fce.entity_code = db.brand_code
WHERE db.company_code = 7007  -- Coromandel
GROUP BY DATE(created_at)

-- Market Share
SELECT dc.company_name, COUNT(DISTINCT fce.conversation_id) as mentions
FROM fact_conversation_entities fce
JOIN dim_brands db ON fce.entity_code = db.brand_code
JOIN dim_companies dc ON db.company_code = dc.company_code
WHERE fce.entity_type = 'brand'
GROUP BY dc.company_name
```

### OPERATIONS Module
```sql
-- Urgent Issues
SELECT conversation_id, created_at, user_text, urgency, primary_topic
FROM fact_conversations fc
JOIN fact_conversation_semantics fcs ON fc.conversation_id = fcs.conversation_id
WHERE fcs.urgency IN ('high', 'critical')
ORDER BY created_at DESC

-- Crop-Pest Heatmap
SELECT crop_name, pest_name, co_mentions
FROM mart_crop_pest_matrix
ORDER BY co_mentions DESC
```

### ENGAGEMENT Module
```sql
-- Conversations by Region
SELECT du.district as region, COUNT(*) as count
FROM fact_conversations fc
JOIN dim_user du ON fc.user_id = du.user_id
GROUP BY du.district

-- Agent Scorecard
SELECT du.full_name, COUNT(*) as total_convs,
       AVG(CASE
           WHEN fcs.overall_sentiment = 'positive' THEN 100
           WHEN fcs.overall_sentiment = 'neutral' THEN 50
           WHEN fcs.overall_sentiment = 'negative' THEN 0
       END) as avg_sentiment
FROM fact_conversations fc
JOIN dim_user du ON fc.user_id = du.user_id
JOIN fact_conversation_semantics fcs ON fc.conversation_id = fcs.conversation_id
GROUP BY du.full_name
```

---

## 🔍 Database Inspection

### Check Database Size
```bash
ls -lh fieldforce.db
```

### View Tables
```sql
.tables
```

### Count Records
```sql
SELECT 
    'fact_conversations' as table_name, COUNT(*) as count FROM fact_conversations
UNION ALL
SELECT 'fact_conversation_entities', COUNT(*) FROM fact_conversation_entities
UNION ALL
SELECT 'fact_conversation_semantics', COUNT(*) FROM fact_conversation_semantics
UNION ALL
SELECT 'dim_brands', COUNT(*) FROM dim_brands
UNION ALL
SELECT 'dim_crops', COUNT(*) FROM dim_crops;
```

### Date Range
```sql
SELECT 
    MIN(created_at) as earliest,
    MAX(created_at) as latest,
    COUNT(*) as total_conversations
FROM fact_conversations;
```

---

## 📌 Key Points

1. **Current State**: Single SQLite database shared by all organizations
2. **Data Type**: Agricultural fieldforce conversation analytics
3. **Schema Pattern**: Star schema (facts + dimensions + marts)
4. **Future**: PostgreSQL with organization-specific databases
5. **Organization Isolation**: Not yet implemented in SQLite (will be in PostgreSQL)

---

**Last Updated**: Based on current codebase analysis

