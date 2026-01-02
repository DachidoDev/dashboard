"""
Storage Manager for User Data
Handles storage of users.json, organizations.json, and user_mappings.json
in Azure Blob Storage instead of local filesystem
"""

import os
import json
from typing import Dict, Optional
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError

# Storage configuration
STORAGE_CONTAINER = "dashboard-data"  # Container for dashboard JSON files
CONNECTION_STRING_ENV = "AZURE_STORAGE_CONNECTION_STRING"

# File names
USERS_FILE_NAME = "users.json"
ORGANIZATIONS_FILE_NAME = "organizations.json"
USER_MAPPINGS_FILE_NAME = "user_mappings.json"


def get_blob_client() -> Optional[BlobServiceClient]:
    """Get Azure Blob Storage client if connection string is available"""
    connection_string = os.environ.get(CONNECTION_STRING_ENV)
    if not connection_string:
        return None
    try:
        return BlobServiceClient.from_connection_string(connection_string)
    except Exception as e:
        print(f"⚠️  Error creating blob client: {e}")
        return None


def ensure_container_exists(blob_client: BlobServiceClient):
    """Ensure the storage container exists"""
    try:
        container_client = blob_client.get_container_client(STORAGE_CONTAINER)
        if not container_client.exists():
            container_client.create_container()
            print(f"✅ Created container: {STORAGE_CONTAINER}")
    except Exception as e:
        print(f"⚠️  Error ensuring container exists: {e}")


def load_from_blob(filename: str) -> Dict:
    """Load JSON file from Azure Blob Storage"""
    blob_client = get_blob_client()
    if not blob_client:
        return {}
    
    try:
        ensure_container_exists(blob_client)
        blob_client_instance = blob_client.get_blob_client(STORAGE_CONTAINER, filename)
        
        if blob_client_instance.exists():
            blob_data = blob_client_instance.download_blob()
            content = blob_data.readall().decode('utf-8')
            return json.loads(content) if content else {}
        else:
            # File doesn't exist, return empty dict and create it
            save_to_blob(filename, {})
            return {}
    except ResourceNotFoundError:
        # Blob doesn't exist, create empty file
        save_to_blob(filename, {})
        return {}
    except Exception as e:
        print(f"⚠️  Error loading {filename} from blob storage: {e}")
        return {}


def save_to_blob(filename: str, data: Dict):
    """Save JSON file to Azure Blob Storage"""
    blob_client = get_blob_client()
    if not blob_client:
        return False
    
    try:
        ensure_container_exists(blob_client)
        blob_client_instance = blob_client.get_blob_client(STORAGE_CONTAINER, filename)
        
        json_content = json.dumps(data, indent=4)
        blob_client_instance.upload_blob(json_content, overwrite=True)
        print(f"✅ Saved {filename} to blob storage")
        return True
    except Exception as e:
        print(f"⚠️  Error saving {filename} to blob storage: {e}")
        return False


def get_file_path(filename: str) -> str:
    """Get file path (local or blob storage based on configuration)"""
    # Check if blob storage is configured
    if os.environ.get(CONNECTION_STRING_ENV):
        # Use blob storage
        return f"blob://{STORAGE_CONTAINER}/{filename}"
    else:
        # Use local filesystem
        if os.environ.get("WEBSITE_INSTANCE_ID"):  # Running on Azure
            return f"/home/site/data/{filename}"
        else:
            return filename


def load_json_file(filename: str) -> Dict:
    """
    Load JSON file from blob storage (if configured) or local filesystem
    """
    # Try blob storage first if configured
    if os.environ.get(CONNECTION_STRING_ENV):
        data = load_from_blob(filename)
        if data is not None:
            return data
    
    # Fallback to local filesystem
    file_path = get_file_path(filename)
    if file_path.startswith("blob://"):
        # Already tried blob, use local fallback
        if os.environ.get("WEBSITE_INSTANCE_ID"):
            file_path = f"/home/site/data/{filename}"
        else:
            file_path = filename
    
    # Ensure directory exists
    file_dir = os.path.dirname(file_path)
    if file_dir and not file_path.startswith("blob://") and not os.path.exists(file_dir):
        os.makedirs(file_dir, exist_ok=True)
    
    # Load from local filesystem
    if not os.path.exists(file_path):
        # Create empty file
        with open(file_path, 'w') as f:
            json.dump({}, f)
        return {}
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Error loading {file_path}: {e}")
        return {}


def save_json_file(filename: str, data: Dict):
    """
    Save JSON file to blob storage (if configured) or local filesystem
    """
    # Try blob storage first if configured
    if os.environ.get(CONNECTION_STRING_ENV):
        if save_to_blob(filename, data):
            return True
    
    # Fallback to local filesystem
    file_path = get_file_path(filename)
    if file_path.startswith("blob://"):
        # Already tried blob, use local fallback
        if os.environ.get("WEBSITE_INSTANCE_ID"):
            file_path = f"/home/site/data/{filename}"
        else:
            file_path = filename
    
    # Ensure directory exists
    file_dir = os.path.dirname(file_path)
    if file_dir and not os.path.exists(file_dir):
        os.makedirs(file_dir, exist_ok=True)
    
    # Save to local filesystem
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"⚠️  Error saving {file_path}: {e}")
        return False

