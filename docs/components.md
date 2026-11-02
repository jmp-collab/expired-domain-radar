# Komponentenpruefung vom 02.11.2026

Read-only-Review von Repository-Metadaten, Lizenzdateien, Kerncode/README und
Teststruktur. Kein fremder Code wurde ausgefuehrt. Kein vollstaendiger Security-
Audit und keine Behauptung, dass Upstream-Tests hier ausgefuehrt wurden.
Exakte abgefragte Revisionen: `upstream-audit.json`.

| Komponente / eindeutig geprueftes Repo | Lizenzbefund | Qualitaet und Entscheidung |
|---|---|---|
| [Common Crawl MCP](https://github.com/arturseo-geo/mcp-common-crawl) | LICENSE nennt MIT; GitHub meldet NOASSERTION. Gewaehrleistungstext ist gegenueber Standard-MIT verkuerzt. | Nicht einbinden: hart codierte 2025-Indizes; Fehler werden zu leeren Ergebnissen; DNS/HTTP-Fehler werden als expired behandelt. `discover_backlinks` fragt `*.target` ab und verwirft danach URLs, die target enthalten. Das entdeckt keine eingehenden Links. Eigener schlanker CDX-Historienadapter statt MCP-Runtime. |
| [Domain-Hunter](https://github.com/WhiteBite/Domain-Hunter) | MIT | Aktives Svelte/TS-Projekt mit CLI, RDAP-, Rate-Limiter-, Schema- und E2E-Tests im Baum. Sinnvolle Trennung von high/low trust und DNS-Gegenprobe. Bei trusted RDAP 404 kann ein DNS-Fehler dennoch available ergeben; fuer unseren Alert zu schwach. Kein kompletter UI/CLI-Stack als Abhaengigkeit; eigene strengere Registry/DNS-Pruefung. |
| [WhoisFreaks Drop Lists](https://github.com/WhoisFreaks/daily-expired-and-dropped-domains) | Keine LICENSE-Datei, API-Lizenzfeld null. README veroeffentlicht ausdruecklich eine kostenlose, maschinenlesbare Stichprobe fuer automatisierte Forschung. Keine allgemeine Open-Data-/Redistributionslizenz festgestellt. | Nur oeffentliches Dropped-Subset remote lesen; nicht spiegeln. Aktualitaet/Commit/SHA256 protokollieren. Expired-Feed ausgeschlossen, weil redemption/pending-delete keine freie Registrierung belegt. Kein kostenpflichtiger Files-API-Zugriff. Eine Drop-Liste ist kein Verfuegbarkeitsbeweis. |
| RDAP Domain Checker (unspezifischer Name) | Kein eindeutiges Original-Repo genannt. | Nicht vorgeben, ein bestimmtes Paket identifiziert zu haben. WhiteBite RDAP-Kern als konkreter Referenzcheck; zusaetzlich [jedarden/domain-check](https://github.com/jedarden/domain-check) gefunden (MIT, Go, RDAP/WHOIS/Web-Stack). Dieser Server ist fuer den stdlib-MVP unnoetig gross und wurde nicht integriert oder umfassend auditiert. Keine Installation eines beliebigen gleichnamigen Pakets. |
| [GAU](https://github.com/lc/gau) / Wayback | GAU MIT; Remote-Archivdaten haben eigene Rechte/Grenzen. | Etabliertes Go-CLI, mehrere Provider, konfigurierbare Filter, Threads/Timeouts/Retry. URL-Discovery belegt weder Backlinks noch saubere Inhalte. Fuer 10 Domains kein Go-Binary noetig: direktes, begrenztes Wayback CDX. Keine automatische OTX/URLScan-Nutzung und keine `latest`-Installation. |
| [CatchDoms MCP](https://github.com/Sambel/catchdoms-mcp) | MIT fuer die veroeffentlichte MCP-Beschreibung; keine pauschale Lizenz der aggregierten Daten. Repo enthaelt LICENSE, README, server.json, keinen vollstaendigen Backend-Code. | README bietet freien Hosted-MCP-Tier: 3 Requests/Minute, nur 10 sichtbare Namen, keine Detailabfrage. REST laut [offizieller Dokumentation](https://catchdoms.com/docs) benoetigt Pro; TF/CF und weitere relevante Daten sind eingeschraenkt. Nicht integriert: Limits und fremde Scores reichen nicht als Qualitaetsbeweis; kein Abo, kein Schluessel, keine Umgehung. |

Die Bezeichnungen Common Crawl MCP und RDAP Domain Checker sind nicht eindeutig.
Die Tabelle dokumentiert die ausgewaehlten konkreten Treffer statt stillschweigend
alle gleichnamigen Projekte gleichzusetzen. Source-Audit ist eine Momentaufnahme.

## Primaerquellen der eigenen Adapter

- [Common Crawl CDXJ](https://www.commoncrawl.org/cdxj-index): URL-Capture-Metadaten;
  dies ist kein Reverse-Backlink-Index.
- [Common Crawl FAQ](https://blog.commoncrawl.org/faq): CDX stark rate-limitiert.
- [Wayback CDX API](https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server):
  Filter, collapse und Ergebnisgrenzen.
- [IANA RDAP Bootstrap](https://data.iana.org/rdap/dns.json): Registry-Endpunkte.
- [Google DNS JSON API](https://developers.google.com/speed/public-dns/docs/doh/json):
  DNS-Status, NXDOMAIN als Zusatzsignal, kein Registrierungsnachweis.
- [GitHub Actions Abrechnung](https://docs.github.com/en/billing/concepts/product-billing/github-actions):
  Standard-Runner in oeffentlichen Repositories kostenfrei; keine grossen Runner nutzen.

Eigene Implementierung ohne kopierte Upstream-Module; daher keine vendorten
MIT-Copyright-Bloecke erforderlich. Bei spaeterer Codeuebernahme muessen die
jeweiligen Lizenz- und Copyright-Texte erhalten bleiben.
