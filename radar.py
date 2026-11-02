"""Bounded, dependency-free research radar. Never registers or buys domains."""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT = Path(__file__).resolve().parent
FEED_REPO = 'WhoisFreaks/daily-expired-and-dropped-domains'
FEED_FILE = '0-latest-free-dropped-domains.csv'
REGISTRIES = {'com': 'https://rdap.verisign.com/com/v1/domain/',
              'net': 'https://rdap.verisign.com/net/v1/domain/'}
KEYWORDS = ('moto', 'motorcycle', 'scooter', 'moped', 'roller', 'tuning', 'motorrad')
BLOCK = ('honda', 'yamaha', 'vespa', 'lambretta', 'google', 'casino', 'pharma', 'porn')
UA = 'ExpiredDomainResearchRadar/0.1 (+https://github.com/jmp-collab/expired-domain-radar)'


def now():
    return datetime.now(timezone.utc)


def stamp(t):
    return t.isoformat()


def age_hours(value, at):
    return (at - datetime.fromisoformat(value.replace('Z', '+00:00'))).total_seconds() / 3600


def normalize(value):
    value = value.strip().lower().rstrip('.')
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.(com|net)', value):
        return None
    if value.startswith('xn--'):
        return None
    return value


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    """No arbitrary hosts, redirects, credentials, paid APIs, or retries on blocks."""
    def __init__(self, delay=1.5):
        self.delay = delay
        self.last = 0
        self.blocked = set()
        self.calls = 0

    def get(self, url):
        host = urlsplit(url).hostname
        allowed = {'api.github.com', 'raw.githubusercontent.com', 'rdap.verisign.com',
                   'dns.google', 'web.archive.org', 'index.commoncrawl.org'}
        if urlsplit(url).scheme != 'https' or host not in allowed:
            raise ValueError('Unapproved endpoint')
        if host in self.blocked or self.calls >= 90:
            return 0, None
        time.sleep(max(0, self.last + self.delay - time.monotonic()))
        self.last = time.monotonic()
        self.calls += 1
        try:
            with build_opener(NoRedirect()).open(Request(url, headers={
                'User-Agent': UA, 'Accept': 'application/json, application/rdap+json'}), timeout=8) as r:
                raw = r.read(4_000_001)
                if len(raw) > 4_000_000:
                    return 0, None
                return r.status, raw.decode('utf-8')
        except HTTPError as e:
            if e.code in (403, 429):
                self.blocked.add(host)
            raw = e.read(100_000).decode('utf-8', errors='replace')
            return e.code, raw
        except (URLError, TimeoutError, OSError, UnicodeError):
            return 0, None


def get_json(client, url):
    code, body = client.get(url)
    try:
        return code, json.loads(body)
    except (ValueError, TypeError):
        return code, None


def collect(client, at):
    """Publisher explicitly advertises this public subset for automated research.
    No dataset is vendored; pin fetched content to a recent upstream commit.
    """
    meta_url = f'https://api.github.com/repos/{FEED_REPO}/commits?' + urlencode({'path': FEED_FILE, 'per_page': 1})
    status, commits = get_json(client, meta_url)
    if status != 200 or not isinstance(commits, list) or not commits:
        raise RuntimeError('Feed provenance unavailable; no stale/local fallback')
    commit = commits[0]
    published = commit['commit']['committer']['date']
    if not 0 <= age_hours(published, at) <= 72:
        raise RuntimeError('Feed older than 72 hours or future dated')
    url = f'https://raw.githubusercontent.com/{FEED_REPO}/{commit["sha"]}/{FEED_FILE}'
    status, body = client.get(url)
    if status != 200 or not body or '<html' in body[:200].lower():
        raise RuntimeError('Feed unavailable/invalid')
    domains = sorted({d for row in csv.reader(io.StringIO(body)) if row
                      if (d := normalize(row[0]))})
    if not domains:
        raise RuntimeError('Feed has no valid supported domains')
    return domains, {'url': url, 'published_at': published,
                     'sha256': hashlib.sha256(body.encode()).hexdigest(), 'supported_rows': len(domains)}


def availability(client, domain):
    url = REGISTRIES[domain.rsplit('.', 1)[1]] + domain
    status, raw = client.get(url)
    try:
        body = json.loads(raw)
    except (TypeError, ValueError):
        body = None
    evidence = {'url': url, 'http_status': status}
    if status == 200 and isinstance(body, dict) and body.get('objectClassName') == 'domain':
        return 'registered', evidence
    # Verisign currently returns empty HTTP 404 bodies for missing domains.
    # Accept ONLY empty or RDAP JSON 404, never HTML/error pages or malformed JSON.
    valid_404 = raw == '' or isinstance(body, dict) and body.get('errorCode') == 404
    if status != 404 or not valid_404:
        return 'unknown', evidence
    code, dns = get_json(client, 'https://dns.google/resolve?' + urlencode({'name': domain, 'type': 'NS'}))
    evidence.update({'dns_http_status': code, 'dns_status': dns.get('Status') if isinstance(dns, dict) else None})
    if code == 200 and isinstance(dns, dict) and dns.get('Status') == 3:
        return 'unregistered_signal', evidence
    return 'unknown', evidence


def history(client, domain):
    url = 'https://web.archive.org/cdx/search/cdx?' + urlencode({
        'url': domain + '/*', 'output': 'json', 'filter': 'statuscode:200',
        'fl': 'timestamp,original', 'collapse': 'timestamp:4', 'limit': 50})
    status, data = get_json(client, url)
    years = set()
    if status == 200 and isinstance(data, list):
        for row in data[1:]:
            if isinstance(row, list) and len(row) == 2 and re.fullmatch(r'\d{14}', str(row[0])):
                host = urlsplit(row[1]).hostname or ''
                if host == domain or host.endswith('.' + domain):
                    year = int(row[0][:4])
                    if 1996 <= year <= now().year:
                        years.add(year)
    return {'years': sorted(years), 'url': url,
            'status': 'ok' if status == 200 and isinstance(data, list) else 'unknown'}


def common_crawl(client, domain, index):
    if not index:
        return {'status': 'unknown', 'pages_sampled': 0}
    url = index + '?' + urlencode({'url': domain + '/*', 'output': 'json', 'limit': 20, 'filter': 'status:200'})
    status, body = client.get(url)
    pages = []
    if status == 200 and body:
        try:
            for line in body.splitlines():
                entry = json.loads(line)
                host = urlsplit(entry.get('url', '')).hostname or ''
                if host == domain or host.endswith('.' + domain):
                    pages.append(entry['url'])
        except (ValueError, TypeError, KeyError):
            return {'status': 'unknown', 'pages_sampled': 0, 'url': url}
    return {'status': 'ok' if status in (200, 404) else 'unknown',
            'pages_sampled': len(pages), 'url': url}


def latest_index(client):
    status, data = get_json(client, 'https://index.commoncrawl.org/collinfo.json')
    if status == 200 and isinstance(data, list):
        for item in data:
            url = item.get('cdx-api', '')
            if re.fullmatch(r'https://index\.commoncrawl\.org/CC-MAIN-\d{4}-\d{2}-index', url):
                return url
    return None


def review_points(domain, review, hist, at):
    """Human evidence is required: CDX is not a backlink or content audit."""
    try:
        if not 0 <= age_hours(review['reviewed_at'], at) <= 720:
            return 0, 'review_missing_or_expired'
        if not review.get('reviewer', '').strip() or len(review.get('notes', '')) < 30:
            return 0, 'review_incomplete'
        if review.get('history_years') != hist['years']:
            return 0, 'history_changed_review_again'
        for key in ('content_clean', 'trademark_clear', 'topic_relevant'):
            if review.get(key) is not True:
                return 0, 'review_not_clear'
        refs = set()
        for link in review['referring_pages']:
            source = urlsplit(link['url'])
            # Restrict to distinct .com/.net/.org registrable names; no PSL guesses.
            root = link['registrable_domain']
            if not re.fullmatch(r'[a-z0-9][a-z0-9-]*\.(com|net|org)', root):
                continue
            if source.scheme != 'https' or source.username or source.port:
                continue
            if source.hostname != root and not (source.hostname or '').endswith('.' + root):
                continue
            if root == domain or link.get('target_domain') != domain or link.get('editorial') is not True:
                continue
            if not 0 <= age_hours(link['verified_at'], at) <= 168:
                continue
            if len(link.get('context', '')) < 20:
                continue
            refs.add(root)
        if len(refs) < 3:
            return 0, 'need_three_reviewed_editorial_ref_domains'
        return 50, 'review_clear'
    except (KeyError, ValueError, TypeError, AttributeError):
        return 0, 'review_missing_or_invalid'


def assess(domain, status, hist, cc, review, at):
    parts = {'availability_signal': 15 if status == 'unregistered_signal' else 0,
             'archive_years': 20 if len(hist['years']) >= 3 else 10 if len(hist['years']) >= 2 else 0,
             'common_crawl': 5 if cc.get('pages_sampled', 0) else 0,
             'niche_name': 10 if any(k in domain for k in KEYWORDS) else 0}
    points, reason = review_points(domain, review, hist, at)
    parts['reviewed_quality'] = points
    blocked = any(k in domain for k in BLOCK)
    score = sum(parts.values()) if not blocked else 0
    eligible = (not blocked and status == 'unregistered_signal' and hist['status'] == 'ok'
                and len(hist['years']) >= 3 and points == 50 and score >= 90)
    return {'score': score, 'components': parts, 'eligible': eligible,
            'reason': 'name_risk_block' if blocked else reason}


def advance(state, domain, eligible, at):
    record = state['domains'].setdefault(domain, {'first_seen': stamp(at)})
    record['last_seen'] = stamp(at)
    previous = record.get('qualified_at')
    if not eligible:
        record.pop('qualified_at', None)
        return False
    if previous is None:
        record['qualified_at'] = stamp(at)
        return False
    return 6 <= age_hours(previous, at) <= 72 and not record.get('notified')


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
    temp.replace(path)


def notify(repo, domain, result, token):
    """A stable issue title deduplicates retries, including a crash before state save."""
    import urllib.request
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ValueError('Invalid repository')
    title = f'[radar] {domain}'
    base = f'https://api.github.com/repos/{repo}/issues'
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json', 'User-Agent': UA}
    # Inspect all states, including closed alerts. Failure stops delivery, never blind POST.
    for page in range(1, 101):
        req = Request(base + f'?state=all&per_page=100&page={page}', headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            issues = json.load(response)
        for issue in issues:
            if issue.get('title') == title and 'pull_request' not in issue:
                return issue['html_url']
        if len(issues) < 100:
            break
    else:
        raise RuntimeError('Issue dedup budget exceeded')
    body = (f"Research candidate: **{domain}**; score {result['score']}/100 (heuristic).\n\n"
            'Repeated registry RDAP 404 + DNS NXDOMAIN; not a registrar purchase guarantee. '
            'Three archive years and current human review required. No purchase action.\n\n'
            'Evidence (including review):\n```json\n' + json.dumps(result, indent=2) + '\n```')
    req = Request(base, data=json.dumps({'title': title, 'body': body}).encode(), headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)['html_url']


def run(args):
    at = now()
    state_path = ROOT / 'state/radar.json'
    state = json.loads(state_path.read_text())  # Missing/corrupt state fails closed.
    if state.get('schema') != 1 or not isinstance(state.get('domains'), dict):
        raise ValueError('Invalid state schema')
    reviews = json.loads((ROOT / 'data/reviews.json').read_text())
    client = Client()
    source = {'kind': 'manual_csv'}
    if args.source == 'feed':
        domains, source = collect(client, at)
    else:
        with (ROOT / 'data/domains.csv').open(newline='', encoding='utf-8-sig') as file:
            domains = [d for row in csv.DictReader(file) if (d := normalize(row.get('domain', '')))]
    # Always retain reviewed candidates for rechecks, even after they leave the daily feed.
    domains = sorted(set(domains) | {d for key in reviews if (d := normalize(key))})
    domains = [d for d in domains if not any(k in d for k in BLOCK) and any(k in d for k in KEYWORDS)]
    # Round-robin by last check prevents a daily cap from starving later candidates.
    domains.sort(key=lambda d: (state['domains'].get(d, {}).get('last_seen', ''), d))
    domains = domains[:args.limit]
    index = latest_index(client) if domains else None
    results = []
    for domain in domains:
        status, rdap = availability(client, domain)
        hist = history(client, domain) if status == 'unregistered_signal' else {'years': [], 'status': 'not_checked'}
        cc = common_crawl(client, domain, index) if status == 'unregistered_signal' else {'status': 'not_checked'}
        assessment = assess(domain, status, hist, cc, reviews.get(domain, {}), at)
        ready = advance(state, domain, assessment['eligible'], at)
        # Expired qualification windows restart, rather than permanently disabling a domain.
        record = state['domains'][domain]
        if assessment['eligible'] and age_hours(record['qualified_at'], at) > 72:
            record['qualified_at'] = stamp(at)
        result = {'domain': domain, 'checked_at': stamp(at), 'status': status, 'rdap': rdap,
                  'history': hist, 'common_crawl': cc, **assessment, 'alert_ready': ready,
                  'review': reviews.get(domain, {})}
        results.append(result)
        if ready and args.notify:
            token = os.environ['GH_TOKEN']
            url = notify(os.environ['GITHUB_REPOSITORY'], domain, result, token)
            record['notified'] = {'at': stamp(at), 'url': url}
            save_json(state_path, state)
    out = ROOT / 'reports'
    save_json(out / 'evidence.json', {'generated_at': stamp(at), 'source': source, 'requests': client.calls,
                                     'blocked_hosts': sorted(client.blocked), 'results': results})
    out.mkdir(exist_ok=True)
    with (out / 'domains.csv').open('w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['domain', 'status', 'score', 'eligible', 'alert_ready', 'reason', 'components', 'checked_at'])
        for r in results:
            writer.writerow([r[k] if k != 'components' else json.dumps(r[k], sort_keys=True)
                             for k in ('domain', 'status', 'score', 'eligible', 'alert_ready', 'reason', 'components', 'checked_at')])
    save_json(state_path, state)
    summary = (f"Checked {len(results)} candidates; qualified {sum(r['eligible'] for r in results)}; "
               f"new alert-ready {sum(r['alert_ready'] for r in results)}.\n"
               'Score is a heuristic. Traffic, full backlink profile and registration price remain unknown.\n')
    (out / 'summary.md').write_text(summary, encoding='utf-8')
    print(summary)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=['feed', 'csv'], default='csv')
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--notify', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.limit <= 15:
        parser.error('--limit must be 1..15')
    run(args)
