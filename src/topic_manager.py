"""
Topic Queue Management Module
Handles reading from topics.txt, filtering out completed topics, and tracking completion.
"""

import datetime
import logging
from pathlib import Path
from typing import List, Optional, Set

from src.config import BASE_DIR

logger = logging.getLogger("youtube_agent.topics")

TOPICS_FILE = BASE_DIR / "topics.txt"
COMPLETED_TOPICS_FILE = BASE_DIR / "completed_topics.txt"

DEFAULT_FALLBACK_TOPIC = "The Mysterious Disappearance of Flight 370"


def get_completed_topics() -> Set[str]:
    """Read completed topics from completed_topics.txt."""
    completed = set()
    if not COMPLETED_TOPICS_FILE.is_file():
        return completed

    with open(COMPLETED_TOPICS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) >= 2:
                topic_name = parts[1].strip().lower()
                completed.add(topic_name)
            else:
                completed.add(line.lower())

    return completed


def get_next_topic(override_topic: Optional[str] = None) -> str:
    """
    Get the topic to process:
    1. Returns override_topic if explicitly provided.
    2. Otherwise, scans topics.txt for the first uncompleted topic.
    3. Falls back to default topic if queue is exhausted or missing.
    """
    if override_topic and override_topic.strip():
        logger.info(f"Using explicitly specified topic: '{override_topic.strip()}'")
        return override_topic.strip()

    if not TOPICS_FILE.is_file():
        logger.warning(f"'{TOPICS_FILE.name}' not found. Using default fallback topic.")
        return DEFAULT_FALLBACK_TOPIC

    completed = get_completed_topics()

    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            topic = line.strip()
            if not topic or topic.startswith("#"):
                continue
            if topic.lower() not in completed:
                logger.info(f"Selected next unused topic from queue: '{topic}'")
                return topic

    logger.warning("All topics in topics.txt have already been completed! Using default fallback.")
    return DEFAULT_FALLBACK_TOPIC


def mark_topic_completed(topic: str, video_id: Optional[str] = None):
    """Record a topic as finished in completed_topics.txt."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    v_id = video_id or "DRY_RUN"

    entry = f"{timestamp} | {topic} | {v_id}\n"
    with open(COMPLETED_TOPICS_FILE, "a", encoding="utf-8") as f:
        f.write(entry)

    logger.info(f"Marked topic as completed: '{topic}' [{v_id}]")
