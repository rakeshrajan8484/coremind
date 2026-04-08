from typing import Dict, Any, List
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from coremind.tools.schemas import PlanStep

class WebResearcherTool:
    name = "web_researcher"
    description = "Performs targeted web searches and returns structured data."
    args_schema = {
        "query": {
            "type": "string",
            "description": "The search query to perform.",
            "required": True,
        },
        "objective_id": {
            "type": "string",
            "description": "Optional ID to track the objective this search belongs to.",
            "required": False,
        },
    }

    def __init__(self):
        self.ddgs = DDGS()
        self._search_counts = {} # Simple in-memory rate limiting by objective_id

    def _check_rate_limit(self, objective_id: str) -> bool:
        if not objective_id:
            return True # No limit if no ID provided (or handle differently)
        
        count = self._search_counts.get(objective_id, 0)
        if count >= 3:
            return False
        
        self._search_counts[objective_id] = count + 1
        return True

    def _scrape_content(self, url: str) -> str:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            
            # Break into lines and remove leading and trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text[:5000] # Limit content length
            
        except Exception as e:
            return f"Error scraping {url}: {str(e)}"

    def run(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
        query = args.get("query")
        objective_id = args.get("objective_id")

        if objective_id and not self._check_rate_limit(objective_id):
             return [{"error": "Rate limit exceeded for this objective."}]

        results = []
        try:
            # efficient search - max 5 results
            ddg_results = list(self.ddgs.text(query, max_results=5, backend="html"))
            
            for r in ddg_results:
                url = r.get("href")
                title = r.get("title")
                snippet = r.get("body")
                
                content = self._scrape_content(url)
                
                results.append({
                    "url": url,
                    "title": title,
                    "snippet": snippet,
                    "content": content,
                    "source": "web_search"
                })
                
        except Exception as e:
            return [{"error": f"Search failed: {str(e)}"}]

        return results
