"""Exportiert die Datenbank nach docs/data.json fuer das Dashboard."""
from __future__ import annotations

import json
from collections import defaultdict

from . import db
from .util import ROOT, now_iso

OUT = ROOT / "docs" / "data.json"


def export(con=None) -> None:
    own = con is None
    con = con or db.connect()
    hist: dict[str, list] = defaultdict(list)
    for r in con.execute("SELECT listing_id, ts, price, currency, price_eur FROM price_history ORDER BY ts"):
        hist[r["listing_id"]].append([r["ts"][:10], r["price"], r["price_eur"]])

    listings = []
    for r in con.execute("SELECT * FROM listings ORDER BY first_seen DESC"):
        details = {k: v for k, v in json.loads(r["details"] or "{}").items()
                   if not k.startswith("_") and "einloggen" not in str(v).lower()}
        listings.append({
            "id": r["id"], "s": r["source"], "u": r["url"], "t": r["title"], "k": r["kind"],
            "m": r["muster"], "h": r["hersteller"], "p": r["price"], "c": r["currency"], "pe": r["price_eur"],
            "pt": r["price_text"], "y": r["year"], "hr": r["hours"], "l": r["location"], "img": r["image"],
            "d": r["description"] or r["snippet"], "det": details, "pub": r["published"],
            "fs": r["first_seen"], "ls": r["last_seen"], "rm": r["removed_at"], "a": r["active"],
            "al": r["alarm_terms"], "ph": hist.get(r["id"], []),
        })

    runs = {}
    for r in con.execute("SELECT * FROM runs ORDER BY ts"):
        runs[r["source"]] = {"ts": r["ts"], "ok": r["ok"], "found": r["found"], "new": r["new"], "error": r["error"]}
    last_ok = {r["source"]: r["ts"] for r in con.execute("SELECT source, MAX(ts) ts FROM runs WHERE ok = 1 GROUP BY source")}
    for s, v in runs.items():
        v["last_ok"] = last_ok.get(s)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"generated": now_iso(), "runs": runs, "listings": listings}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"\nExport: {len(listings)} Inserate -> {OUT.relative_to(ROOT)}")
    if own:
        con.close()


if __name__ == "__main__":
    export()
