
import os
import requests
from typing import List, Dict

class NewsService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("NEWS_API_KEY")
        self.base_url = "https://newsapi.org/v2"
        self.cache = {} # Temporary cache for the current session

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
                article_id = f"news-{i}"
                article = {
                    "id": article_id,
                    "title": item.get("title"),
                    "source": item.get("source", {}).get("name", "Unknown"),
                    "category": category.capitalize(),
                    "time": item.get("publishedAt", "Recently"),
                    "content": item.get("description") or item.get("content") or "No content available.",
                    "url": item.get("url")
                }
                articles.append(article)
                self.cache[article_id] = article # Store in cache
            return articles
        except Exception as e:
            print(f"Error fetching news: {e}")
            return []

    def search_news(self, query: str, language: str = "en", sort_by: str = "relevancy") -> List[Dict]:
        """Searches for articles containing specific keywords using '/everything' endpoint"""
        if not self.api_key or not query:
            return []

        url = f"{self.base_url}/everything"
        params = {
            "apiKey": self.api_key,
            "q": query,
            "language": language,
            "sortBy": sort_by,
            "pageSize": 10
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for i, item in enumerate(data.get("articles", [])):
                article_id = f"search-{i}"
                article = {
                    "id": article_id,
                    "title": item.get("title"),
                    "source": item.get("source", {}).get("name", "Unknown"),
                    "category": "Search Result",
                    "time": item.get("publishedAt", "Recently"),
                    "content": item.get("description") or item.get("content") or "No content available.",
                    "url": item.get("url")
                }
                articles.append(article)
                self.cache[article_id] = article
            return articles
        except Exception as e:
            print(f"Error searching news: {e}")
            return []

    def get_article_by_id(self, article_id: str) -> Dict:
        """Retrieves an article from the current session cache"""
        return self.cache.get(article_id)

# Singleton instance
news_service = NewsService()
