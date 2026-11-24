"""soaringmarket.eu – Rubrik Segelflugzeuge."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..util import block_text, clean, detect_currency, detect_kind, parse_number, parse_year, scrub_contact
from .segelflug import _de_date

NAME = "soaringmarket.eu"
BASE = "https://soaringmarket.eu"
LIST_URL = BASE + "/de/segelflugzeuge/"
MAX_PAGES = 40


def list_items(http, cfg) -> list[dict]:
    items: dict[str, dict] = {}
    for page in range(1, MAX_PAGES + 1):
        soup = BeautifulSoup(http.get(LIST_URL + (f"?page={page}" if page > 1 else "")).content, "lxml")
        before = len(items)
        for card in soup.select("article.listing-card"):
            a = card.select_one("h3 a[href*='/listings/']")
            if not a:
                continue
            m = re.search(r"/listings/([0-9a-f-]{36})/", a["href"])
            if not m or m.group(1) in items:
                continue
            price_el = card.select_one(".listing-price")
            price_text = clean(price_el.get_text()) if price_el else ""
            specs = [clean(s.get_text()) for s in card.select(".listing-specs span")]
            year = next((parse_year(s) for s in specs if re.fullmatch(r"\d{4}", s)), None)
            hours = next((parse_number(s) for s in specs if s.endswith(" h")), None)
            badge = card.select_one(".offer-badge")
            title = clean(a.get_text())
            kind = detect_kind(title, badge.get_text() if badge else None)
            if "pro tag" in price_text.lower() or "/tag" in price_text.lower() or "per day" in price_text.lower():
                kind = "Charter"
            img = card.select_one("img")
            loc = card.select_one(".listing-location")
            items[m.group(1)] = {
                "ext_id": m.group(1),
                "url": urljoin(BASE, a["href"]),
                "title": title,
                "price": parse_number(price_text),
                "currency": detect_currency(price_text),
                "price_text": price_text,
                "kind": kind,
                "year": year,
                "hours": hours,
                "location": clean(loc.get_text()) if loc else None,
                "image": urljoin(BASE, img["src"]) if img and img.get("src") else None,
                "snippet": clean(card.select_one(".listing-engine").get_text(" ")) if card.select_one(".listing-engine") else None,
            }
        if len(items) == before:
            break
    return list(items.values())


def fetch_detail(http, item: dict) -> dict:
    soup = BeautifulSoup(http.get(item["url"]).content, "lxml")
    details: dict[str, str] = {}
    for div in soup.select("dl.listing-facts > div"):
        dt, dd = div.select_one("dt"), div.select_one("dd")
        if dt and dd:
            details[clean(dt.get_text())] = clean(dd.get_text(" "))
    desc = soup.select_one("div.listing-description")
    out: dict = {"details": details, "description": scrub_contact(block_text(desc))}
    for li in soup.select("ul.listing-summary-meta li"):
        t = clean(li.get_text())
        if t.lower().startswith(("veröffentlicht", "published")):
            out["published"] = _de_date(t)
        elif t:
            out["location"] = t
    if details.get("Baujahr"):
        out["year"] = parse_year(details["Baujahr"])
    if details.get("Gesamtflugstunden"):
        out["hours"] = parse_number(details["Gesamtflugstunden"])
    out["hersteller_hint"] = details.get("Hersteller")
    out["muster_hint"] = details.get("Muster")
    out["condition"] = details.get("Zustand")
    return out
