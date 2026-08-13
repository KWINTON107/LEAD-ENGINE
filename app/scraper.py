"""
Visits a business's current website with Playwright and extracts:
  - visible text (services, about)
  - contact info (phone, email, address) found in the page
  - dominant brand colors (from CSS)
  - logo image URL
  - basic quality signals used by scorer.py

Single browser instance is reused across the whole run (rate-limit rule:
1 concurrent browser session).
"""
import re
import json
from playwright.sync_api import sync_playwright

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\-\s().]{7,}\d)")


class SiteVisitor:
    """Context manager wrapping a single reused Playwright browser."""

    def __init__(self, headless=True):
        self._pw = None
        self._browser = None
        self.headless = headless

    def __enter__(self):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        return self

    def __exit__(self, *exc):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    def visit(self, url: str, timeout_ms: int = 15000) -> dict:
        page = self._browser.new_page()
        try:
            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            page.wait_for_timeout(1000)

            html = page.content()
            text = page.inner_text("body")
            has_ssl = url.startswith("https://")
            viewport_meta = page.locator('meta[name="viewport"]').count() > 0

            # try common "contact" / "about" links for richer data
            extra_text = ""
            for label in ("contact", "about"):
                try:
                    link = page.locator(f'a:has-text("{label}")').first
                    if link and link.count() > 0:
                        href = link.get_attribute("href")
                        if href:
                            sub = self._browser.new_page()
                            sub.goto(href if href.startswith("http") else url.rstrip("/") + "/" + href.lstrip("/"),
                                      timeout=timeout_ms, wait_until="domcontentloaded")
                            extra_text += "\n" + sub.inner_text("body")
                            sub.close()
                except Exception:
                    pass

            full_text = text + "\n" + extra_text
            emails = list(set(EMAIL_RE.findall(full_text)))
            phones = list(set(PHONE_RE.findall(full_text)))

            logo_url = None
            try:
                logo_el = page.locator('img[class*="logo"], img[id*="logo"], header img').first
                if logo_el and logo_el.count() > 0:
                    logo_url = logo_el.get_attribute("src")
            except Exception:
                pass

            social_links = list(set(re.findall(
                r'https?://(?:www\.)?(?:facebook|instagram|twitter|x|linkedin)\.com/[^\s"\'<>]+', html
            )))

            colors = list(set(re.findall(r'#(?:[0-9a-fA-F]{3}){1,2}\b', html)))[:8]

            return {
                "raw_text": full_text[:6000],
                "emails": emails,
                "phones": phones,
                "logo_url": logo_url,
                "social_links": social_links,
                "colors": colors,
                "has_ssl": has_ssl,
                "has_viewport_meta": viewport_meta,
                "html_length": len(html),
            }
        finally:
            page.close()


def extract_scraped_data(visit_result: dict, business_name: str) -> dict:
    """Shapes raw visit output into the structured Prospect.scraped_data payload."""
    return {
        "business_name": business_name,
        "about_text": visit_result["raw_text"][:1500],
        "emails": visit_result["emails"],
        "phones": visit_result["phones"],
        "logo_url": visit_result["logo_url"],
        "social_links": visit_result["social_links"],
        "brand_colors": visit_result["colors"] or ["#2563eb", "#1e293b"],  # sane fallback palette
        "services": _guess_services(visit_result["raw_text"]),
    }


def _guess_services(text: str) -> list:
    """Very lightweight heuristic list-extraction. Good enough as a starting
    point — you'll likely want to refine this per-niche."""
    lines = [l.strip("-•* \t") for l in text.split("\n")]
    candidates = [l for l in lines if 3 <= len(l.split()) <= 6 and l[:1].isupper()]
    seen, out = set(), []
    for c in candidates:
        if c.lower() not in seen:
            seen.add(c.lower())
            out.append(c)
        if len(out) >= 6:
            break
    return out
