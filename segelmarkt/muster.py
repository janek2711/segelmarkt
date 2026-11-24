"""Erkennt das Flugzeugmuster (z. B. 'DG-400') aus Titel und Datenfeldern.

Varianten werden auf die Musterfamilie zusammengefasst, damit z. B.
'DG 400/17', 'DG-400 15/17m' und 'DG400' alle als 'DG-400' gefiltert werden.
Neue Muster einfach unten in PATTERNS ergaenzen (spezifischere zuerst).
"""
from __future__ import annotations

import re

S = r"[\s\-_./]*"  # flexible Trennzeichen
END = r"(?![0-9])"

# (Regex, Muster-Name oder Funktion, Hersteller)
PATTERNS: list[tuple[str, object, str]] = [
    # --- Schleicher ---
    (rf"\bAS{S}K{S}(13|14|16|18|21|23){END}", lambda m: f"ASK {m.group(1)}", "Schleicher"),
    (rf"\bAS{S}W{S}(12|15|17|19|20|22|24|27|28){END}", lambda m: f"ASW {m.group(1)}", "Schleicher"),
    (rf"\bAS{S}H{S}(25|26|30|31){END}", lambda m: f"ASH {m.group(1)}", "Schleicher"),
    (rf"\bAS{S}G{S}(29|32){END}", lambda m: f"ASG {m.group(1)}", "Schleicher"),
    (rf"\bAS{S}(33|34){END}", lambda m: f"AS {m.group(1)}", "Schleicher"),
    (r"\bRH(Ö|OE|O)NLERCHE", "Ka 4", "Schleicher"),
    (rf"\bKA?{S}(2|4|6|7|8){END}(?![.,]\d)", lambda m: f"Ka {m.group(1)}", "Schleicher"),
    # --- DG / Glaser-Dirks / Rolladen-Schneider ---
    (rf"\bDG{S}(1000|1001|100|101|200|202|300|303|400|500|505|600|800|808|1100){END}",
     lambda m: "DG-" + {"1001": "1000", "101": "100", "202": "200", "303": "300", "505": "500", "808": "800"}.get(m.group(1), m.group(1)), "DG"),
    (rf"\bLS{S}(10|1|3|4|6|7|8){END}", lambda m: f"LS {m.group(1)}", "Rolladen-Schneider/DG"),
    # --- Schempp-Hirth ---
    (rf"\bDUO{S}DISCUS", "Duo Discus", "Schempp-Hirth"),
    (rf"\bDISCUS{S}2", "Discus 2", "Schempp-Hirth"),
    (r"\bDISCUS", "Discus", "Schempp-Hirth"),
    (rf"\bVENTUS{S}3", "Ventus 3", "Schempp-Hirth"),
    (rf"\bVENTUS{S}2", "Ventus 2", "Schempp-Hirth"),
    (r"\bVENTUS", "Ventus", "Schempp-Hirth"),
    (rf"\bMINI{S}NIMBUS", "Mini-Nimbus", "Schempp-Hirth"),
    (rf"\bNIMBUS{S}(2|3|4){END}", lambda m: f"Nimbus {m.group(1)}", "Schempp-Hirth"),
    (r"\bNIMBUS", "Nimbus", "Schempp-Hirth"),
    (r"\bJANUS", "Janus", "Schempp-Hirth"),
    (r"\bARCUS", "Arcus", "Schempp-Hirth"),
    (r"\bQUINTUS", "Quintus", "Schempp-Hirth"),
    (rf"\b(STD|STANDARD){S}CIRRUS", "Standard Cirrus", "Schempp-Hirth"),
    (r"\bCIRRUS", "Cirrus", "Schempp-Hirth"),
    # --- Glasfluegel / HpH ---
    (rf"\b(LIBELLE|H{S}201|H{S}301)", "Libelle", "Glasflügel"),
    (rf"\b(HORNET|H{S}206)", "Hornet", "Glasflügel"),
    (r"\bMOSQUITO", "Mosquito", "Glasflügel"),
    (r"\bKESTREL", "Kestrel", "Glasflügel"),
    (rf"\b(GLASFL\S*{S}|H{S})?604\b", "Glasflügel 604", "Glasflügel"),
    (r"\bTWIN\s*SHARK", "Twin Shark", "HpH"),
    # HpH 304 S / MS / eS = "Shark"; 304 C / CZ und das alte Glasfluegel 304 bleiben "Glasflügel 304"
    (rf"SHARK|\b304{S}(S|MS|ES)\b|HPH{S}304{S}(S|MS|ES)\b", "Shark", "HpH"),
    (rf"\b304{S}(CZ|C)\b|\bGLASFL\S*{S}304|\bH{S}304|\bHPH{S}304", "Glasflügel 304", "HpH/Glasflügel"),
    # --- Grob ---
    (rf"\bTWIN{S}(III|3)\b|\bG{S}103{S}C\b", "Twin III", "Grob"),
    (rf"\bTWIN{S}(II|2)\b|\bTWIN{S}ACRO|\bG{S}103{S}A\b", "Twin II", "Grob"),
    (rf"\bTWIN{S}ASTIR|\bTWIN{S}(I|1)\b|\bG{S}103", "Twin Astir", "Grob"),
    (rf"\bASTIR|\bG{S}102", "Astir", "Grob"),
    (rf"\bG{S}109", "Grob G 109", "Grob"),
    # --- SZD / PZL ---
    (rf"\bJUNIOR\b|\bSZD{S}51", "SZD-51 Junior", "SZD"),
    (rf"\bPUCHACZ|\bSZD{S}50", "SZD-50 Puchacz", "SZD"),
    (rf"\bPERKOZ|\bSZD{S}54", "SZD-54 Perkoz", "SZD"),
    (rf"\bJANTAR|\bSZD{S}(41|42|48)", "Jantar", "SZD"),
    (rf"\bFOKA|\bSZD{S}(24|32)", "Foka", "SZD"),
    (rf"\bPIRAT|\bSZD{S}30", "SZD-30 Pirat", "SZD"),
    (rf"\bBOCIAN|\bSZD{S}9{END}", "SZD-9 Bocian", "SZD"),
    (rf"\bDIANA|\bSZD{S}56", "Diana", "SZD"),
    (rf"\bSZD{S}55", "SZD-55", "SZD"),
    # --- LET ---
    (rf"\bSUPER{S}BLANIK|\bL{S}23{END}", "Blaník L-23", "LET"),
    (rf"\bBLAN[IÍ]K|\bL{S}13{END}", "Blaník L-13", "LET"),
    # --- weitere ---
    (rf"\bJS{S}(1|3|5){END}", lambda m: f"JS{m.group(1)}", "Jonker"),
    (rf"\bSTEMME{S}S?{S}(10|12)|\bS{S}(10|12){S}V", lambda m: f"Stemme S{m.group(1) or m.group(2)}", "Stemme"),
    (r"\bANTARES", "Antares", "Lange"),
    (r"\bTAURUS", "Taurus", "Pipistrel"),
    (r"\bSILENT", "Silent", "Alisport"),
    (rf"\bAPIS", "Apis", "Albastar"),
    (rf"\bLAK{S}(12|17|19|20){END}", lambda m: f"LAK-{m.group(1)}", "LAK"),
    (rf"\bMINI{S}LAK", "Mini-LAK", "LAK"),
    (rf"\bEB{S}(28|29){END}", lambda m: f"EB {m.group(1)}", "Binder"),
    (rf"\bPILATUS|\bB{S}4{S}PC", "Pilatus B4", "Pilatus"),
    (r"\bPEGASE", "Pégase", "Centrair"),
    (r"\bPH(O|Ö|OE)BUS", "Phoebus", "Bölkow"),
    (r"\bELFE", "Elfe", "Neukom"),
    (r"\bDIAMANT", "Diamant", "FFA"),
    (r"\bSALTO", "Salto", "Start+Flug"),
    (r"\bMISTRAL", "Mistral", "Mistral"),
    (rf"\bSB{S}5", "SB 5", "Akaflieg/Eichelsdörfer"),
    (rf"\bSF{S}(25|26|27|28|34|36){END}", lambda m: f"SF {m.group(1)}", "Scheibe"),
    (r"\bFALKE", "SF 25", "Scheibe"),
    (r"\bBERGFALKE", "Bergfalke", "Scheibe"),
    (r"\bSPATZ", "Spatz", "Scheibe"),
    (rf"\bDIMONA|\bH{S}K?{S}36", "Dimona", "Diamond"),
    (rf"\bLO{S}100", "Lo 100", "Wolf Hirth"),
    (r"\bKRANICH", "Kranich", "Focke-Wulf/Jacobs-Schweyer"),
    (rf"\bPIK{S}20", "PIK-20", "Eiriavion"),
    (r"\bCALIF", "Caproni Calif", "Caproni"),
    (rf"\bC{S}101\b", "Pégase", "Centrair"),
    (r"\bWEIHE", "Weihe", "DFS/Jacobs-Schweyer"),
    (r"\bZUGVOGEL", "Zugvogel", "Scheibe"),
    (r"\bURIBEL", "Uribel", "Aeromere/Caproni"),
    (rf"\bTST{S}(\d+)", lambda m: f"TST-{m.group(1)}", "TeST"),
    (rf"\bSZD{S}36|\bCOBRA{S}15", "SZD-36 Cobra", "SZD"),
    (rf"\bPW{S}(5|6){END}", lambda m: f"PW-{m.group(1)}", "PZL"),
    (rf"\bVSO{S}10", "VSO-10", "Orličan"),
    (rf"\bRF{S}5", "RF 5", "Sportavia"),
    (r"\bXIMANGO", "Ximango", "Aeromot"),
    (r"\bTAIFUN", "Taifun", "Valentin"),
    (r"\bCARAT", "Carat", "AMS"),
    (r"\bG(Ó|O)B(É|E)", "Góbé", "Rubik"),
    (r"\bGRUNAU", "Grunau Baby", "Schneider"),
]

_COMPILED = [(re.compile(p, re.I), name, maker) for p, name, maker in PATTERNS]


def _match(*texts: str | None):
    """(Muster-Familie, Hersteller, Text direkt hinter dem Treffer)"""
    for text in texts:
        if not text:
            continue
        for rx, name, maker in _COMPILED:
            m = rx.search(text)
            if m:
                return (name(m) if callable(name) else name), maker, text[m.end():m.end() + 20]
    return None, None, ""


def detect_muster(*texts: str | None) -> tuple[str | None, str | None]:
    """Liefert (Muster-Familie, Hersteller) ohne Antriebs-Unterscheidung."""
    name, maker, _ = _match(*texts)
    return name, maker


# ---------------------------------------------------------------------------
# Antrieb: Segelflugzeug / Turbo / Eigenstarter
# ---------------------------------------------------------------------------
SEGLER, TURBO, EIGEN = "Segelflugzeug", "Turbo", "Eigenstarter"

# Muster, die es als Segelflugzeug UND mit Motor gibt -> werden als eigene Muster getrennt,
# z. B. "Ventus 2", "Ventus 2 (Turbo)", "Ventus 2 (Eigenstarter)"
MOTOR_FAMILIES = {
    "Ventus", "Ventus 2", "Ventus 3", "Discus", "Discus 2", "Duo Discus", "Nimbus", "Nimbus 2", "Nimbus 3",
    "Nimbus 4", "Janus", "Arcus", "Quintus",
    "ASW 20", "ASW 22", "ASW 24", "ASW 27", "ASW 28", "ASG 29", "ASG 32", "ASH 25", "ASH 26", "ASH 30",
    "ASH 31", "ASK 21", "AS 33", "AS 34",
    "DG-500", "DG-600", "DG-800", "DG-1000", "LS 8", "LS 10", "JS1", "JS3", "Antares", "Shark",
    "Glasflügel 304", "Twin III", "Apis", "Silent", "LAK-17", "LAK-19", "LAK-20", "EB 28", "EB 29",
}
# Muster, die es nur mit Motor gibt -> Name bleibt, Antrieb = Eigenstarter
ALWAYS_SELF_LAUNCH = {"DG-400", "Stemme S10", "Stemme S12", "SF 25", "Grob G 109", "Dimona", "Taurus",
                      "RF 5", "Ximango", "Taifun", "Carat"}
# Schleicher: "E" heisst je nach Muster Turbo (ASG 29 E) oder Eigenstarter (ASW 22 BE)
SCHLEICHER_E_TURBO = {"ASW 27", "ASW 28", "ASG 29"}

_GLIDER_KW = re.compile(r"ohne\s+(motor|turbo|triebwerk|antrieb)|without\s+(engine|motor|turbo)|no\s+engine"
                        r"|motor\s+(ausgebaut|entfernt|removed)|pure\s+glider|reiner\s+segler", re.I)
_SELF_KW = re.compile(r"eigenstart|self[\s-]?launch|selbststart|\bSL\b", re.I)
_TURBO_KW = re.compile(r"\bturbo\b|heimkehrhilfe|sustainer|\bFES\b|\bRES\b|\bTJ\b|\bjet\b", re.I)


def _from_title(title: str) -> str | None:
    if not title:
        return None
    if _GLIDER_KW.search(title):
        return SEGLER
    s, t = bool(_SELF_KW.search(title)), bool(_TURBO_KW.search(title))
    if s and not t:
        return EIGEN
    if t and not s:
        return TURBO
    return None


_STOPWORDS = {"MIT", "NOT", "SET", "HAT", "IST", "GUT", "BIT", "ART", "OPT", "FIT", "GOT", "PUT", "CUT", "LOT",
              "NET", "SAT", "ACT", "ALT", "HOT", "OUT", "BUT", "IT", "ZUM", "IM", "AM", "UM", "VOM", "ROM", "DEM",
              "DOM", "SUM", "HAM", "RUM", "JAM", "DAM", "HIM", "AUS", "UND", "AND", "FOR", "THE", "VON", "BEI",
              "NEW", "NEU", "TO", "IN", "AN", "AB", "BIS", "PER", "PRO", "ZU", "DER", "DIE", "DAS"}


def _from_suffix(family: str, rest: str) -> str | None:
    """Wertet den Musterzusatz direkt hinter dem Namen aus: 'cxT', 'DM', 'Mi', 'BE', '-18E', 'TJ' ..."""
    m = re.match(r"^[\s\-/]*(\d{2,3})?[\s\-]*([A-Za-z]{1,3})\b", rest or "")
    if not m:
        return None
    digits, tok = m.group(1), m.group(2).upper()
    if digits and tok == "M":  # "18m" = Spannweite
        return None
    if tok in _STOPWORDS:  # normale Woerter wie "mit", "not", "im" sind kein Musterzusatz
        return None
    if tok in ("FES", "RES", "TJ", "JET", "ES", "EL"):
        return TURBO
    if family.startswith("AS"):  # Schleicher
        if "MI" in tok or tok in ("M", "ME", "TOP"):
            return EIGEN
        if tok.endswith("E"):
            return TURBO if family in SCHLEICHER_E_TURBO else EIGEN
        return None
    if family == "DG-800":
        return EIGEN if tok in ("A", "B", "C", "M", "MB") else None
    if family in ("Antares", "Arcus", "Apis", "Silent") and tok in ("E", "M"):
        return EIGEN  # elektrische / Verbrenner-Eigenstarter
    if tok in ("MS", "SL"):
        return EIGEN
    if family.startswith("LS") and tok == "E":
        return TURBO  # LS 8-e neo (FES)
    if tok.endswith("T"):
        return TURBO  # Ventus cT, 2cxT, Discus bT, DG-1000T, LS 8-t, Nimbus 3DT ...
    if tok.endswith("M"):
        return EIGEN  # Ventus 2cM, Nimbus 4DM, Janus CM, DG-1000M, DG-500M ...
    return None


def _from_fields(details: dict) -> str | None:
    d = details or {}
    # segelflug.de: Mehrfachauswahl, z. B. "Eigenstarter, Verbrenner" oder "ohne"
    mot = d.get("Motorisierung")
    if mot:
        parts = {p.strip().lower() for p in mot.split(",")}
        has_e = "eigenstarter" in parts
        has_t = bool(parts & {"turbo", "jet", "fes", "res"})
        has_o = "ohne" in parts
        if has_e + has_t + has_o == 1:
            return EIGEN if has_e else TURBO if has_t else SEGLER
    # soaringmarket.eu
    an = (d.get("Antrieb") or "").lower()
    if an:
        if "eigenstart" in an:
            return EIGEN
        if "turbo" in an or "heimkehr" in an:
            return TURBO
        if "ohne" in an:
            return SEGLER
    # flugzeugmarkt.de: Motor-Feld + Flugzeugtyp
    if "Motor" in d or "Flugzeugtyp" in d:
        motor = (d.get("Motor") or "-").strip()
        typ = (d.get("Flugzeugtyp") or "").lower()
        if motor in ("-", ""):
            return EIGEN if "motorsegler" in typ else SEGLER
        if re.search(r"\bTJ|jet|solo\s*2350", motor, re.I):
            return TURBO
        return EIGEN
    return None


def classify(title: str | None, hint: str | None = None, details: dict | None = None) -> tuple[str | None, str | None, str]:
    """Liefert (Muster, Hersteller, Antrieb). Motorvarianten bekommen einen Zusatz im Musternamen."""
    family, maker, rest = _match(title, hint)
    antrieb = _from_title(title or "")
    if antrieb is None and family in MOTOR_FAMILIES:
        antrieb = _from_suffix(family, rest)
        if antrieb is None and hint and hint != title:
            f2, _, rest2 = _match(hint)
            if f2 == family:
                antrieb = _from_suffix(family, rest2)
    if antrieb is None:
        antrieb = _from_fields(details or {})
    if family in ALWAYS_SELF_LAUNCH:
        antrieb = EIGEN
    antrieb = antrieb or SEGLER
    name = family
    if family in MOTOR_FAMILIES and antrieb != SEGLER:
        name = f"{family} ({antrieb})"
    return name, maker, antrieb
