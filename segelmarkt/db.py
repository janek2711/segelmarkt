"""SQLite-Datenbank: alle Inserate, Preisverlauf, Laufprotokoll."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .util import ROOT

DB_PATH = ROOT / "data" / "segelmarkt.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id            TEXT PRIMARY KEY,          -- quelle:externe_id
    source        TEXT NOT NULL,
    ext_id        TEXT NOT NULL,
    url           TEXT NOT NULL,
    title         TEXT,
    kind          TEXT,                       -- Biete / Suche / Charter
    muster        TEXT,
    hersteller    TEXT,
    price         REAL,
    currency      TEXT,
    price_eur     REAL,
    price_text    TEXT,
    year          INTEGER,
    hours         REAL,
    location      TEXT,
    image         TEXT,
    snippet       TEXT,
    description   TEXT,
    details       TEXT,                       -- JSON mit allen Datenfeldern der Detailseite
    published     TEXT,
    detail_fetched INTEGER DEFAULT 0,
    alarm         INTEGER DEFAULT 0,
    alarm_terms   TEXT,
    first_seen    TEXT NOT NULL,
    last_seen     TEXT NOT NULL,
    removed_at    TEXT,
    active        INTEGER DEFAULT 1,
    notified      INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_listings_muster ON listings(muster);
CREATE INDEX IF NOT EXISTS idx_listings_source ON listings(source);

CREATE TABLE IF NOT EXISTS price_history (
    listing_id TEXT NOT NULL REFERENCES listings(id),
    ts         TEXT NOT NULL,
    price      REAL,
    currency   TEXT,
    price_eur  REAL,
    PRIMARY KEY (listing_id, ts)
);

CREATE TABLE IF NOT EXISTS runs (
    ts        TEXT NOT NULL,
    source    TEXT NOT NULL,
    ok        INTEGER NOT NULL,
    found     INTEGER,
    new       INTEGER,
    changed   INTEGER,
    removed   INTEGER,
    error     TEXT
);
"""


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    cols = {r[1] for r in con.execute("PRAGMA table_info(listings)")}
    if "antrieb" not in cols:  # Erweiterung: Segelflugzeug / Turbo / Eigenstarter
        con.execute("ALTER TABLE listings ADD COLUMN antrieb TEXT")
    return con


def get(con, lid: str):
    return con.execute("SELECT * FROM listings WHERE id = ?", (lid,)).fetchone()


def source_count(con, source: str) -> int:
    return con.execute("SELECT COUNT(*) FROM listings WHERE source = ?", (source,)).fetchone()[0]


def insert(con, item: dict, ts: str) -> None:
    cols = [
        "id", "source", "ext_id", "url", "title", "kind", "muster", "antrieb", "hersteller", "price", "currency",
        "price_eur", "price_text", "year", "hours", "location", "image", "snippet", "description",
        "details", "published", "detail_fetched", "alarm", "alarm_terms",
    ]
    row = {c: item.get(c) for c in cols}
    if isinstance(row["details"], dict):
        row["details"] = json.dumps(row["details"], ensure_ascii=False)
    row["first_seen"] = row["last_seen"] = ts
    con.execute(
        f"INSERT INTO listings ({','.join(row)}) VALUES ({','.join('?' * len(row))})",
        list(row.values()),
    )
    add_price(con, item["id"], ts, item.get("price"), item.get("currency"), item.get("price_eur"))


def update(con, lid: str, fields: dict) -> None:
    if not fields:
        return
    fields = dict(fields)
    if isinstance(fields.get("details"), dict):
        fields["details"] = json.dumps(fields["details"], ensure_ascii=False)
    sets = ", ".join(f"{k} = ?" for k in fields)
    con.execute(f"UPDATE listings SET {sets} WHERE id = ?", [*fields.values(), lid])


def add_price(con, lid: str, ts: str, price, currency, price_eur) -> None:
    con.execute(
        "INSERT OR REPLACE INTO price_history (listing_id, ts, price, currency, price_eur) VALUES (?,?,?,?,?)",
        (lid, ts, price, currency, price_eur),
    )


def log_run(con, ts, source, ok, found=0, new=0, changed=0, removed=0, error=None) -> None:
    con.execute(
        "INSERT INTO runs (ts, source, ok, found, new, changed, removed, error) VALUES (?,?,?,?,?,?,?,?)",
        (ts, source, int(ok), found, new, changed, removed, error),
    )
