"""
Real-Time Trend Hijacking Agent (Module A)
Fetches breaking real-time trends from Google Trends RSS and Reddit public JSON feeds,
filters out gossip/politics using Google Gemini 2.5 Flash, and automatically prepends
the top viral documentary story angles to topics.txt.
"""

import asyncio
import json
import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Set
import httpx

from src.config import Config, BASE_DIR
from src.topic_manager import TOPICS_FILE, get_completed_topics

logger = logging.getLogger("youtube_agent.trend_hunter")

DEFAULT_REDDIT_SUBREDDITS = [
    "UnresolvedMysteries",
    "todayilearned",
    "history",
    "technology",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) YouTubeDocAgent/1.0"
}


async def fetch_google_trends(geo: str = "US", client: Optional[httpx.AsyncClient] = None) -> List[str]:
    """Fetch real-time trending search queries from Google Trends RSS feed."""
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    logger.info(f"Fetching Google Trends RSS for region: {geo}...")
    headlines = []

    try:
        close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=20.0, headers=HEADERS)
            close_client = True

        resp = await client.get(url, follow_redirects=True)
        if resp.status_code == 200:
            root = ET.fromstring(resp.text)
            for item in root.findall(".//item"):
                title_elem = item.find("title")
                if title_elem is not None and title_elem.text:
                    headlines.append(title_elem.text.strip())
                # Also collect news item title if available
                news_title = item.find("{https://trends.google.com/trending/rss}news_item/{https://trends.google.com/trending/rss}news_item_title")
                if news_title is not None and news_title.text:
                    headlines.append(news_title.text.strip())

        if close_client:
            await client.aclose()
    except Exception as err:
        logger.warning(f"Could not fetch Google Trends for {geo}: {err}")

    logger.info(f"Collected {len(headlines)} candidate headlines from Google Trends ({geo}).")
    return headlines


async def fetch_reddit_trends(subreddit: str, limit: int = 15, client: Optional[httpx.AsyncClient] = None) -> List[str]:
    """Fetch viral discussion headlines from public Reddit JSON feeds (no API key required)."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    logger.info(f"Fetching top discussions from Reddit r/{subreddit}...")
    posts = []

    try:
        close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=20.0, headers=HEADERS)
            close_client = True

        resp = await client.get(url, follow_redirects=True)
        if resp.status_code == 200:
            data = resp.json()
            children = data.get("data", {}).get("children", [])
            for child in children:
                post_data = child.get("data", {})
                title = post_data.get("title", "").strip()
                score = post_data.get("score", 0)
                # Filter out sticky/pinned moderator posts
                if title and not post_data.get("stickied", False) and score > 20:
                    posts.append(title)

        if close_client:
            await client.aclose()
    except Exception as err:
        logger.warning(f"Could not fetch Reddit r/{subreddit}: {err}")

    logger.info(f"Collected {len(posts)} posts from Reddit r/{subreddit}.")
    return posts


async def collect_raw_trend_candidates(
    country_codes: Optional[List[str]] = None,
    subreddits: Optional[List[str]] = None,
) -> List[str]:
    """Aggregate trend candidates from multiple Google Trends regions and Reddit communities."""
    geos = country_codes or Config.TREND_COUNTRY_CODES
    subs = subreddits or DEFAULT_REDDIT_SUBREDDITS

    all_raw = []
    async with httpx.AsyncClient(timeout=25.0, headers=HEADERS) as client:
        # Fetch Google Trends for each configured region
        g_tasks = [fetch_google_trends(geo, client) for geo in geos]
        # Fetch Reddit feeds
        r_tasks = [fetch_reddit_trends(sub, client=client) for sub in subs]

        results = await asyncio.gather(*g_tasks, *r_tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, list):
                all_raw.extend(res)

    # De-duplicate while preserving order
    seen = set()
    unique_candidates = []
    for item in all_raw:
        norm = item.strip().lower()
        if norm and norm not in seen and len(item) > 10:
            seen.add(norm)
            unique_candidates.append(item.strip())

    logger.info(f"Aggregated {len(unique_candidates)} unique raw trend candidates.")
    return unique_candidates


def score_and_filter_trends_with_gemini(
    raw_headlines: List[str],
    max_topics: int = 3,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Use Gemini 2.5 Flash to filter noise and craft high-retention documentary story angles."""
    key = api_key or Config.GEMINI_API_KEY
    model = model_name or Config.GEMINI_MODEL

    if not key:
        raise ValueError("GEMINI_API_KEY is required to score trends.")

    # Slice top 60 candidates to keep prompt concise
    sample_headlines = raw_headlines[:60]
    headlines_text = "\n".join(f"- {h}" for h in sample_headlines)

    prompt = f"""You are an elite YouTube Documentary Trend Analyst (producing content like 'Info with Ahsan', 'Vox', 'Fern', 'MagnatesMedia').

Below is a raw list of trending headlines and discussions from Google Trends and Reddit:
{headlines_text}

TASK:
1. STRICTLY FILTER OUT: Routine political elections, political arguments, daily sports results, celebrity breakups/gossip, weather updates, and mundane product launches.
2. SELECT THE TOP {max_topics} MOST VIRAL, HIGH-RETENTION DOCUMENTARY TOPICS.
   Look for:
   - Deep unresolved mysteries, bizarre scientific anomalies, or historical secrets
   - Shocking technological breakthroughs or cyber conspiracies
   - Fascinating corporate collapses or heist investigations
3. Transform each chosen item into a dramatic, click-worthy documentary topic title and identify its suspense angle.

OUTPUT FORMAT:
Return a single JSON array with up to {max_topics} objects matching this exact schema:
[
  {{
    "topic": "Clean Dramatic Documentary Title (e.g. The 1974 Declassified CIA Ocean Mystery)",
    "angle": "Why this story creates intense suspense and viewer retention",
    "source_headline": "Original raw headline reference",
    "viral_reason": "Specific psychological hook driving high CTR"
  }}
]

Return strictly valid JSON only. No markdown fences, no explanatory prose.
"""

    logger.info(f"Filtering and scoring trends with Gemini ({model})...")

    raw_text = ""
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
            config=types.GenerateContentConfig(temperature=0.4, response_mime_type="application/json"),
        )
        raw_text = resp.text or ""
    except Exception as e1:
        try:
            import google.generativeai as legacy_genai

            legacy_genai.configure(api_key=key)
            g_model = legacy_genai.GenerativeModel(model_name=model)
            resp = g_model.generate_content(prompt)
            raw_text = resp.text or ""
        except Exception as e2:
            raise RuntimeError(f"Failed to filter trends with Gemini: {e1} / {e2}")

    # Clean markdown code fences
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)

    try:
        winning_topics = json.loads(cleaned)
        if isinstance(winning_topics, list):
            return winning_topics
        elif isinstance(winning_topics, dict) and "topics" in winning_topics:
            return winning_topics["topics"]
        return []
    except Exception as err:
        logger.error(f"Failed to parse Gemini trend ranking JSON: {err}. Raw output:\n{raw_text}")
        return []


def push_trends_to_queue(winning_topics: List[Dict[str, str]]) -> List[str]:
    """Check against topics.txt and completed_topics.txt, and prepend new winners to topics.txt."""
    completed = get_completed_topics()

    # Read existing topics.txt
    existing_topics = []
    if TOPICS_FILE.is_file():
        with open(TOPICS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                t = line.strip()
                if t:
                    existing_topics.append(t)

    existing_lower = {t.lower() for t in existing_topics}

    added_topics = []
    for item in winning_topics:
        topic_title = item.get("topic", "").strip()
        if not topic_title:
            continue
        norm = topic_title.lower()
        if norm not in completed and norm not in existing_lower:
            added_topics.append(topic_title)
            existing_lower.add(norm)

    if added_topics:
        # Prepend new trending topics to the top of the queue
        new_queue = added_topics + existing_topics
        with open(TOPICS_FILE, "w", encoding="utf-8") as f:
            for t in new_queue:
                f.write(f"{t}\n")
        logger.info(f"✅ Successfully prepended {len(added_topics)} trending topic(s) to {TOPICS_FILE.name}:")
        for at in added_topics:
            logger.info(f"   🔥 [TRENDING] {at}")
    else:
        logger.info("All discovered trends are already present in queue or completed.")

    return added_topics


def run_trend_hunter(
    country_codes: Optional[List[str]] = None,
    max_topics: int = 3,
) -> List[Dict[str, str]]:
    """Execute end-to-end trend hunting, scoring, and queue integration."""
    print("=" * 65)
    print("🕵️  MODULE A: REAL-TIME TREND HIJACKING AGENT")
    print("=" * 65)

    # 1. Fetch raw candidates
    candidates = asyncio.run(collect_raw_trend_candidates(country_codes=country_codes))
    if not candidates:
        logger.warning("No candidate trends could be fetched. Check internet connection.")
        return []

    print(f"📡 Found {len(candidates)} raw trend headlines across Google Trends & Reddit.")

    # 2. Score & filter with Gemini
    winning_topics = score_and_filter_trends_with_gemini(candidates, max_topics=max_topics)

    print("\n🎯 TOP VIRAL DOCUMENTARY STORY ANGLES SELECTED BY GEMINI:")
    for idx, item in enumerate(winning_topics, start=1):
        print(f" {idx}. 🎬 {item.get('topic')}")
        print(f"    💡 Angle: {item.get('angle')}")
        print(f"    🔥 Hook:  {item.get('viral_reason')}")

    # 3. Push to queue
    added = push_trends_to_queue(winning_topics)
    print(f"\n✅ Added {len(added)} new trending topic(s) to the top of '{TOPICS_FILE.name}'!")
    print("=" * 65 + "\n")

    return winning_topics


if __name__ == "__main__":
    run_trend_hunter()
