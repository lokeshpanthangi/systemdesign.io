"""
YouTube Video Fetcher Tool
Fetches relevant YouTube videos for learning based on problem topic and missing concepts.
Uses YouTube Data API v3 ONLY - requires YOUTUBE_API_KEY environment variable.
"""
from typing import List, Dict, Any
import os

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("ERROR: requests package not installed. Install with: pip install requests")


async def fetch_youtube_videos(
    problem_data: Dict[str, Any],
    missing_concepts: List[str]
) -> List[Dict[str, Any]]:
    """
    Fetch YouTube videos using YouTube Data API v3.
    Requires YOUTUBE_API_KEY environment variable.
    
    Args:
        problem_data: Problem info with title and categories
        missing_concepts: List of missing concepts from scoring
    
    Returns:
        List of video dicts with {title, url, channel, reason}
        Returns empty list if API key missing or API call fails
    """
    # Check if requests library is available
    if not REQUESTS_AVAILABLE:
        print("ERROR: Cannot fetch YouTube videos - requests library not installed")
        return []
    
    # Check for API key
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print("WARNING: YOUTUBE_API_KEY not configured - cannot fetch videos")
        print("To enable YouTube video recommendations, set YOUTUBE_API_KEY in your .env file")
        return []
    
    # Build focused search query
    problem_title = problem_data.get("title", "System Design")
    query = f"System design of {problem_title}"
    
    # Make API request
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": 5,
            "key": api_key,
            "relevanceLanguage": "en",
            "safeSearch": "strict"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        videos = []
        
        # Limit to exactly 5 videos
        for item in data.get("items", [])[:5]:
            video_id = item.get("id", {}).get("videoId")
            snippet = item.get("snippet", {})
            
            if video_id:
                videos.append({
                    "title": snippet.get("title", "Unknown Title"),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "channel": snippet.get("channelTitle", "Unknown Channel"),
                    "reason": f"Recommended video about {problem_title}"
                })
        
        print(f"Successfully fetched {len(videos)} YouTube videos (max 5)")
        return videos[:5]  # Ensure we never return more than 5
        
    except requests.exceptions.HTTPError as e:
        print(f"YouTube API HTTP error: {e}")
        print(f"Response: {e.response.text if hasattr(e, 'response') else 'No response'}")
        return []
    except Exception as e:
        print(f"YouTube API error: {e}")
        return []
