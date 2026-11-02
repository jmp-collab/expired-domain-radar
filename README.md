# Expired Domain Radar MVP

Kostenfreier Forschungsradar fuer Motorrad-/Roller-/Moped-Domains. Python >=3.10,
nur Standardbibliothek. Keine API-Schluessel fuer Datenquellen, kein Kauf,
keine Gebote, keine Registrierung, kein Registrar-Zugriff.

## Start

```sh
python -m unittest discover -s tests -v
python radar.py --source feed --limit 10
# Eigene Kandidaten: data/domains.csv mit Spalte domain
python radar.py --source csv
```

GitHub: **Actions > Expired Domain Radar > Run workflow**. Der Zeitplan laeuft
taeglich um **06:23 UTC** (07:23 Paris im Winter, 08:23 im Sommer). GitHub kann
Zeitplaene verzoegern und deaktiviert inaktive oeffentliche Repos gegebenenfalls
nach 60 Tagen. Der manuelle Lauf bleibt verfuegbar.

Das neue Repository ist oeffentlich, damit Standard-Linux-Runner die kostenfreie
Public-Repository-Nutzung verwenden. Beide Workflows stoppen bei einem privaten
Repository. Es werden keine kostenpflichtigen Runner, APIs oder Abonnements
eingerichtet. Kandidaten und Reviews im Repository sind oeffentlich; keine
vertraulichen Notizen oder personenbezogenen Daten eintragen.

## Automatischer Ablauf

1. Nur den explizit frei veroeffentlichten WhoisFreaks-**Dropped**-GitHub-Feed lesen.
   Neuester Commit fuer die konkrete Datei muss hoechstens 72 Stunden alt sein;
   Download an dessen SHA gebunden. Keine Vollkopie des Datensatzes im Repo.
   Bei Fehlern kein stiller Ersatz mit alten Daten.
2. Normalisieren, deduplizieren, auf `.com`/`.net`, Nischenwoerter und Risikofilter
   begrenzen. Maximal 10 Kandidaten pro Lauf (CLI hart auf 15 begrenzt).
   Zuletzt gepruefte Kandidaten hinten anstellen; Reviews werden erneut geprueft,
   auch wenn die Domain den Tagesfeed verlaesst.
3. Registry-RDAP bei Verisign. Nur HTTP 404 mit leerem Body (aktuelles Verisign-
   Verhalten) oder RDAP-JSON `errorCode:404` **plus** DNS
   NXDOMAIN ergibt `unregistered_signal`. Fehler, HTML, 403/429, DNS-Probleme
   und widerspruechliche Delegation ergeben `unknown`. Ein Signal belegt weder
   Registrar-Verfuegbarkeit noch Standardpreis; Reservierungen bleiben moeglich.
4. Wayback CDX nach erfolgreichen Captures abfragen; verschiedene Kalenderjahre
   zaehlen. Common-Crawl-Index dynamisch ermitteln und maximal 20 URL-Eintraege
   als zusaetzliche Historienprobe lesen. Keine Backlink-Zahlen daraus erfinden.
5. CSV und komplette Evidenz als GitHub-Artefakt (7 Tage), kurze Actions Summary.
   `state/radar.json` im Git-Verlauf speichert Beobachtungen und Benachrichtigungen.

Maximal 90 Daten-Requests, mindestens 1,5 Sekunden Abstand, 8 Sekunden Timeout,
keine automatischen Redirects. Nach 403/429 wird der Host fuer den Lauf gesperrt.
Keine Proxys, Umgehungen, fremden Installationsskripte oder externen Python-Pakete.
Der Gesamtworkflow ist auf 10 Minuten begrenzt. Fehlschlaege stehen in Actions;
es gibt keine Nulltreffer- oder Routine-Issues.

## Transparenter Score (Heuristik, keine Wertermittlung)

| Komponente | Punkte | Nachweis |
|---|---:|---|
| RDAP + DNS | 15 | Unregistriert-Signal dieses Laufs |
| Wayback-Historie | 0 / 10 / 20 | <2 / 2 / >=3 verschiedene erfolgreiche Archivjahre |
| Common Crawl | 5 | Mindestens ein passender URL-Eintrag im aktuellen Index |
| Nischenname | 10 | Konfiguriertes Nischenwort im Domainnamen |
| Menschliche Due Diligence | 50 oder 0 | Alle untenstehenden Review-Pruefungen bestanden |

Namens-Risikofilter setzt den Score auf 0. Blockliste ist nur ein Grobfilter,
kein vollstaendiger Markencheck. Ein Fund wird nur qualifiziert bei Score >=90,
mindestens drei Archivjahren, positivem RDAP-/DNS-Signal und gueltigem Review.
Ein Ausfall von Common Crawl kann maximal 5 Punkte kosten; Wayback/Review/RDAP
bleiben harte Voraussetzungen. Traffic, DA/DR, komplettes Linkprofil, Spam-Anteil,
Preise und Marktwert bleiben **unbekannt**, soweit nicht separat recherchiert.

## Verifizierte Benachrichtigungen

Reine Automation kann mit diesen freien URL-Indizes keine saubere Content- und
Backlink-Pruefung ersetzen. **Der MVP automatisiert Suche und technische Checks;
der Qualitaetsnachweis benoetigt eine menschliche Freigabe in `data/reviews.json`.**
Ohne diese Freigabe gibt es absichtlich keine Kandidaten-Issues.

Vor einem Review mehrere alte und neue Snapshots auf Themenwechsel, Spam,
aktive Firma/Person und sensible Inhalte pruefen; Markenrisiken recherchieren.
Mindestens drei unabhaengige redaktionelle Verweise im Original pruefen, mit
Kontext und tatsaechlichem Ziel-Link. Nur `.com/.net/.org`-Referrer werden im MVP
gezaehlt, um ohne Public-Suffix-Liste keine unabhaengigen Domains zu erfinden.
Subdomains zaehlen nicht mehrfach. Das sind drei gepruefte Stichproben, kein
vollstaendiges Linkprofil und keine Garantie einer Google-Bewertung.

Schema: [docs/review.example.json](docs/review.example.json). Werte muessen echt
geprueft sein; Beispiel nicht in produktive Reviews kopieren. Review hoechstens
30 Tage alt, Referrer-Pruefung hoechstens 7 Tage alt, Archivjahre muessen exakt
zum aktuellen Befund passen. Dokumentierte Prueferidentitaet und Kontext sind
Pflicht. Fremde URLs werden nur dokumentiert, nicht automatisch abgerufen.

Erst **zwei vollstaendig qualifizierte Laeufe im Abstand 6 bis 72 Stunden**
erzeugen ein Issue `[radar] domain.com`. Jeder negative Check setzt die
Bestaetigung zurueck. Ein Erstlauf meldet nichts. "Neu" heisst: noch nie
benachrichtigt, unabhaengig von Feed-Reihenfolge, Schliessung eines Issues oder
spaeterer Requalifikation. State und Suche ueber offene/geschlossene Issues
verhindern doppelte Zustellung auch nach einem Absturz zwischen Issue und Commit.
Concurrency serialisiert manuelle und geplante Laeufe. Keine Emails/Telegram/
Webhooks werden konfiguriert; GitHub benachrichtigt entsprechend deinen eigenen
Watch-Einstellungen.

## Dateien und Betrieb

- `radar.py`: Collector, Quellenchecks, Score, Review-Gate, Zustand und Issues.
- `data/domains.csv`: manuelle Eingabe; `data/reviews.json`: echte Reviews.
- `state/radar.json`: dauerhafter Zustand; nicht loeschen/zuruecksetzen.
- `reports/domains.csv`, `evidence.json`, `summary.md`: Laufresultate, lokal ignoriert.
- `docs/components.md`: Repository-, Lizenz- und Qualitaetspruefung.
- `docs/upstream-audit.json`: Metadaten und Commit-SHAs des Audits.

Keine Inhalte der alten Website kopieren, keine Identitaet des Vorbesitzers
uebernehmen und keine Catch-all-Mailbox einrichten. Eine Domainentscheidung
bleibt eine gesonderte manuelle Handlung ausserhalb dieses Radars.

## Grenzen

Die freie Feed-Stichprobe hat laut Anbieter einen Tag Verzug und keine ccTLDs.
`.de` und andere TLDs werden bewusst nicht als frei eingestuft. Nischenfilter
sind in `radar.py` konfigurierbar. Archive koennen lueckenhaft oder blockiert
sein; dann bleiben Befunde unbekannt. Reviews sind menschliche attestierte
Beobachtungen, keine automatische aktuelle Live-Link-Verifikation. Der Radar
kann daher legitimerweise dauerhaft null qualifizierte Kandidaten liefern.

Die Source-Lizenzen decken keine pauschalen Rechte an archivierten Inhalten ab.
Die eigene Implementierung steht unter MIT; fremder Quellcode wurde nicht
uebernommen. Der WhoisFreaks-Feed ist als freies Forschungsangebot veroeffentlicht,
hat aber keine explizite Open-Data-Lizenz: nur remote fuer diese Recherche lesen,
keinen Feed spiegeln oder als lizenzierten eigenen Datensatz weiterverkaufen.
