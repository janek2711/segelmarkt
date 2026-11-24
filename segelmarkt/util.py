"""Hilfsfunktionen: HTTP, Preis-/Zahlen-Parsing, Datenschutz-Bereinigung."""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130 Safari/537.36 SegelflugmarktMonitor/1.0 (privat)"
)

# Grobe Umrechnungskurse nur fuer den Preisvergleich im Dashboard.
FX_TO_EUR = {"EUR": 1.0, "CHF": 1.07, "GBP": 1.17, "USD": 0.92, "PLN": 0.23, "CZK": 0.04, "SEK": 0.087, "DKK": 0.134, "NOK": 0.085, "HUF": 0.0025}

MIN_PLAUSIBLE_PRICE = 200  # darunter ist es meist ein Platzhalter ("1 EUR", "123 EUR")


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Http:
    """requests-Session mit Pause zwischen Abrufen (schont die Plattformen)."""

    def __init__(self, pause: float = 1.5):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "de-DE,de;q=0.9,en;q=0.8"})
        self.pause = pause
        self._last = 0.0

    def get(self, url: str, **kw) -> requests.Response:
        wait = self.pause - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        for attempt in range(3):
            try:
                r = self.s.get(url, timeout=30, **kw)
                self._last = time.time()
                if r.status_code >= 500 and attempt < 2:
                    time.sleep(5 * (attempt + 1))
                    continue
                r.raise_for_status()
                return r
            except requests.RequestException:
                self._last = time.time()
                if attempt == 2:
                    raise
                time.sleep(5 * (attempt + 1))
        raise RuntimeError("unreachable")


def clean(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def parse_number(text: str | None) -> float | None:
    """'69.500' -> 69500, '3.175 h' -> 3175, '12,5' -> 12.5"""
    if not text:
        return None
    m = re.search(r"\d[\d.,' ]*", text)
    if not m:
        return None
    raw = m.group(0).strip().replace("'", "").replace(" ", "")
    # deutsches Format: Punkt = Tausender, Komma = Dezimal
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", raw) or ("," in raw and "." not in raw):
        raw = raw.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", raw):
        raw = raw.replace(",", "")
    else:
        raw = raw.replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return None


def detect_currency(text: str | None) -> str:
    t = (text or "").upper()
    for cur in FX_TO_EUR:
        if cur in t:
            return cur
    if "€" in t or "EURO" in t:
        return "EUR"
    if "£" in t:
        return "GBP"
    if "$" in t:
        return "USD"
    if "ZŁ" in t or "ZL" in t:
        return "PLN"
    return "EUR"


def price_eur(price: float | None, currency: str) -> float | None:
    if price is None or price < MIN_PLAUSIBLE_PRICE:
        return None
    return round(price * FX_TO_EUR.get(currency, 1.0))


def parse_year(text: str | None) -> int | None:
    m = re.search(r"\b(19[3-9]\d|20[0-4]\d)\b", text or "")
    return int(m.group(1)) if m else None


WANTED_RE = re.compile(r"^\s*(suche|gesucht|looking for|wanted|ich suche|wir suchen)\b|\b(gesucht|wanted)\s*$", re.I)


def detect_kind(title: str, hint: str | None = None) -> str:
    """Biete / Suche / Charter"""
    h = (hint or "").lower()
    if "such" in h or "gesuch" in h or "wanted" in h:
        return "Suche"
    if "charter" in h or "miet" in h:
        return "Charter"
    if WANTED_RE.search(title or ""):
        return "Suche"
    return "Biete"


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"(?<![\w.])(?:\+|00|0)\d[\d \t/().-]{6,}\d")


def scrub_contact(text: str) -> str:
    """Entfernt Telefonnummern und E-Mail-Adressen der Verkaeufer (Datenschutz)."""
    text = _EMAIL_RE.sub("[E-Mail siehe Inserat]", text or "")

    def repl(m: re.Match) -> str:
        return "[Telefon siehe Inserat]" if len(re.sub(r"\D", "", m.group(0))) >= 9 else m.group(0)

    return _PHONE_RE.sub(repl, text)


def block_text(el) -> str:
    """Text eines HTML-Elements mit erhaltenen Zeilenumbruechen."""
    if el is None:
        return ""
    for br in el.find_all("br"):
        br.replace_with("\n")
    txt = el.get_text("\n")
    lines = [re.sub(r"[ \t\xa0]+", " ", ln).strip() for ln in txt.splitlines()]
    out, blank = [], False
    for ln in lines:
        if not ln:
            if not blank and out:
                out.append("")
            blank = True
        else:
            out.append(ln)
            blank = False
    return "\n".join(out).strip()
