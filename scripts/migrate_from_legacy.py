#!/usr/bin/env python3
"""
One-off migration helpers from legacy repos:

- youtube_analysis: public schema tables -> already compatible with `market` if you pg_dump/restore
  into schema market (rename schema) or use INSERT...SELECT across DBs.

- video_subs_and_desc: schema `video_analysis` (integer video PK) -> `studio.media_assets` (UUID).

Run with DATABASE_URL pointing to the new DB. Adjust connection URLs for source DBs.
This script is a template: fill in SOURCE_* URLs and run in a maintenance window.
"""
from __future__ import annotations

import os
import uuid

# Example using psycopg2 — install if needed: pip install psycopg2-binary
# import psycopg2
#
# def migrate_studio_from_video_analysis():
#     target = os.environ["DATABASE_URL"]
#     source = os.environ["LEGACY_VIDEO_ANALYSIS_URL"]
#     ...

if __name__ == "__main__":
    print(__doc__)
    print("Configure LEGACY_* and DATABASE_URL, then implement COPY or INSERT...SELECT.")
    print("For Kaggle loader: point load_keggle_data at DATABASE_URL and add channel_id resolution.")
