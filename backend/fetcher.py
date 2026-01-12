"""
arXiv fetcher - dead simple, no bullshit.

Fetches latest papers every 5 minutes.
Downloads HTML version for DeepSeek analysis.
"""

import asyncio
import httpx
import feedparser
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List
import json
from datetime import datetime
import os
from typing import Optional

from models import Paper,Config


class ArxivFetcher:
    """
    Fetches papers from arXiv.
    Simple and effective.
    """
    
    def __init__(self, data_dir: str = "data/papers"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # arXiv RSS feed URLs for different categories
        self.categories = [
            "cs.RO",  # Robotics
            "cs.AI",  # Artificial Intelligence
            "cs.CV",  # Computer Vision
            "cs.LG",  # Machine Learning
            "cs.CL",  # Computation and Language
            "cs.NE",  # Neural and Evolutionary Computing
        ]
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

    async def fetch_latest(self, max_results: int = 100, config: Optional[Config] = None) -> List[Paper]:
        """
        Fetch arXiv papers by submission date.

        Args:
            max_results: max papers per category
            config: Config object (if None, uses Config class defaults)
        """
        # Use provided config or fall back to class defaults
        if config is not None:
            start_date = config.start_date
            end_date = config.end_date
        else:
            start_date = Config.start_date
            end_date = Config.end_date
        
        papers = []
        # Track processed papers in this fetch session to avoid duplicates across categories
        processed_ids = set()

        start_date = start_date.replace("-", "")
        end_date = (end_date or start_date).replace("-", "")

        base_url = "https://export.arxiv.org/api/query"

        async with httpx.AsyncClient(
                headers=self.headers,
                timeout=30.0,
                follow_redirects=True
        ) as client:
            for idx, category in enumerate(self.categories):
                query = (
                    f"cat:{category} AND "
                    f"submittedDate:[{start_date} TO {end_date}]"
                )

                params = {
                    "search_query": query,
                    "start": 0,
                    "max_results": max_results,
                    "sortBy": "submittedDate",
                    "sortOrder": "ascending",
                }

                print(f"  📂 Fetching {category} [{start_date} → {end_date}]")

                # Retry logic for rate limiting (HTTP 429)
                max_retries = 3
                retry_delay = 3  # Start with 3 seconds
                response = None
                
                for attempt in range(max_retries):
                    try:
                        response = await client.get(base_url, params=params)
                        
                        # Handle rate limiting (429)
                        if response.status_code == 429:
                            if attempt < max_retries - 1:
                                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff: 3s, 6s, 12s
                                print(f"  ⚠️  Rate limited (429) for {category}, waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                                await asyncio.sleep(wait_time)
                                continue
                            else:
                                print(f"  ✗ HTTP 429 for {category} after {max_retries} attempts. Skipping this category.")
                                response = None  # Mark as failed
                                break
                        
                        # Handle other non-200 status codes
                        if response.status_code != 200:
                            print(f"  ✗ HTTP {response.status_code} for {category}")
                            break
                        
                        # Success - break out of retry loop
                        break
                        
                    except httpx.RequestError as e:
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)
                            print(f"  ⚠️  Network error for {category}, retrying in {wait_time}s ({attempt + 1}/{max_retries}): {e}")
                            await asyncio.sleep(wait_time)
                        else:
                            print(f"  ✗ Network error for {category} after {max_retries} attempts: {e}")
                            response = None  # Mark as failed
                            break
                    except Exception as e:
                        print(f"  ✗ Unexpected error for {category}: {e}")
                        response = None  # Mark as failed
                        break
                
                # Check if we got a valid response
                if response is None or response.status_code != 200:
                    continue

                feed = feedparser.parse(response.text)
                print(f"     Found {len(feed.entries)} papers")

                # Add delay between categories to avoid rate limiting
                # arXiv recommends max 1 request per 3 seconds
                if idx < len(self.categories) - 1:  # Don't delay after last category
                    await asyncio.sleep(3)  # Wait 3 seconds between categories

                for entry in feed.entries:
                    arxiv_id = entry.id.split("/abs/")[-1]

                    # Skip if already exists on disk OR already processed in this session
                    if self._paper_exists(arxiv_id) or arxiv_id in processed_ids:
                        if arxiv_id in processed_ids:
                            # Silently skip - already processed in this fetch session
                            continue
                        # Already exists on disk
                        continue
                    
                    # Mark as processed to avoid duplicates across categories
                    processed_ids.add(arxiv_id)

                    html_content = await self._fetch_html(client, arxiv_id)
                    # Add small delay between HTML fetches to avoid rate limiting
                    await asyncio.sleep(1)  # Wait 1 second between HTML downloads
                    
                    preview_text = self._extract_preview(html_content, entry.summary)
                    published_date = getattr(entry, "published", "")

                    paper = Paper(
                        id=arxiv_id,
                        title=entry.title,
                        authors=self._extract_authors(entry),
                        abstract=entry.summary,
                        url=entry.link,
                        html_url=f"https://arxiv.org/html/{arxiv_id}",
                        html_content=html_content,
                        preview_text=preview_text,
                        published_date=published_date,
                    )

                    self._save_paper(paper)
                    papers.append(paper)

                    print(f"     ✓ {arxiv_id} - {paper.title[:60]}...")

        return papers

    async def _fetch_html(self, client: httpx.AsyncClient, arxiv_id: str) -> str:
        """
        Download HTML version of paper.
        Falls back to abstract if HTML not available.
        Includes retry logic for rate limiting.
        """
        html_url = f"https://arxiv.org/html/{arxiv_id}"
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = await client.get(html_url)
                
                # Handle rate limiting (429)
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # 2s, 4s, 8s
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        # Skip HTML content if rate limited after all retries
                        return ""
                
                if response.status_code == 200:
                    # Extract main content
                    soup = BeautifulSoup(response.text, 'lxml')
                    
                    # Try to find main article content
                    article = soup.find('article') or soup.find('div', {'id': 'main'})
                    if article:
                        return article.get_text(separator='\n', strip=True)
                    
                    return soup.get_text(separator='\n', strip=True)
                else:
                    # Non-200 status (but not 429, which is handled above)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        break
                        
            except httpx.RequestError as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Silently fail - will use abstract instead
                    return ""
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    # Silently fail - will use abstract instead
                    return ""
        
        # Fallback: return empty, will use abstract
        return ""
    
    def _extract_preview(self, html_content: str, abstract: str) -> str:
        """
        Extract preview text (first 2000 chars).
        Priority: abstract + beginning of paper
        """
        if html_content:
            # Combine abstract and paper start
            preview = f"{abstract}\n\n{html_content[:1500]}"
        else:
            preview = abstract
        
        return preview[:2000]
    
    def _extract_authors(self, entry) -> List[str]:
        """Extract author names from RSS entry"""
        if hasattr(entry, 'authors'):
            return [author.name for author in entry.authors]
        elif hasattr(entry, 'author'):
            return [entry.author]
        return []
    
    async def fetch_single_paper(self, arxiv_id: str) -> Paper:
        """
        Fetch a single paper by arXiv ID.
        Uses arXiv API to get metadata, then downloads HTML.
        Returns Paper object.
        Raises exception if paper not found or fetch fails.
        """
        # Check if already exists
        if self._paper_exists(arxiv_id):
            return self.load_paper(arxiv_id)
        
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0, follow_redirects=True) as client:
            # Use arXiv API to get paper metadata
            api_url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
            
            try:
                response = await client.get(api_url)
                if response.status_code != 200:
                    raise Exception(f"arXiv API returned {response.status_code}")
                
                # Parse Atom feed
                feed = feedparser.parse(response.text)
                
                if not feed.entries or len(feed.entries) == 0:
                    raise Exception(f"Paper {arxiv_id} not found on arXiv")
                
                entry = feed.entries[0]
                
                # Download HTML version
                html_content = await self._fetch_html(client, arxiv_id)
                
                # Extract preview text
                preview_text = self._extract_preview(html_content, entry.summary)
                
                # Extract published date
                published_date = getattr(entry, 'published', '')
                
                # Create Paper object
                paper = Paper(
                    id=arxiv_id,
                    title=entry.title,
                    authors=self._extract_authors(entry),
                    abstract=entry.summary,
                    url=entry.link,
                    html_url=f"https://arxiv.org/html/{arxiv_id}",
                    html_content=html_content,
                    preview_text=preview_text,
                    published_date=published_date,
                )
                
                # Save immediately
                self.save_paper(paper)
                print(f"✓ Fetched single paper: {arxiv_id} - {paper.title[:60]}...")
                
                return paper
            
            except Exception as e:
                print(f"✗ Error fetching paper {arxiv_id}: {e}")
                raise
    
    def _paper_exists(self, arxiv_id: str) -> bool:
        """Check if paper already exists"""
        return (self.data_dir / f"{arxiv_id}.json").exists()
    
    def save_paper(self, paper: Paper):
        """Save paper to JSON file"""
        file_path = self.data_dir / f"{paper.id}.json"
        with open(file_path, 'w') as f:
            json.dump(paper.to_dict(), f, indent=2, ensure_ascii=False)
    
    # Keep _save_paper for backward compatibility
    def _save_paper(self, paper: Paper):
        """Deprecated: use save_paper instead"""
        self.save_paper(paper)
    
    def load_paper(self, arxiv_id: str) -> Paper:
        """Load paper from JSON file"""
        file_path = self.data_dir / f"{arxiv_id}.json"
        with open(file_path) as f:
            return Paper.from_dict(json.load(f))
    
    def list_papers(self, skip: int = 0, limit: int = 20) -> List[Paper]:
        """
        List papers with pagination.
        If limit is None or <= 0, load all papers.
        """
        paper_files = sorted(
            self.data_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        papers = []
        
        # If limit is None or <= 0, load all papers
        if limit is None or limit <= 0:
            file_range = paper_files[skip:]
        else:
            file_range = paper_files[skip:skip + limit]
        
        for file_path in file_range:
            try:
                with open(file_path) as f:
                    papers.append(Paper.from_dict(json.load(f)))
            except Exception as e:
                print(f"Warning: Failed to load paper {file_path.name}: {e}")
                continue
        
        return papers

async def run_fetcher_loop(start_date, end_date, interval: int = 300):
    fetcher = ArxivFetcher()

    print("🚀 Fetching arXiv papers by date...")

    papers = await fetcher.fetch_latest()

    print(f"✓ Fetched {len(papers)} papers")



if __name__ == "__main__":
    # Test the fetcher
    asyncio.run(run_fetcher_loop())

