"""
Sends the outreach message. Email is tried first (via Gmail API); if no
email was found, falls back to filling the site's contact form via
Playwright. Every message includes sender name, physical address, and an
unsubscribe/opt-out instruction (CAN-SPAM requirement).

Gmail auth: uses a pre-generated OAuth refresh token (GMAIL_TOKEN_JSON secret).
Generate it once locally with google-auth-oauthlib's InstalledAppFlow and
paste the resulting token JSON into your GitHub secret — see README.
"""
import base64
import json
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import settings
from app import db


def build_outreach_message(business_name: str, specific_detail_1: str, specific_detail_2: str,
                            preview_url: str) -> str:
    return f"""Hi there,

I came across {business_name}'s website and noticed {specific_detail_1}, and thought about how {specific_detail_2}.

Out of interest, I put together a modern concept version of your site — same info, refreshed design and mobile layout: {preview_url}

No obligation at all — just tell me if you like it or not. If it's not useful, no worries, I won't follow up again.

Best,
{settings.sender_name}
{settings.sender_physical_address}

---
This is a one-time message. You will not receive further emails from me about this. If you'd like this concept preview taken down, just reply "remove" and I'll delete it immediately.
"""


def send_email(to_email: str, business_name: str, message_body: str) -> tuple:
    """Returns (status, error_message)."""
    if db.is_opted_out(to_email):
        return "skipped_opt_out", None

    try:
        creds = Credentials.from_authorized_user_info(json.loads(settings.gmail_token_json))
        service = build("gmail", "v1", credentials=creds)

        mime_msg = MIMEText(message_body)
        mime_msg["to"] = to_email
        mime_msg["from"] = settings.sender_email
        mime_msg["subject"] = f"A concept redesign for {business_name}"

        raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return "sent", None
    except Exception as e:
        return "failed", str(e)


def submit_contact_form(site_visitor, contact_form_url: str, business_name: str, message_body: str) -> tuple:
    """Uses the already-open Playwright browser (SiteVisitor) to find and
    fill a contact form. Returns (status, error_message)."""
    page = site_visitor._browser.new_page()
    try:
        page.goto(contact_form_url, timeout=15000, wait_until="domcontentloaded")

        name_field = page.locator('input[name*="name" i], input[id*="name" i]').first
        email_field = page.locator('input[type="email"], input[name*="email" i]').first
        message_field = page.locator('textarea').first

        if name_field.count() == 0 or email_field.count() == 0 or message_field.count() == 0:
            return "failed", "Could not locate expected form fields"

        name_field.fill(settings.sender_name)
        email_field.fill(settings.sender_email)
        message_field.fill(message_body)

        submit_btn = page.locator('button[type="submit"], input[type="submit"]').first
        if submit_btn.count() == 0:
            return "failed", "Could not locate submit button"
        submit_btn.click()
        page.wait_for_timeout(2000)
        return "sent", None
    except Exception as e:
        return "failed", str(e)
    finally:
        page.close()
