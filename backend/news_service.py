
import os
import requests
import hashlib
from typing import List, Dict

class NewsService:
    def __init__(self, api_key: str = None):
        # We can still read from the same env var so you don't have to rename it
        self.api_key = api_key or os.getenv("NEWS_API_KEY") 
        self.base_url = "https://gnews.io/api/v4"
        self.cache = {} # Discovery session cache

    def _generate_id(self, title: str, prefix: str) -> str:
        """Generates a stable unique ID based on the title"""
        title_hash = hashlib.md5(title.encode('utf-8')).hexdigest()[:8]
        return f"{prefix}-{title_hash}"

    def get_top_headlines(self, category: str = "general", country: str = "us") -> List[Dict]:
        """Fetches top headlines from GNews API"""
        if not self.api_key:
            print("Warning: No GNews API Key provided. Returning empty list.")
            return []

        url = f"{self.base_url}/top-headlines"
        params = {
            "apikey": self.api_key,
            "category": category,
            "lang": "en",
            "country": country,
            "max": 10
        }

        try:
            print(f"DEBUG: Fetching headlines for category: {category} via GNews")
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for item in data.get("articles", []):
                title = item.get("title", "")
                if not title: continue
                
                article_id = self._generate_id(title, "news")
                article = {
                    "id": article_id,
                    "title": title,
                    "source": item.get("source", {}).get("name", "Unknown"),
                    "category": category.capitalize(),
                    "time": item.get("publishedAt", "Recently"),
                    "content": item.get("content") or item.get("description") or "No content available.",
                    "url": item.get("url")
                }
                articles.append(article)
                self.cache[article_id] = article 
            
            return articles
        except Exception as e:
            print(f"Error fetching news: {e}")
            return []

    def search_news(self, query: str, language: str = "en", sort_by: str = "relevancy") -> List[Dict]:
        """Searches for articles containing specific keywords using '/search' endpoint"""
        if not self.api_key or not query:
            return []

        url = f"{self.base_url}/search"
        params = {
            "apikey": self.api_key,
            "q": query,
            "lang": language,
            "max": 10
        }

        try:
            print(f"DEBUG: Searching news for: {query} via GNews")
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for item in data.get("articles", []):
                title = item.get("title", "")
                if not title: continue
                
                article_id = self._generate_id(title, "search")
                article = {
                    "id": article_id,
                    "title": title,
                    "source": item.get("source", {}).get("name", "Unknown"),
                    "category": "Search Result",
                    "time": item.get("publishedAt", "Recently"),
                    "content": item.get("content") or item.get("description") or "No content available.",
                    "url": item.get("url")
                }
                articles.append(article)
                self.cache[article_id] = article
            
            return articles
        except Exception as e:
            print(f"Error searching news: {e}")
            return []

    def get_article_by_id(self, article_id: str) -> Dict:
        """Retrieves an article from the current discovery cache"""
        return self.cache.get(article_id)

    def extract_article(self, url: str) -> Dict:
        """Extracts content from a raw URL using BeautifulSoup"""
        from bs4 import BeautifulSoup
        try:
            print(f"DEBUG: Extracting content from: {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Remove scripts and styles
            for script in soup(["script", "style"]):
                script.extract()

            # Extract title
            title = soup.find('h1').get_text().strip() if soup.find('h1') else "Custom Article"
            
            # Extract content (grab all paragraphs)
            paragraphs = soup.find_all('p')
            content = " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20])
            
            if len(content) < 100:
                content = "Could not extract sufficient text from this page."

            article_id = self._generate_id(title, "custom")
            article = {
                "id": article_id,
                "title": title,
                "source": "Custom Link",
                "category": "Custom Broadcast",
                "time": "Just now",
                "content": content,
                "url": url
            }
            
            # Save to cache so generate_audio can find it
            self.cache[article_id] = article
            return article
        except Exception as e:
            print(f"Extraction Error: {e}")
            return None

# Singleton instance
news_service = NewsService()
