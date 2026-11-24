"""Erkennt Alarm-Begriffe wie 'Bruch' oder 'Projekt' in Titel und Beschreibung.

Verneinungen werden ignoriert: 'unfallfrei', 'kein Unfall', 'ohne Bruch', 'never damaged'.
"""
from __future__ import annotations

import re

NEGATIONS = {"kein", "keine", "keinen", "keiner", "ohne", "nie", "niemals", "no", "not", "never", "without", "non", "nicht"}
CONDITION_WORDS = ("defekt", "beschädigt", "beschaedigt", "unfall", "bruch", "damaged", "projekt", "project")


def find_terms(text: str, terms: list[str]) -> list[str]:
    hits: list[str] = []
    if not text:
        return hits
    words = list(re.finditer(r"[\wäöüÄÖÜß-]+", text))
    for i, m in enumerate(words):
        w = m.group(0).lower()
        for term in terms:
            t = term.lower()
            pos = w.find(t)
            if pos < 0:
                continue
            rest = w[pos + len(t):]
            if "frei" in rest or "free" in rest:
                continue  # unfallfrei, bruchfreier, damage-free
            if w[:pos].endswith(("un", "non")):
                continue  # undamaged
            # 'damaged free', 'Unfall- und beschädigungsfrei': 'frei' in den naechsten Woertern desselben Satzes
            after = text[m.end(): words[min(len(words) - 1, i + 3)].end()] if i + 1 < len(words) else ""
            after = re.split(r"[.,!?;:\n()]", after)[0]
            if re.search(r"(frei|free)\w*\b", after, re.I):
                continue
            # bis zu 3 Woerter davor, aber nur innerhalb desselben Satzes
            before = text[words[max(0, i - 3)].start():m.start()] if i else ""
            before = re.split(r"[.!?;:\n]", before)[-1]
            prev = {w.lower() for w in re.findall(r"[\wäöüÄÖÜß-]+", before)}
            if prev & NEGATIONS:
                continue
            if m.group(0) not in hits:
                hits.append(m.group(0))
            break
    return hits


def check(item: dict, terms: list[str]) -> list[str]:
    text = "\n".join(filter(None, [item.get("title"), item.get("snippet"), item.get("description")]))
    hits = find_terms(text, terms)
    cond = (item.get("condition") or "")
    if cond and any(c in cond.lower() for c in CONDITION_WORDS) and not cond.lower().endswith("frei"):
        hits.append(f"Zustand: {cond}")
    return hits
