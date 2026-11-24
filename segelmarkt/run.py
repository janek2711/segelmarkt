"""Ein Suchlauf ueber alle Plattformen.

    python -m segelmarkt.run              # normaler Lauf (mit Push)
    python -m segelmarkt.run --dry-run    # ohne Push, zeigt nur an, was gesendet wuerde
    python -m segelmarkt.run --only soaringmarket.eu
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback

from . import alarm, db, notify
from .export import export
from .muster import detect_muster
from .sources import flugzeugmarkt, segelflug, soaringmarket
from .util import Http, clean, load_config, now_iso, price_eur

SOURCES = [segelflug, flugzeugmarkt, soaringmarket]

# notified: 0 = noch nicht, 1 = neu gemeldet, 2 = Alarm gemeldet, 9 = Erstbefuellung (still)
SILENT = 9


def classify(item: dict) -> None:
    details = item.get("details") or {}
    hint = item.get("muster_hint") or details.get("_muster_hint")
    muster, maker = detect_muster(item.get("title"), hint)
    if not muster and hint:
        muster = clean(hint)[:40]
    item["muster"] = muster
    item["hersteller"] = item.get("hersteller_hint") or details.get("Hersteller") or maker
    item["price_eur"] = price_eur(item.get("price"), item.get("currency") or "EUR")


def merge_detail(item: dict, detail: dict) -> None:
    for k, v in detail.items():
        if v in (None, "", {}):
            continue
        if k == "details":
            item["details"] = {**(item.get("details") or {}), **v}
        else:
            item[k] = v
    d = item.setdefault("details", {})
    if item.get("muster_hint"):
        d["_muster_hint"] = item["muster_hint"]
    if item.get("condition"):
        d["_zustand"] = item["condition"]
    item["detail_fetched"] = 1


def wants_push(item: dict, cfg: dict) -> bool:
    return item.get("kind") == "Biete" or not cfg["benachrichtigen_bei"].get("nur_biete", True)


def is_watched(item: dict, cfg: dict) -> bool:
    watch = [w.lower().replace("-", "").replace(" ", "") for w in cfg.get("beobachtete_muster", [])]
    m = (item.get("muster") or "").lower().replace("-", "").replace(" ", "")
    return bool(m) and m in watch


def run_source(con, http, mod, cfg, args, budget: list[int]) -> None:
    ts = now_iso()
    name = mod.NAME
    terms = cfg["alarm_begriffe"]
    print(f"\n=== {name} ===")
    try:
        items = mod.list_items(http, cfg)
    except Exception as e:  # Plattform nicht erreichbar oder Layout geaendert
        traceback.print_exc()
        db.log_run(con, ts, name, False, error=f"{type(e).__name__}: {e}"[:500])
        con.commit()
        return
    if not items:
        db.log_run(con, ts, name, False, error="0 Inserate gefunden – Seitenlayout geändert?")
        con.commit()
        print("  WARNUNG: keine Inserate gefunden")
        return

    seeding = db.source_count(con, name) == 0
    new = changed = 0
    seed_alarms: list[dict] = []
    seen: set[str] = set()

    for it in items:
        lid = f"{name}:{it['ext_id']}"
        seen.add(lid)
        it.update(id=lid, source=name)
        row = db.get(con, lid)

        if row is None:  # ---------- neues Inserat
            if budget[0] > 0:
                budget[0] -= 1
                try:
                    merge_detail(it, mod.fetch_detail(http, it))
                except Exception as e:
                    print(f"  Detailseite fehlgeschlagen ({it['url']}): {e}")
            classify(it)
            hits = alarm.check(it, terms)
            it["alarm"] = int(bool(hits))
            it["alarm_terms"] = ", ".join(hits) or None
            db.insert(con, it, ts)
            new += 1
            print(f"  NEU {'🚨 ' if hits else ''}{it.get('muster') or '?':<16} {it.get('price_text') or '':<14} {it['title'][:60]}")
            if seeding:
                db.update(con, lid, {"notified": SILENT})
                if hits and wants_push(it, cfg):
                    seed_alarms.append(it)
            elif wants_push(it, cfg) and (hits or cfg["benachrichtigen_bei"].get("neues_inserat", True)):
                notify.new_listing(it, hits, cfg, dry_run=args.dry_run, watched=is_watched(it, cfg))
                db.update(con, lid, {"notified": 2 if hits else 1})
            continue

        # ---------- bekanntes Inserat
        upd: dict = {"last_seen": ts}
        if not row["active"]:
            upd.update(active=1, removed_at=None)
        if it.get("title") and it["title"] != row["title"] and not row["detail_fetched"]:
            upd["title"] = it["title"]
        if it.get("price") is not None and row["price"] is not None and abs(it["price"] - row["price"]) >= 1:
            pe = price_eur(it["price"], it.get("currency") or row["currency"] or "EUR")
            upd.update(price=it["price"], price_text=it.get("price_text"), currency=it.get("currency"), price_eur=pe)
            db.add_price(con, lid, ts, it["price"], it.get("currency"), pe)
            changed += 1
            full = {**dict(row), **upd}
            print(f"  PREIS {row['price']:.0f} -> {it['price']:.0f}  {row['title'][:60]}")
            if cfg["benachrichtigen_bei"].get("preisaenderung", True) and wants_push(full, cfg):
                notify.price_change(full, row["price"], cfg, dry_run=args.dry_run)
        elif it.get("price") is not None and row["price"] is None:
            upd.update(price=it["price"], price_text=it.get("price_text"),
                       price_eur=price_eur(it["price"], it.get("currency") or "EUR"))

        # Detailseite nachholen, falls beim ersten Mal das Limit erreicht war
        if not row["detail_fetched"] and budget[0] > 0:
            budget[0] -= 1
            full = {**dict(row), **it, **upd, "details": json.loads(row["details"] or "{}")}
            try:
                merge_detail(full, mod.fetch_detail(http, full))
                classify(full)
                hits = alarm.check(full, terms)
                for k in ("title", "description", "details", "published", "location", "year", "hours",
                          "muster", "hersteller", "detail_fetched"):
                    upd[k] = full.get(k)
                upd["alarm"] = int(bool(hits))
                upd["alarm_terms"] = ", ".join(hits) or None
                if hits and row["notified"] in (0, 1) and wants_push(full, cfg):
                    notify.new_listing(full, hits, cfg, dry_run=args.dry_run)
                    upd["notified"] = 2
            except Exception as e:
                print(f"  Detailseite fehlgeschlagen ({it['url']}): {e}")
        db.update(con, lid, upd)

    # nicht mehr gelistete Inserate als entfernt markieren (verkauft / geloescht)
    gone = [r["id"] for r in con.execute("SELECT id FROM listings WHERE source = ? AND active = 1", (name,)) if r["id"] not in seen]
    for lid in gone:
        db.update(con, lid, {"active": 0, "removed_at": ts})
    print(f"  {len(items)} gefunden, {new} neu, {changed} Preisänderungen, {len(gone)} entfernt")
    db.log_run(con, ts, name, True, len(items), new, changed, len(gone))
    con.commit()

    if seeding:
        msg = f"{new} Inserate erstmals gespeichert. Ab jetzt wirst du bei neuen Inseraten benachrichtigt."
        if seed_alarms:
            msg += "\n\nBereits vorhanden mit Alarm-Begriff:\n" + "\n".join(
                f"• {a.get('muster') or '?'}: {a['title'][:60]} ({a.get('alarm_terms')})" for a in seed_alarms[:15])
        notify.send(f"Segelmarkt: {name} eingerichtet", msg, priority=4 if seed_alarms else 2,
                    tags=["white_check_mark"], click=notify.DASHBOARD_URL or None, dry_run=args.dry_run)


def reclassify_all(con, terms: list[str]) -> None:
    """Muster- und Alarm-Erkennung auf alle Inserate neu anwenden (z. B. nach Aenderung von muster.py
    oder der Alarm-Begriffe). Verschickt keine Nachrichten."""
    for r in con.execute("SELECT id, title, snippet, description, details FROM listings").fetchall():
        details = json.loads(r["details"] or "{}")
        muster, _ = detect_muster(r["title"], details.get("_muster_hint"))
        if not muster and details.get("_muster_hint"):
            muster = clean(details["_muster_hint"])[:40]
        hits = alarm.check({"title": r["title"], "snippet": r["snippet"], "description": r["description"],
                            "condition": details.get("_zustand")}, terms)
        con.execute("UPDATE listings SET muster = ?, alarm = ?, alarm_terms = ? WHERE id = ?",
                    (muster, int(bool(hits)), ", ".join(hits) or None, r["id"]))
    con.commit()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="keine Push-Nachrichten senden")
    ap.add_argument("--only", help="nur diese Plattform, z. B. segelflug.de")
    ap.add_argument("--max-details", type=int, help="max. Detailseiten pro Lauf")
    ap.add_argument("--no-export", action="store_true")
    args = ap.parse_args(argv)

    cfg = load_config()
    con = db.connect()
    http = Http(cfg.get("pause_zwischen_abrufen_sekunden", 1.5))
    budget = [args.max_details if args.max_details is not None else cfg.get("max_detailabrufe_pro_lauf", 400)]
    for mod in SOURCES:
        if args.only and mod.NAME != args.only:
            continue
        if not cfg["quellen"].get(mod.NAME, True):
            continue
        run_source(con, http, mod, cfg, args, budget)
    reclassify_all(con, cfg["alarm_begriffe"])
    if not args.no_export:
        export(con)
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
