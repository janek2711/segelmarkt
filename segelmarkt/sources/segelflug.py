"""segelflug.de – Kleinanzeigen, Kategorie Segelflugzeuge (DJ-Classifieds)."""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..util import block_text, clean, detect_currency, detect_kind, parse_number, parse_year, scrub_contact

NAME = "segelflug.de"
BASE = "https://www.segelflug.de"
LIST_URL = BASE + "/index.php/de/kleinanzeigen/filterseite-de/com-djclassifieds-cat-sailplanes,5"
PAGE_SIZE = 48
MAX_PAGES = 30


def list_items(http, cfg) -> list[dict]:
    items: dict[str, dict] = {}
    for page in range(MAX_PAGES):
        url = LIST_URL + (f"?start={page * PAGE_SIZE}" if page else "")
        soup = BeautifulSoup(http.get(url).content, "lxml")
        before = len(items)
        for el in soup.select("div.el-item[id]"):
            a = el.select_one("h3.el-title a[href*='/ad/']")
            if not a or not el["id"].isdigit():
                continue
            ext_id = el["id"]
            if ext_id in items:
                continue
            pv = el.select_one(".price_val")
            pu = el.select_one(".price_unit")
            price_text = clean(f"{pv.get_text() if pv else ''} {pu.get_text() if pu else ''}")
            img = el.select_one("img")
            badge = el.select_one(".type_button")
            title = clean(a.get_text())
            items[ext_id] = {
                "ext_id": ext_id,
                "url": urljoin(BASE, a["href"]),
                "title": title,
                "price": parse_number(pv.get_text()) if pv else None,
                "currency": detect_currency(price_text),
                "price_text": price_text,
                "kind": detect_kind(title, badge.get_text() if badge else None),
                "image": img.get("src") if img else None,
            }
        if len(items) == before:  # keine neuen Inserate mehr -> letzte Seite erreicht
            break
    return list(items.values())


def fetch_detail(http, item: dict) -> dict:
    soup = BeautifulSoup(http.get(item["url"]).content, "lxml")
    details: dict[str, str] = {}
    for row in soup.select("div.uk-child-width-expand"):
        k = row.select_one(".el-title")
        v = row.select_one(".el-content")
        if k and v:
            raw = clean(k.get_text())
            if not raw.endswith(":"):  # nur echte Datenfelder ("Baujahr:"), nicht den Verkaeufer-Kasten
                continue
            key = raw.rstrip(":")
            if key and key not in details:
                details[key] = clean(v.get_text(" "))

    desc_parts = [block_text(d) for d in soup.select("div.uk-panel.uk-margin-remove-top.uk-margin-bottom.uk-text-left")]
    description = scrub_contact("\n\n".join(p for p in desc_parts if p))

    out: dict = {"details": details, "description": description}
    h1 = soup.select_one("h1")
    if h1 and clean(h1.get_text()):
        out["title"] = clean(h1.get_text())

    regions = [clean(s.get_text()) for s in soup.select(".reg_path")]
    airfield = None
    published = None
    negotiable = False
    for c in soup.select(".el-content"):
        t = clean(c.get_text(" "))
        if t.startswith("Flugplatz:"):
            airfield = t.split(":", 1)[1].strip()
        elif t.startswith("Veröffentlicht am:"):
            published = t.split(":", 1)[1].strip()
        elif t.lower() == "preis verhandelbar":
            negotiable = True
    loc = ", ".join(x for x in [airfield, regions[-1] if regions else None] if x)
    if loc:
        out["location"] = loc
    if published:
        out["published"] = _de_date(published)
    if negotiable:
        details["Preis"] = "verhandelbar"

    if details.get("Baujahr"):
        out["year"] = parse_year(details["Baujahr"])
    if details.get("Stunden"):
        out["hours"] = parse_number(details["Stunden"])
    out["hersteller_hint"] = details.get("Hersteller")
    out["condition"] = details.get("Zustand")
    return out


_MONTHS = {m: i for i, m in enumerate(
    ["januar", "februar", "märz", "april", "mai", "juni", "juli", "august", "september", "oktober", "november", "dezember"], 1)}


def _de_date(text: str) -> str | None:
    m = re.search(r"(\d{1,2})\.\s*([A-Za-zäÄ]+)\s+(\d{4})", text)
    if m and m.group(2).lower() in _MONTHS:
        return f"{m.group(3)}-{_MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return None
