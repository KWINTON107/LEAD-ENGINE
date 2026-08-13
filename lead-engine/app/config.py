"""
Central config. All values are pulled from environment variables so nothing
sensitive lives in the repo. Set these as GitHub Actions "Secrets" (Settings
-> Secrets and variables -> Actions) in your repo.
"""
import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    # --- targeting ---
    target_location: str = os.environ.get("LEAD_TARGET_LOCATION", "Bhubaneswar, Odisha, India")
    niches: list = field(default_factory=lambda: os.environ.get(
        "LEAD_NICHES", "dentist,gym,salon,spa"
    ).split(","))

    # --- limits (kept conservative on purpose) ---
    quality_score_threshold: int = int(os.environ.get("LEAD_QUALITY_THRESHOLD", "45"))
    daily_capacity: int = int(os.environ.get("LEAD_DAILY_CAPACITY", "5"))
    max_site_visits_per_run: int = int(os.environ.get("LEAD_MAX_VISITS", "30"))
    max_concurrent_browsers: int = 1
    max_retries: int = 3

    # --- sender identity (REQUIRED for CAN-SPAM compliance) ---
    sender_name: str = os.environ.get("LEAD_SENDER_NAME", "")
    sender_email: str = os.environ.get("LEAD_SENDER_EMAIL", "")
    sender_physical_address: str = os.environ.get("LEAD_SENDER_ADDRESS", "")

    # --- API keys / credentials (set as GitHub Secrets, never commit these) ---
    google_places_api_key: str = os.environ.get("GOOGLE_PLACES_API_KEY", "")
    gmail_credentials_json: str = os.environ.get("GMAIL_CREDENTIALS_JSON", "")  # OAuth client json, base64 or raw
    gmail_token_json: str = os.environ.get("GMAIL_TOKEN_JSON", "")  # stored refresh token, base64 or raw

    # --- hosting (GitHub Pages) ---
    pages_repo_slug: str = os.environ.get("PAGES_REPO_SLUG", "")  # e.g. "yourname/lead-engine"
    pages_branch: str = os.environ.get("PAGES_BRANCH", "gh-pages")
    pages_base_url: str = os.environ.get("PAGES_BASE_URL", "")  # e.g. https://yourname.github.io/lead-engine

    db_path: str = os.environ.get("LEAD_DB_PATH", "data/leads.db")

    def validate(self):
        missing = []
        for field_name in ("sender_name", "sender_email", "sender_physical_address",
                            "google_places_api_key", "pages_repo_slug", "pages_base_url"):
            if not getattr(self, field_name):
                missing.append(field_name)
        if missing:
            raise RuntimeError(
                f"Missing required config: {', '.join(missing)}. "
                "Set these as GitHub Actions secrets before running."
            )


settings = Settings()
