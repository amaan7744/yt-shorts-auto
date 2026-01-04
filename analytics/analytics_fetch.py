#!/usr/bin/env python3

import os
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ---------------------------------
# CONFIG
# ---------------------------------

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

MEMORY_DIR = Path("memory")
PERF_LOG = MEMORY_DIR / "performance_log.json"
SIGNAL_FILE = MEMORY_DIR / "last_signal.json"

# Performance thresholds (REALISTIC)
KILL_COMPLETION_RATE = 0.60
GOOD_COMPLETION_RATE = 0.75
VIRAL_COMPLETION_RATE = 0.85

MIN_VIEWS_REQUIRED = 100  # avoid noise

# ---------------------------------
# AUTH
# ---------------------------------

def get_credentials():
    return Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=SCOPES,
    )


def get_analytics_service():
    return build("youtubeAnalytics", "v2", credentials=get_credentials())


# ---------------------------------
# FETCH
# ---------------------------------

def fetch_video_analytics(video_id: str, days_back: int = 7) -> dict | None:
    """
    Fetch analytics for a Short.
    Returns None if analytics not ready yet.
    """

    service = get_analytics_service()

    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days_back)

    try:
        response = service.reports().query(
            ids=f"channel=={os.environ['YT_CHANNEL_ID']}",
            startDate=start_date.isoformat(),
            endDate=end_date.isoformat(),
            metrics="views,averageViewDuration,averageViewPercentage,likes,comments",
            dimensions="video",
            filters=f"video=={video_id}",
        ).execute()

    except HttpError as e:
        if e.resp.status in (403, 400):
            print("[ANALYTICS] Analytics not available yet — skipping")
            return None
        raise

    if not response.get("rows"):
        return None

    row = response["rows"][0]
    columns = [c["name"] for c in response["columnHeaders"]]

    return dict(zip(columns, row))


# ---------------------------------
# EVALUATION
# ---------------------------------

def evaluate_performance(data: dict) -> dict:
    views = int(data.get("views", 0))
    completion = float(data.get("averageViewPercentage", 0)) / 100

    if views < MIN_VIEWS_REQUIRED:
        verdict = "insufficient_data"
    elif completion >= VIRAL_COMPLETION_RATE:
        verdict = "viral_candidate"
    elif completion >= GOOD_COMPLETION_RATE:
        verdict = "good"
    elif completion < KILL_COMPLETION_RATE:
        verdict = "kill"
    else:
        verdict = "average"

    return {
        "views": views,
        "avg_view_duration": round(float(data.get("averageViewDuration", 0)), 2),
        "completion_rate": round(completion, 3),
        "likes": int(data.get("likes", 0)),
        "comments": int(data.get("comments", 0)),
        "verdict": verdict,
    }


# ---------------------------------
# STORAGE
# ---------------------------------

def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_json(path: Path, data: dict):
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def log_performance(video_id: str, performance: dict):
    log = load_json(PERF_LOG)

    log[video_id] = {
        **performance,
        "checked_at": datetime.utcnow().isoformat(),
    }

    save_json(PERF_LOG, log)


def emit_signal(video_id: str, performance: dict):
    """
    Emits the latest decision for downstream automation.
    """
    signal = {
        "video_id": video_id,
        "verdict": performance["verdict"],
        "completion_rate": performance["completion_rate"],
        "views": performance["views"],
        "timestamp": datetime.utcnow().isoformat(),
    }

    save_json(SIGNAL_FILE, signal)


# ---------------------------------
# CLI
# ---------------------------------

def main():
    if len(sys.argv) != 2:
        print("Usage: python analytics_fetch.py <video_id>")
        sys.exit(1)

    video_id = sys.argv[1]

    data = fetch_video_analytics(video_id)
    if not data:
        print(f"[ANALYTICS] No usable data yet for {video_id}")
        return

    performance = evaluate_performance(data)

    log_performance(video_id, performance)
    emit_signal(video_id, performance)

    print(f"[ANALYTICS] {video_id}")
    for k, v in performance.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
