"""
Run this ONCE on your own machine (not in CI) to produce the token JSON you'll
paste into the GMAIL_TOKEN_JSON GitHub secret.

Prereqs:
  1. Go to https://console.cloud.google.com/ -> create a project (free).
  2. Enable the "Gmail API".
  3. Create OAuth client credentials, type "Desktop app" -> download as
     client_secret.json, put it next to this script.
  4. pip install google-auth-oauthlib
  5. Run: python generate_gmail_token.py
  6. It opens a browser, you log in with the Gmail account you want to send
     from, and it prints the token JSON to paste into GitHub secrets.
"""
import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
creds = flow.run_local_server(port=0)

print("\n--- Paste this whole line into the GMAIL_TOKEN_JSON GitHub secret ---\n")
print(creds.to_json())
