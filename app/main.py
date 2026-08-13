"""
Runs the full daily pipeline once. Invoked by .github/workflows/daily.yml.

Steps: discover -> qualify (score) -> scrape -> generate -> host -> outreach -> log.
Hard stop at settings.daily_capacity successful outreaches and
settings.max_site_visits_per_run total visits, whichever comes first.
"""
import sys
import time
from datetime import date

from app.config import settings
from app import db
from app.discovery import find_businesses
from app.scraper import SiteVisitor, extract_scraped_data
from app.scorer import score_site
from app.site_generator import generate_site_html
from app.hosting import checkout_pages_branch, publish_site, commit_and_push_pages
from app.outreach import build_outreach_message, send_email, submit_contact_form


def run():
    settings.validate()
    db.init_db()
    checkout_pages_branch()

    target_location = db.get_next_location(settings.target_locations)
    print(f"Target city for this run: {target_location}")

    already_today = db.prospects_contacted_today()
    remaining_capacity = max(settings.daily_capacity - already_today, 0)
    if remaining_capacity <= 0:
        print("Daily capacity already reached. Exiting.")
        return

    visits_used = 0
    contacted = 0
    any_site_committed = False

    with SiteVisitor(headless=True) as visitor:
        for niche in settings.niches:
            if contacted >= remaining_capacity or visits_used >= settings.max_site_visits_per_run:
                break

            try:
                candidates = find_businesses(niche.strip(), target_location, limit=15)
            except Exception as e:
                print(f"[discovery] failed for niche={niche}: {e}", file=sys.stderr)
                continue

            for biz in candidates:
                if contacted >= remaining_capacity or visits_used >= settings.max_site_visits_per_run:
                    break

                if db.is_duplicate(biz["name"], target_location):
                    continue

                # STEP 1: qualify
                try:
                    visit_result = visitor.visit(biz["website"])
                    visits_used += 1
                except Exception as e:
                    print(f"[visit] failed for {biz['name']}: {e}", file=sys.stderr)
                    continue

                quality_score = score_site(visit_result)
                if quality_score > settings.quality_score_threshold:
                    continue  # site is already decent — not a target

                # STEP 2: scrape (reuse visit_result, already have the data)
                scraped = extract_scraped_data(visit_result, biz["name"])
                if not scraped["emails"] and not scraped["phones"]:
                    print(f"[scrape] essential contact data missing for {biz['name']}, skipping")
                    continue

                prospect_id = db.insert_prospect(
                    business_name=biz["name"], niche=niche.strip(), location=target_location,
                    website_url=biz["website"], quality_score=quality_score, scraped_data=scraped,
                )

                # STEP 3: generate
                html_content = generate_site_html(
                    scraped, biz["website"], settings.sender_name, settings.sender_email,
                    generated_date=date.today().isoformat(),
                )

                # STEP 4: host
                public_url = publish_site(biz["name"], html_content)
                db.insert_generated_site(prospect_id, html_content, public_url)
                db.update_prospect(prospect_id, enhanced_site_url=public_url)
                any_site_committed = True

                # STEP 5: outreach
                message = build_outreach_message(
                    biz["name"],
                    specific_detail_1="it doesn't look great on mobile",
                    specific_detail_2="a refreshed layout could help more visitors turn into bookings",
                    preview_url=public_url,
                )

                if scraped["emails"]:
                    to_email = scraped["emails"][0]
                    status, err = send_email(to_email, biz["name"], message)
                    method = "email"
                    db.update_prospect(prospect_id, contact_email=to_email)
                else:
                    # fallback: try contact form
                    contact_url = biz["website"].rstrip("/") + "/contact"
                    status, err = submit_contact_form(visitor, contact_url, biz["name"], message)
                    method = "contact_form"

                db.insert_outreach_log(prospect_id, method, message, status, err)

                if status == "sent":
                    db.update_prospect(prospect_id, outreach_method=method, outreach_status="contacted",
                                        outreach_date=date.today().isoformat())
                    contacted += 1
                elif status == "skipped_opt_out":
                    db.update_prospect(prospect_id, outreach_status="opted_out")
                else:
                    db.update_prospect(prospect_id, outreach_status="failed")

                time.sleep(1)  # be polite between businesses

    if any_site_committed:
        commit_and_push_pages(f"Add preview sites — {date.today().isoformat()}")

    print(f"Run complete. Contacted {contacted} businesses, visited {visits_used} sites.")


if __name__ == "__main__":
    run()
