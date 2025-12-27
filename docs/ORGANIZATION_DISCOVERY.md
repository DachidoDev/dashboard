# Organization Discovery from Containers

## Overview

The system now **dynamically discovers organizations** by scanning Azure Blob Storage containers. Only organizations that have actual data in the containers will appear in the organization selector for Dachido admins.

## How It Works

### 1. Container Scanning

The `AudioMonitor.get_organizations_from_containers()` method scans all relevant containers:

- `recordings` (pending recordings)
- `processed-recordings` (processed recordings)
- `failedrecordings` (failed recordings)

### 2. Organization Extraction

For each blob in these containers, the system:
1. Extracts the organization name from the blob path prefix
2. Format: `{organization}/{filename}.mp3`
3. Example: `coromandel/recording1.mp3` → organization = `coromandel`

### 3. Filtering

The system excludes:
- Empty organization names
- System prefixes: `dachido`, `system`, `temp`

### 4. Display Name Resolution

Once organizations are discovered:
- The system looks up display names from `organizations.json`
- If not found, it uses a title-cased version of the organization name
- Example: `coromandel` → `Coromandel` (or custom display name if set)

## Implementation Details

### New Method: `get_organizations_from_containers()`

**Location**: `audio_monitor.py`

```python
def get_organizations_from_containers(self) -> List[str]:
    """
    Discover organizations by scanning blob names in all containers
    Returns list of organization names found in containers
    """
```

**Returns**: Sorted list of organization names found in containers

### Updated Endpoints

#### 1. Dashboard Route (`/`)

**Location**: `app.py` - `index()` function

- For Dachido admins, the organization selector now only shows organizations with data in containers
- Falls back to `organizations.json` if container scanning fails

#### 2. API Endpoint (`/api/organizations`)

**Location**: `app.py` - `get_organizations()` function

- Returns only organizations found in containers
- Includes display names from `organizations.json` when available

## Benefits

1. **Data-Driven**: Only shows organizations that actually have data
2. **No Manual Configuration**: Automatically discovers new organizations when data is uploaded
3. **Accurate**: Prevents showing empty or non-existent organizations
4. **Dynamic**: Updates automatically as new organizations add data

## Example Flow

1. **Container has data**:
   - `recordings/coromandel/audio1.mp3`
   - `recordings/coromandel/audio2.mp3`
   - `processed-recordings/coromandel/audio1.mp3`

2. **System discovers**:
   - Organization: `coromandel`

3. **Dashboard shows**:
   - Organization selector includes "Coromandel" (or custom display name)

4. **If organization has no data**:
   - Organization does NOT appear in the selector
   - Even if it exists in `organizations.json`

## Fallback Behavior

If container scanning fails (e.g., Azure connection issues):
- System falls back to `organizations.json`
- Ensures the dashboard remains functional even if container access is temporarily unavailable

## Future Enhancements

Potential improvements:
- Cache organization list with TTL to reduce container scans
- Add organization metadata (data count, last activity) to the selector
- Support for nested organization structures
- Real-time updates when new organizations are detected

