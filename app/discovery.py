"""
Finds candidate businesses using the Google Places API (Text Search + Place
Details). This is used instead of scraping Google Maps directly because:
  1. It's within Google's ToS.
  2. Google gives ~$200/month free credit on the Places API, which comfortably
     covers a 5-leads/day pipeline (~150 lookups/month).

Docs: https://developers.google.com/maps/documentation/places/web-service/text-search
"""
import time
import requests

from app.config import settings

PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


def find_businesses(niche: str, location: str, limit: int = 20) -> list:
    """Returns a list of dicts: {name, place_id, formatted_address, website}"""
    query = f"{niche} in {location}"
    params = {"query": query, "key": settings.google_places_api_key}
    resp = requests.get(PLACES_TEXT_SEARCH_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        raise RuntimeError(f"Places API error: {data.get('status')} - {data.get('error_message')}")

    results = []
    for place in data.get("results", [])[:limit]:
        details = _get_place_details(place["place_id"])
        if not details:
            continue
        website = details.get("website")
        if not website:
            continue  # no website at all -> not a "weak website" case, skip (different outreach angle)
        results.append({
            "name": details.get("name", place.get("name")),
            "place_id": place["place_id"],
            "formatted_address": details.get("formatted_address"),
            "website": website,
            "phone": details.get("formatted_phone_number"),
        })
        time.sleep(0.2)  # be gentle with the API
    return results


def _get_place_details(place_id: str) -> dict:
    params = {
        "place_id": place_id,
        "fields": "name,website,formatted_address,formatted_phone_number",
        "key": settings.google_places_api_key,
    }
    resp = requests.get(PLACES_DETAILS_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "OK":
        return {}
    return data.get("result", {})
