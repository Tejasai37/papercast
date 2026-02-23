
import json
import os
import shutil
from pathlib import Path

CACHE_FILE = "backend/local_cache.json"
AUDIO_DIR = "backend/static/audio_cache"

class MockAWSService:
    def __init__(self):
        # Ensure audio cache directory exists
        os.makedirs(AUDIO_DIR, exist_ok=True)
        
        # Load or initialize database cache
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                self.db = json.load(f)
        else:
            self.db = {}

    def _save_db(self):
        with open(CACHE_FILE, "w") as f:
            json.dump(self.db, f, indent=4)

    # --- S3 Mock (File Storage) ---
    def upload_audio(self, file_content: bytes, file_name: str) -> str:
        """Simulates S3 Upload by saving to local static folder"""
        file_path = os.path.join(AUDIO_DIR, file_name)
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Return web-accessible URL
        return f"/static/audio_cache/{file_name}"

    def get_audio_url(self, file_name: str) -> str:
        file_path = os.path.join(AUDIO_DIR, file_name)
        if os.path.exists(file_path):
            return f"/static/audio_cache/{file_name}"
        return None

    # --- DynamoDB Mock (Metadata Cache) ---
    def get_article_metadata(self, article_id: str):
        return self.db.get(article_id)

    def save_article_metadata(self, article_id: str, data: dict):
        self.db[article_id] = data
        self._save_db()

# Singleton Instance
mock_aws = MockAWSService()
