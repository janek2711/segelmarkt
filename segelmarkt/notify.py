"""Push-Benachrichtigungen ueber ntfy (https://ntfy.sh).

Umgebungsvariablen (in GitHub als Repository-Secrets hinterlegen):
  NTFY_TOPIC   – geheimer Themenname, den du in der ntfy-App abonnierst (Pflicht)
  NTFY_SERVER  – optional, Standard https://ntfy.sh
  NTFY_TOKEN   – optional, Zugangstoken (noetig fuer Anrufe mit ntfy Pro)
  NTFY_CALL    – optional, Telefonnummer (+49...) oder 'yes' fuer Anruf bei Alarm
"""
from __future__ import annotations

import os

import requests

DASHBOARD_URL = (os.environ.get("DASHBOARD_URL") or "").strip()


def _fmt_price(item: dict) -> str:
    p = item.get("price")
    if not p or p < 200:
        return item.get("price_text") or "Preis k. A."
    return f"{p:,.0f} {item.get('currency') or 'EUR'}".replace(",", ".")


def send(title: str, message: str, *, priority: int = 3, tags: list[str] | None = None,
         click: str | None = None, call: bool = False, dry_run: bool = False) -> bool:
    topic = os.environ.get("NTFY_TOPIC")
    payload = {"topic": topic, "title": title[:250], "message": message[:3900], "priority": priority}
    if tags:
        payload["tags"] = tags
    if click:
        payload["click"] = click
        payload["actions"] = [{"action": "view", "label": "Inserat öffnen", "url": click}]
        if DASHBOARD_URL:
            payload["actions"].append({"action": "view", "label": "Dashboard", "url": DASHBOARD_URL})
    number = os.environ.get("NTFY_CALL")
    if call and number:
        payload["call"] = number
    if dry_run or not topic:
        print(f"  [PUSH{' (nur Test)' if topic else ' – kein NTFY_TOPIC gesetzt'}] P{priority} {title} | {message[:120]!r}")
        return False
    headers = {}
    if os.environ.get("NTFY_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['NTFY_TOKEN']}"
    # GitHub uebergibt nicht gesetzte Variablen als leeren Text -> dann Standardserver
    server = (os.environ.get("NTFY_SERVER") or "https://ntfy.sh").strip().rstrip("/")
    try:
        r = requests.post(server, json=payload, headers=headers, timeout=20)
        if r.status_code >= 400 and "call" in payload:
            # Anruf nicht erlaubt (z. B. kein ntfy-Pro-Tarif) -> Nachricht trotzdem zustellen
            payload.pop("call")
            r = requests.post(server, json=payload, headers=headers, timeout=20)
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"  ntfy-Fehler: {e}")
        return False


def new_listing(item: dict, alarm_terms: list[str], cfg: dict, dry_run=False, watched=False) -> bool:
    muster = item.get("muster") or "Unbekanntes Muster"
    base = f"{muster} – {_fmt_price(item)}"
    lines = [item.get("title") or "", " · ".join(filter(None, [
        str(item["year"]) if item.get("year") else None,
        f"{item['hours']:.0f} h" if item.get("hours") else None,
        item.get("location"),
        item.get("source"),
    ]))]
    if alarm_terms:
        lines.insert(0, "Gefunden: " + ", ".join(alarm_terms))
        return send(f"🚨 ALARM {base}", "\n".join(lines), priority=5, tags=["rotating_light", "warning"],
                    click=item["url"], call=bool(cfg.get("anruf_bei_alarm")), dry_run=dry_run)
    return send(f"Neu: {base}", "\n".join(lines), priority=4 if watched else 3,
                tags=["airplane"] + (["star"] if watched else []), click=item["url"], dry_run=dry_run)


def price_change(item: dict, old_price: float, cfg: dict, dry_run=False) -> bool:
    new = item.get("price") or 0
    arrow = "gesenkt" if new < old_price else "erhöht"
    diff = abs(new - old_price)
    return send(
        f"Preis {arrow}: {item.get('muster') or item.get('title')}",
        f"{item.get('title')}\n{old_price:,.0f} → {new:,.0f} {item.get('currency') or 'EUR'} ({'-' if new < old_price else '+'}{diff:,.0f})\n{item.get('source')}".replace(",", "."),
        priority=3, tags=["chart_with_downwards_trend" if new < old_price else "chart_with_upwards_trend"],
        click=item["url"], dry_run=dry_run,
    )
