# 🛩️ Segelflugmarkt Monitor

Durchsucht **segelflug.de**, **flugzeugmarkt.de** (Segelflugzeuge + Motorsegler) und **soaringmarket.eu**
automatisch nach Inseraten. Alles landet in einer Datenbank mit Preisverlauf. Neue Inserate kommen als
Push-Nachricht aufs Handy. Bei **„Bruch“/„Projekt“** gibt es einen Alarm mit höchster Priorität.

```
GitHub Actions (stündlich)  ──►  Scraper (Python)  ──►  data/segelmarkt.db  (SQLite, alle Inserate + Preisverlauf)
                                      │                         │
                                      ▼                         ▼
                              ntfy  ──►  Handy-Push        docs/data.json  ──►  Dashboard (GitHub Pages)
```

## Einrichtung (einmalig, ca. 15 Minuten)

### 1. Handy: ntfy-App
1. App **ntfy** installieren ([Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy) / [iPhone](https://apps.apple.com/app/ntfy/id1625396347)).
2. Auf **+** tippen und ein Thema abonnieren. Der Name muss geheim und schwer zu erraten sein,
   z. B. `segelmarkt-7f3k9q2x`. Wer den Namen kennt, kann deine Nachrichten mitlesen.
3. Für den Alarm in den App-Einstellungen des Themas bei **Priorität „Max“** einen eigenen,
   lauten Ton einstellen. Auf Android zusätzlich „Nicht stören“ übergehen lassen.

### 2. GitHub-Repository
1. Kostenloses Konto auf github.com anlegen (falls noch keins vorhanden).
2. Neues Repository anlegen, z. B. `segelmarkt`, und alle Dateien dieses Ordners hochladen
   (inkl. `.github/`, `data/`, `docs/`).
   > **Öffentlich oder privat?** Das kostenlose GitHub Pages (Dashboard) gibt es nur für öffentliche Repositories.
   > Die gespeicherten Daten sind ohnehin öffentliche Inserate. Telefonnummern und E-Mail-Adressen der Verkäufer
   > werden vor dem Speichern entfernt. Mit GitHub Pro (ca. 4 $/Monat) geht das Ganze auch privat.
3. **Settings → Secrets and variables → Actions → Secrets → New repository secret**
   - `NTFY_TOPIC` = dein Themenname aus Schritt 1.2
4. **Settings → Secrets and variables → Actions → Variables** (optional)
   - `DASHBOARD_URL` = `https://<dein-name>.github.io/segelmarkt/`. Dann hat jede Push-Nachricht einen „Dashboard“-Knopf.
5. **Settings → Pages**: Source = *Deploy from a branch*, Branch = `main`, Ordner = `/docs` → Save.
6. **Settings → Actions → General → Workflow permissions**: *Read and write permissions* → Save.
7. **Actions → Segelflugmarkt-Suche → Run workflow**, um den ersten Lauf sofort zu starten.

Danach läuft die Suche von 6 bis 23 Uhr stündlich, nachts alle 3 Stunden.

## Anruf bei „Bruch“

ntfy kann bei einem Alarm zusätzlich **anrufen** und die Nachricht vorlesen. Das braucht ein
ntfy.sh-Konto mit einem Tarif, der Telefonanrufe enthält, und eine dort bestätigte Telefonnummer.
1. Auf ntfy.sh registrieren, Tarif mit Anrufen wählen, Telefonnummer bestätigen und Zugangstoken erstellen.
2. In GitHub die Secrets `NTFY_TOKEN` (Token) und `NTFY_CALL` (Telefonnummer `+49…` oder `yes`) anlegen.
3. In `config.json` `"anruf_bei_alarm": true` setzen.

Ohne Anruf-Tarif kommt der Alarm trotzdem als Push mit höchster Priorität.

## Einstellungen – `config.json`

| Schlüssel | Bedeutung |
|---|---|
| `alarm_begriffe` | Wörter, die einen 🚨-Alarm auslösen. Sie zählen auch als Teil eines Worts, z. B. „Bruchschaden“ oder „Restaurationsprojekt“. Verneinungen wie „unfallfrei“ oder „kein Bruch“ werden ignoriert. |
| `beobachtete_muster` | z. B. `["DG-400", "LS 8"]`. Neue Inserate dieser Muster kommen mit höherer Priorität. |
| `benachrichtigen_bei` | Push bei neuen Inseraten, bei Preisänderungen, nur für „Biete“-Inserate |
| `anruf_bei_alarm` | siehe oben |
| `quellen` | einzelne Plattformen ein- oder ausschalten |

## Dashboard

- **Muster wählen** (z. B. `DG-400`). Es zeigt den Preisverlauf, Kennzahlen und alle aktuellen Inserate im Vergleich.
- Jede Linie im Diagramm ist ein Inserat, von der Veröffentlichung bis heute. Stufen sind Preisänderungen,
  gestrichelte Linien sind verkaufte oder entfernte Inserate. Dazu kommt der Median je Monat.
- Eine Zeile anklicken öffnet Beschreibung, Datenfelder und Preishistorie.
- Mit der Status-Auswahl „inkl. verkauft/entfernt“ siehst du auch alte Preise.
- Direktlink auf ein Muster: `…/#m=DG-400`, nur Alarme: `…/#alarm=1`.

Lokal ansehen:
```
python -m http.server 8000 --directory docs
```
Dann im Browser `http://localhost:8000` öffnen.

## Lokal ausführen / testen

```
pip install -r requirements.txt
python -m segelmarkt.run --dry-run     # sucht, speichert, zeigt Push-Nachrichten nur an
python -m segelmarkt.run               # mit Push (NTFY_TOPIC als Umgebungsvariable setzen)
```

## Muster-Erkennung erweitern

Die Muster stehen in `segelmarkt/muster.py`. Varianten werden zur Musterfamilie zusammengefasst
(„DG 400/17“, „DG-400 15/17m“ → `DG-400`). Ein fehlendes Muster kannst du in `PATTERNS` ergänzen.
Beim nächsten Lauf werden alle gespeicherten Inserate neu zugeordnet.

## Hinweise

- **planecheck.com** ist nicht enthalten. Die Seite blockiert automatische Abrufe mit einer Cloudflare-Bot-Sperre,
  und diese wird bewusst nicht umgangen. Als Alternative kannst du bei Planecheck selbst einen Suchauftrag
  per E-Mail anlegen.
- Der erste Lauf je Plattform speichert alle vorhandenen Inserate still und schickt eine Zusammenfassung.
  So bekommst du nicht hunderte Nachrichten auf einmal.
- Zwischen den Abrufen liegen 1,5 Sekunden Pause, um die Plattformen zu schonen.
- Ändert eine Plattform ihr Seitenlayout, zeigt das Dashboard oben „⚠ Fehler“ bei dieser Plattform.
  Der Scraper in `segelmarkt/sources/` muss dann angepasst werden.
- Daten nur für den privaten Gebrauch. Bilder werden nicht kopiert, sondern von der Originalseite geladen.
