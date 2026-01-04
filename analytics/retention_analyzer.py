import json
from pathlib import Path
from typing import Dict

PERFORMANCE_FILE = Path("memory/performance_log.json")
RETENTION_REPORT = Path("memory/retention_report.json")

# Heuristic thresholds (Shorts-optimized)
HOOK_FAIL_THRESHOLD = 0.55     # <55% → people swiped instantly
MID_DROP_THRESHOLD = 0.70      # 55–70% → pacing problem
GOOD_THRESHOLD = 0.80          # 70–80% → decent
EXCELLENT_THRESHOLD = 0.85     # 85%+ → viral territory


def load_performance():
    if not PERFORMANCE_FILE.exists():
        return {}
    return json.loads(PERFORMANCE_FILE.read_text())


def save_report(report: Dict):
    RETENTION_REPORT.parent.mkdir(exist_ok=True)
    RETENTION_REPORT.write_text(json.dumps(report, indent=2))


def analyze_video(video_id: str, data: Dict) -> Dict:
    """
    Analyzes retention behavior and gives actionable diagnosis.
    """

    completion = data.get("completion_rate", 0)
    views = data.get("views", 0)
    likes = data.get("likes", 0)
    comments = data.get("comments", 0)

    diagnosis = []
    fix = []

    # 1. Hook failure (first 1–3 seconds)
    if completion < HOOK_FAIL_THRESHOLD:
        diagnosis.append("hook_failed")
        fix.extend([
            "Rewrite first line with shock/contradiction",
            "Start with outcome, not context",
            "Increase first 2s voice speed",
            "Change opening visual immediately"
        ])

    # 2. Mid-video drop (pacing issue)
    elif completion < MID_DROP_THRESHOLD:
        diagnosis.append("mid_video_drop")
        fix.extend([
            "Cut filler lines",
            "Add faster visual cuts",
            "Insert micro-pauses before twists",
            "Increase mid-section energy"
        ])

    # 3. Weak ending (no loop)
    elif completion < GOOD_THRESHOLD:
        diagnosis.append("weak_ending")
        fix.extend([
            "End with unresolved sentence",
            "Loop final frame to first frame",
            "Add question-based ending"
        ])

    # 4. Strong performer
    elif completion >= EXCELLENT_THRESHOLD:
        diagnosis.append("high_retention")
        fix.append("Repeat this format and hook structure")

    else:
        diagnosis.append("average_retention")
        fix.append("Minor pacing and hook improvements")

    # Engagement sanity check
    engagement_rate = 0
    if views > 0:
        engagement_rate = round((likes + comments) / views, 4)

    return {
        "video_id": video_id,
        "views": views,
        "completion_rate": completion,
        "engagement_rate": engagement_rate,
        "diagnosis": diagnosis,
        "recommended_fixes": fix
    }


def run_analysis():
    performance = load_performance()
    report = {}

    for video_id, data in performance.items():
        report[video_id] = analyze_video(video_id, data)

    save_report(report)

    print("[RETENTION] Analysis complete.")
    for vid, r in report.items():
        print(f"\nVideo: {vid}")
        print(f"  Completion: {r['completion_rate']}")
        print(f"  Diagnosis: {', '.join(r['diagnosis'])}")


if __name__ == "__main__":
    run_analysis()
