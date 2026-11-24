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
    (rf"\b304{S}(S|CZ|C|ES|MS)\b|\bGLASFL\S*{S}304|\bH{S}304", "Glasflügel 304", "HpH"),
    (r"\bTWIN\s*SHARK", "Twin Shark", "HpH"),
    (r"\bSHARK", "Shark", "HpH"),
    # --- Grob ---
    (rf"\bTWIN{S}(ASTIR|III|3)\b|\bG{S}103", "Twin Astir", "Grob"),
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


def detect_muster(*texts: str | None) -> tuple[str | None, str | None]:
    """Liefert (Muster, Hersteller). Texte werden in der gegebenen Reihenfolge geprueft."""
    for text in texts:
        if not text:
            continue
        for rx, name, maker in _COMPILED:
            m = rx.search(text)
            if m:
                return (name(m) if callable(name) else name), maker
    return None, None
