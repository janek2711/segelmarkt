"""flugzeugmarkt.de – Kategorien Segelflugzeuge und Motorsegler."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..util import block_text, clean, detect_currency, parse_number, parse_year, scrub_contact
from .segelflug import _de_date

NAME = "flugzeugmarkt.de"
BASE = "https://www.flugzeugmarkt.de/"
MAX_PAGES = 20
# Diese Felder enthalten Kontaktdaten des Verkaeufers und werden nicht gespeichert.
SKIP_FIELDS = {"mobil", "telefon", "e-mail", "email", "fax", "kontakt", "name", "ansprechpartner"}


def list_items(http, cfg) -> list[dict]:
    items: dict[str, dict] = {}
    for cat in cfg.get("flugzeugmarkt_kategorien", ["segelflugzeuge"]):
        for page in range(1, MAX_PAGES + 1):
            url = urljoin(BASE, cat if page == 1 else f"{cat}/seite-{page}.html")
            soup = BeautifulSoup(http.get(url).content, "lxml")
            cards = soup.select("div.aircraft-listing")
            before = len(items)
            for card in cards:
                a = card.select_one("h2.title a[href]")
                if not a:
                    continue
                m = re.search(r"kaufen-(\d+)\.html", a["href"])
                if not m or m.group(1) in items:
                    continue
                price_el = card.select_one(".price")
                price_text = clean(price_el.get_text()) if price_el else ""
                foot = [clean(li.get_text()) for li in card.select(".listing_footer ul.mb0:not(.share-icons) li")]
                year = hours = loc = None
                for li, f in zip(card.select(".listing_footer ul.mb0:not(.share-icons) li"), foot):
                    icon = " ".join(li.select_one("i").get("class", [])) if li.select_one("i") else ""
                    if "calendar" in icon:
                        year = parse_year(f)
                    elif "clock" in icon:
                        hours = parse_number(f)
                    elif "map-marker" in icon:
                        loc = f
                img = card.select_one("img")
                snippet = card.select_one(".details p")
                items[m.group(1)] = {
                    "ext_id": m.group(1),
                    "url": urljoin(BASE, a["href"]),
                    "title": clean(a.get_text()),
                    "price": parse_number(price_text),
                    "currency": detect_currency(price_text),
                    "price_text": price_text,
                    "kind": "Biete",
                    "year": year,
                    "hours": hours,
                    "location": loc,
                    "image": urljoin(BASE, img["src"]) if img and img.get("src") else None,
                    "snippet": scrub_contact(clean(snippet.get_text())) if snippet else None,
                    "category": cat,
                    "muster_hint": (img.get("alt") if img else None),
                }
            if len(items) == before or not soup.select_one(f"a[href*='seite-{page + 1}.html']"):
                break
    return list(items.values())


def fetch_detail(http, item: dict) -> dict:
    soup = BeautifulSoup(http.get(item["url"]).content, "lxml")
    details: dict[str, str] = {}
    for li in soup.select("ul.list-group li.list-group-item"):
        parts = [clean(x) for x in li.find_all(string=True, recursive=True) if clean(x)]
        if len(parts) < 2:
            continue
        key, val = parts[0], " ".join(parts[1:])
        if key.lower() in SKIP_FIELDS or "@" in val:
            continue
        details.setdefault(key, val)
    desc = soup.select_one("div.aircraft_description")
    out: dict = {"details": details, "description": scrub_contact(block_text(desc))}
    h1 = soup.select_one("h1.title")
    if h1:
        out["title"] = clean(h1.get_text())
    for li in soup.select("li.list-inline-item"):
        t = clean(li.get_text())
        if re.fullmatch(r"\d{1,2}\.\d{1,2}\.\d{4}", t):
            out["published"] = _de_date(t)
            break
    if details.get("Standort"):
        out["location"] = details["Standort"]
    if details.get("Baujahr"):
        out["year"] = parse_year(details["Baujahr"])
    if details.get("Gesamtzeit"):
        out["hours"] = parse_number(details["Gesamtzeit"])
    out["hersteller_hint"] = details.get("Hersteller")
    out["muster_hint"] = details.get("Modellbezeichnung")
    cond = [details.get("Zustand", "")]
    unfall = details.get("Unfall", "")
    # 'Ja, Schäden durch LTB behoben' = reparierter Altschaden -> kein Alarm
    if unfall and unfall.lower() not in ("unfallfrei", "-", "nein", "keine") and "behoben" not in unfall.lower():
        cond.append(f"Unfall: {unfall}")
    out["condition"] = " | ".join(c for c in cond if c)
    return out
