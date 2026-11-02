# MVP-Verifikation am 02.11.2026

- Lokal: 19 Tests erfolgreich, Python 3.13.7, keine Zusatzpakete.
- [Erster GitHub-Testlauf](https://github.com/jmp-collab/expired-domain-radar/actions/runs/41458733949):
  19 Tests erfolgreich unter Ubuntu 24.04.
- [Echter GitHub-Feed-Lauf](https://github.com/jmp-collab/expired-domain-radar/actions/runs/41458740905):
  erfolgreich in 2m44s, 9 passende Kandidaten geprueft (Limit 10),
  0 qualifiziert, 0 neue Alerts.
  Aktueller Dropped-Feed an Upstream-Commit gebunden; Quellenhash im Artefakt.
  Registry/DNS, Archive und Common Crawl wurden live abgefragt. Unbekannte oder
  unvollstaendige Daten blieben unbekannt; es wurden keine Reviews erfunden.
  CSV/Evidenz-Artefakt und State-Commit erfolgreich erzeugt.
- Issue-Deduplikation, einmalige neue Zustellung und Abbruch bei Suchfehlern
  mit lokalen HTTP-Mocks getestet. Es wurde kein kuenstliches Test-Issue erstellt.
- Erste Workflow-Version lief erfolgreich mit gepinnten v4-Actions, meldete
  jedoch Node-20-Deprecation. Anschliessend auf gepinnte v6-Actions mit Node 24
  umgestellt. [Tests mit v6](https://github.com/jmp-collab/expired-domain-radar/actions/runs/41459362602)
  und [manueller CSV-Smoke-Test mit v6](https://github.com/jmp-collab/expired-domain-radar/actions/runs/41459364147)
  ebenfalls erfolgreich. Der CSV-Smoke-Test nutzt die leere Eingabedatei und
  bestaetigt sauberen Nulltrefferlauf und Artefakt-Upload ohne Benachrichtigung.

Ein echter Alert mit menschlich verifizierter hochwertiger Domain wurde mangels
qualifiziertem Fund nicht ausgeloest. Der taegliche Zeitplan ist aktiv; ein
automatischer Cron-Trigger laesst sich erst zu seinem Termin beobachten.
