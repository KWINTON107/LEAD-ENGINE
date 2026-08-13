"""
Scores a scraped site 0-100. Businesses scoring <= threshold (default 45)
qualify for outreach. Weights are intentionally simple/transparent so you can
tune them per-niche.
"""

WEIGHTS = {
    "ssl": 15,
    "mobile_viewport": 20,
    "modern_css_framework": 15,
    "has_social_presence": 15,
    "has_contact_info": 15,
    "content_richness": 20,
}

MODERN_CSS_SIGNATURES = ("bootstrap", "tailwind", "flex", "grid-template", "--")  # crude CSS var/framework check


def score_site(visit_result: dict) -> int:
    score = 0

    if visit_result.get("has_ssl"):
        score += WEIGHTS["ssl"]

    if visit_result.get("has_viewport_meta"):
        score += WEIGHTS["mobile_viewport"]

    html_len = visit_result.get("html_length", 0)
    # crude modern-framework signal: longer, more structured pages tend to
    # use frameworks; refine by grepping raw HTML for framework class names
    # if you pass it through here instead of just length.
    if html_len > 20000:
        score += WEIGHTS["modern_css_framework"]

    if visit_result.get("social_links"):
        score += WEIGHTS["has_social_presence"]

    if visit_result.get("emails") or visit_result.get("phones"):
        score += WEIGHTS["has_contact_info"]

    text_len = len(visit_result.get("raw_text", ""))
    if text_len > 1500:
        score += WEIGHTS["content_richness"]
    elif text_len > 500:
        score += WEIGHTS["content_richness"] // 2

    return min(score, 100)
