
import os
import requests
from typing import List, Dict

class NewsService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("NEWS_API_KEY")
        self.base_url = "https://newsapi.org/v2"

    def get_top_headlines(self, category: str = "general", country: str = "us") -> List[Dict]:
        """Fetches top headlines from NewsAPI.org"""
        if not self.api_key:
            print("Warning: No News API Key provided. Returning empty list.")
            return []

        url = f"{self.base_url}/top-headlines"
        params = {
            "apiKey": self.api_key,
            "category": category,
            "country": country,
            "pageSize": 10
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Format the data to match our application's expected structure
            articles = []
            for i, item in enumerate(data.get("articles", [])):
                articles.append({
                    "id": f"news-{i}",
                    "title": item.get("title"),
                    "source": item.get("source", {}).get("name", "Unknown"),
                    "category": category.capitalize(),
                    "time": item.get("publishedAt", "Recently"),
                    "content": item.get("description") or item.get("content") or "No content available.",
                    "url": item.get("url")
                })
            return articles
        except Exception as e:
            print(f"Error fetching news: {e}")
            return []

# Singleton instance
news_service = NewsService()
