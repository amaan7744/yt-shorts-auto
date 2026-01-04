import os
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# ----------------------------
# CONFIG
# ----------------------------

SCOPES = ["https://www.googleapis.com/auth/yt-analytics.readonly"]
OUTPUT_DIR = Path("memory")
OUTPUT_FILE = OUTPUT_DIR / "performance_log.json"

# Shorts thresholds (BRUTAL but realistic)
KILL_COMPLETION_RATE = 0.60
GOOD_COMPLETION_RATE = 0.75
VIRAL_COMPLETION_RATE = 0.85


# ----------------------------
# AUTH
# ----------------------------

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
    creds = get_credentials()
    return build("youtubeAnalytics", "v2", credentials=creds)


# ----------------------------
# CORE FETCH
# ----------------------------

def fetch_video_analytics(video_id: str, days_back: int = 7) -> dict:
    """
    Fetch analytics for a single Short.
    """

    service = get_analytics_service()

    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days_back)

    response = service.reports().query(
        ids=f"channel=={os.environ['YT_CHANNEL_ID']}",
        startDate=start_date.isoformat(),
        endDate=end_date.isoformat(),
        metrics="views,averageViewDuration,averageViewPercentage,likes,comments",
        dimensions="video",
        filters=f"video=={video_id}",
    ).execute()

    if not response.get("rows"):
        return {}

    row = response["rows"][0]
    columns = [c["name"] for c in response["columnHeaders"]]

    data = dict(zip(columns, row))
    return data


# ----------------------------
# EVALUATION LOGIC
# ----------------------------

def evaluate_performance(data: dict) -> dict:
    """
    Classify video performance.
    """

    completion = data.get("averageViewPercentage", 0) / 100

    if completion >= VIRAL_COMPLETION_RATE:
        verdict = "viral_candidate"
    elif completion >= GOOD_COMPLETION_RATE:
        verdict = "good"
    elif completion < KILL_COMPLETION_RATE:
        verdict = "kill"
    else:
        verdict = "average"

    return {
        "views": data.get("views", 0),
        "avg_view_duration": data.get("averageViewDuration", 0),
        "completion_rate": round(completion, 3),
        "likes": data.get("likes", 0),
        "comments": data.get("comments", 0),
        "verdict": verdict,
    }


# ----------------------------
# STORAGE
# ----------------------------

def load_log():
    if not OUTPUT_FILE.exists():
        return {}
    return json.loads(OUTPUT_FILE.read_text())


def save_log(log: dict):
    OUTPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(log, indent=2))


def log_video_performance(video_id: str, performance: dict):
    log = load_log()

    log[video_id] = {
        **performance,
        "checked_at": datetime.utcnow().isoformat()
    }

    save_log(log)


# ----------------------------
# CLI ENTRY
# ----------------------------

def main():
    if len(sys.argv) != 2:
        print("Usage: python analytics_fetch.py <video_id>")
        sys.exit(1)

    video_id = sys.argv[1]

    data = fetch_video_analytics(video_id)
    if not data:
        print(f"[ANALYTICS] No data yet for video {video_id}")
        return

    performance = evaluate_performance(data)
    log_video_performance(video_id, performance)

    print(f"[ANALYTICS] {video_id}")
    for k, v in performance.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
