"""
Sends a Friday 5pm summary of the week's activity to the sender's own inbox.
Invoked by .github/workflows/weekly_digest.yml.
"""
import json
from datetime import date, timedelta

from app.config import settings
from app import db
from app.outreach import send_email


def run():
    settings.validate()
    db.init_db()

    since = (date.today() - timedelta(days=7)).isoformat()
    rows = db.prospects_for_digest_since(since)

    if not rows:
        body = "No prospects processed this week."
    else:
        lines = [f"Weekly Lead Engine Digest — {date.today().isoformat()}", ""]
        by_status = {}
        for r in rows:
            by_status.setdefault(r["outreach_status"], 0)
            by_status[r["outreach_status"]] += 1
        lines.append("Summary:")
        for status, count in by_status.items():
            lines.append(f"  {status}: {count}")
        lines.append("")
        lines.append("Details:")
        for r in rows:
            lines.append(
                f"- {r['business_name']} ({r['niche']}) | score={r['quality_score']} | "
                f"status={r['outreach_status']} | preview={r['enhanced_site_url']}"
            )
        body = "\n".join(lines)

    status, err = send_email(settings.sender_email, "Weekly Digest", body)
    print(f"Digest send status: {status} {err or ''}")


if __name__ == "__main__":
    run()
