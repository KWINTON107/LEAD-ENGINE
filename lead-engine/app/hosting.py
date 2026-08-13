"""
Free hosting: commits generated HTML into the `gh-pages` branch of this same
repo. GitHub Pages serves it automatically at:

    {PAGES_BASE_URL}/preview/{slug}/index.html

Requires no third-party hosting account or API key — just the repo's own
GITHUB_TOKEN, which GitHub Actions provides automatically. This script is
meant to be called from within the GitHub Actions runner (see
.github/workflows/daily.yml), where the repo is already checked out.
"""
import os
import re
import subprocess

from app.config import settings


def slugify(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return s or "business"


def publish_site(business_name: str, html_content: str) -> str:
    """Writes the HTML into ./pages-checkout/preview/<slug>/index.html.
    The actual git commit/push happens once for the whole run in
    main.py / the workflow, not per-site, to keep it to a single push.
    Returns the public URL.
    """
    slug = slugify(business_name)
    out_dir = os.path.join("pages-checkout", "preview", slug)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)

    base = settings.pages_base_url.rstrip("/")
    return f"{base}/preview/{slug}/"


def checkout_pages_branch():
    """Ensures ./pages-checkout has the gh-pages branch checked out.
    Called once at the start of a run."""
    if os.path.isdir("pages-checkout"):
        return
    repo_url = f"https://github.com/{settings.pages_repo_slug}.git"
    branch = settings.pages_branch
    # try checking out existing branch; if it doesn't exist yet, create an orphan branch
    result = subprocess.run(
        ["git", "clone", "--branch", branch, "--single-branch", repo_url, "pages-checkout"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        subprocess.run(["git", "clone", repo_url, "pages-checkout"], check=True)
        subprocess.run(["git", "-C", "pages-checkout", "checkout", "--orphan", branch], check=True)
        subprocess.run(["git", "-C", "pages-checkout", "rm", "-rf", "."], check=True, capture_output=True)


def commit_and_push_pages(commit_message: str):
    subprocess.run(["git", "-C", "pages-checkout", "add", "."], check=True)
    diff = subprocess.run(["git", "-C", "pages-checkout", "diff", "--cached", "--quiet"])
    if diff.returncode == 0:
        return  # nothing to commit
    subprocess.run(["git", "-C", "pages-checkout", "commit", "-m", commit_message], check=True)
    subprocess.run(["git", "-C", "pages-checkout", "push", "origin", settings.pages_branch], check=True)
