#!/usr/bin/env python3
"""
CLI Runner for Module B: Automated A/B Title & Thumbnail Optimizer
Usage: python optimize_ab.py [--live]
"""

import sys
from src.ab_optimizer import optimize_all_published_videos
from src.config import Config

if __name__ == "__main__":
    is_live = "--live" in sys.argv
    dry_run = False if is_live else Config.DRY_RUN
    optimize_all_published_videos(dry_run=dry_run)
