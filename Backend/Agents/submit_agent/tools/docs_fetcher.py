"""
Documentation Fetcher Tool
Fetches relevant documentation and article links for learning.
Uses centralized LLM provider (GitHub Copilot API).
"""
from typing import List, Dict, Any
import json
from langchain_core.prompts import ChatPromptTemplate

from core.llm_provider import get_llm

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


async def fetch_docs_llm(
    problem_data: Dict[str, Any],
    missing_concepts: List[str]
) -> List[Dict[str, Any]]:
    """
    Use LLM to suggest documentation and learning resources.
    
    Args:
        problem_data: Problem info
        missing_concepts: Missing concepts from scoring
    
    Returns:
        List of doc recommendations
    """
    try:
        llm = get_llm(temperature=0.7)

        system_prompt = """You are a system design educator. Suggest 4-6 documentation sources.

Focus on: Official docs (AWS, Azure, GCP), system design blogs, educational resources.

Return ONLY JSON array:
[{{"title": "Resource title", "url": "real URL", "source": "source name", "reason": "why helpful"}}, ...]

Prefer real, well-known URLs."""

        user_prompt = f"""Problem: System design of {problem_data.get('title', 'System Design')}

Missing concepts: {', '.join(missing_concepts[:5])}

Suggest docs/articles specifically about designing {problem_data.get('title', 'systems')}."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt)
        ])
        
        chain = prompt | llm
        result = await chain.ainvoke({})
        
        docs = json.loads(result.content)
        
        return docs[:6]
        
    except Exception as e:
        print(f"LLM doc suggestion error: {e}")
        return []


async def fetch_documentation(
    problem_data: Dict[str, Any],
    missing_concepts: List[str]
) -> List[Dict[str, Any]]:
    """
    Main function to fetch documentation resources.
    
    Args:
        problem_data: Problem info
        missing_concepts: Missing concepts
    
    Returns:
        List of documentation links
    """
    # Try LLM suggestions
    docs = await fetch_docs_llm(problem_data, missing_concepts)
    
    if docs:
        return docs
    
    # Final fallback: generic resources
    problem_title = problem_data.get("title", "System Design")
    
    return [
        {
            "title": "System Design Primer",
            "url": "https://github.com/donnemartin/system-design-primer",
            "source": "GitHub",
            "reason": "Comprehensive system design resource"
        },
        {
            "title": "AWS Architecture Center",
            "url": "https://aws.amazon.com/architecture/",
            "source": "AWS",
            "reason": "Learn cloud architecture patterns"
        },
        {
            "title": "Google Cloud Architecture Framework",
            "url": "https://cloud.google.com/architecture/framework",
            "source": "Google Cloud",
            "reason": "Best practices for system design"
        },
        {
            "title": f"{problem_title} - System Design",
            "url": f"https://www.google.com/search?q={problem_title.replace(' ', '+')}+system+design",
            "source": "Google Search",
            "reason": "Search for specific implementation guides"
        }
    ]
