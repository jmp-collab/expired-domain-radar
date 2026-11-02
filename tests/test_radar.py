import json
import unittest
from unittest.mock import Mock
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
import radar

AT = datetime(2026, 11, 2, 12, tzinfo=timezone.utc)
DOMAIN = 'mopedjournal.com'
HISTORY = {'years': [2008, 2010, 2015], 'status': 'ok'}


def review():
    return {'reviewer': 'test-fixture-only', 'reviewed_at': AT.isoformat(),
            'notes': 'Fixture only. Three editorial references manually checked.',
            'history_years': HISTORY['years'], 'content_clean': True,
            'trademark_clear': True, 'topic_relevant': True,
            'referring_pages': [
                {'url': f'https://{ref}/article', 'registrable_domain': ref,
                 'target_domain': DOMAIN, 'editorial': True,
                 'verified_at': AT.isoformat(), 'context': 'A relevant editorial reference to the target.'}
                for ref in ['first.com', 'second.org', 'third.net']]}


class FakeClient:
    def __init__(self, *responses):
        self.responses = iter(responses)

    def get(self, url):
        status, body = next(self.responses)
        return status, json.dumps(body)


class RadarTests(unittest.TestCase):
    def assess(self, rev=None, status='unregistered_signal', hist=None):
        return radar.assess(DOMAIN, status, hist or HISTORY,
                            {'pages_sampled': 2}, review() if rev is None else rev, AT)

    def test_invalid_domains_rejected(self):
        for bad in ['http://x.com', 'x.com/a', '127.0.0.1', 'a.de', 'a.co.uk',
                    'foo.com\nbar.com', '-x.com', 'xn--abc.com', 'a@b.com']:
            self.assertIsNone(radar.normalize(bad), bad)
        self.assertEqual(radar.normalize(' Moped.COM. '), 'moped.com')

    def test_registry_404_needs_dns_nxdomain(self):
        c = FakeClient((404, {'errorCode': 404}), (200, {'Status': 3}))
        self.assertEqual(radar.availability(c, DOMAIN)[0], 'unregistered_signal')

    def test_verisign_empty_404_is_supported_with_dns(self):
        c = Mock()
        c.get.side_effect = [(404, ''), (200, '{"Status":3}')]
        status, evidence = radar.availability(c, DOMAIN)
        self.assertEqual(status, 'unregistered_signal')
        self.assertEqual(evidence['dns_status'], 3)

    def test_rate_limit_timeout_html_do_not_mean_available(self):
        for status, payload in [(429, {}), (403, {}), (0, None), (404, '<html>'), (200, {})]:
            self.assertEqual(radar.availability(FakeClient((status, payload)), DOMAIN)[0], 'unknown')

    def test_dns_contradiction_or_failure_blocks(self):
        for dns in [{'Status': 0, 'Answer': [{}]}, {'Status': 2}, None]:
            self.assertEqual(radar.availability(FakeClient((404, {'errorCode': 404}), (200, dns)), DOMAIN)[0], 'unknown')

    def test_registered_is_not_candidate(self):
        self.assertEqual(radar.availability(FakeClient((200, {'objectClassName': 'domain'})), DOMAIN)[0], 'registered')
        self.assertFalse(self.assess(status='registered')['eligible'])

    def test_score_transparent_and_requires_review(self):
        result = self.assess()
        self.assertEqual(result['score'], 100)
        self.assertEqual(result['score'], sum(result['components'].values()))
        self.assertTrue(result['eligible'])
        self.assertFalse(self.assess(rev={})['eligible'])

    def test_history_and_review_expiry(self):
        rev = review()
        rev['reviewed_at'] = (AT - timedelta(days=31)).isoformat()
        self.assertFalse(self.assess(rev)['eligible'])
        rev = review()
        rev['referring_pages'][0]['verified_at'] = (AT - timedelta(days=8)).isoformat()
        self.assertFalse(self.assess(rev)['eligible'])
        self.assertFalse(self.assess(hist={'years': [2020], 'status': 'ok'})['eligible'])

    def test_referrer_subdomains_do_not_inflate_count(self):
        rev = review()
        for r in rev['referring_pages']:
            r['registrable_domain'] = 'same.com'
            r['url'] = 'https://sub.same.com/article'
        self.assertFalse(self.assess(rev)['eligible'])

    def test_review_must_match_target_and_clean_content(self):
        for key in ['content_clean', 'trademark_clear', 'topic_relevant']:
            rev = review()
            rev[key] = False
            self.assertFalse(self.assess(rev)['eligible'])
        rev = review()
        rev['referring_pages'][0]['target_domain'] = 'another.com'
        self.assertFalse(self.assess(rev)['eligible'])

    def test_two_qualified_runs_and_permanent_dedup(self):
        state = {'domains': {}}
        self.assertFalse(radar.advance(state, DOMAIN, True, AT))
        self.assertFalse(radar.advance(state, DOMAIN, True, AT + timedelta(minutes=5)))
        self.assertTrue(radar.advance(state, DOMAIN, True, AT + timedelta(hours=24)))
        state['domains'][DOMAIN]['notified'] = {'url': 'fixture'}
        self.assertFalse(radar.advance(state, DOMAIN, True, AT + timedelta(hours=48)))

    def test_failure_resets_confirmation(self):
        state = {'domains': {}}
        radar.advance(state, DOMAIN, True, AT)
        radar.advance(state, DOMAIN, False, AT + timedelta(hours=12))
        self.assertFalse(radar.advance(state, DOMAIN, True, AT + timedelta(hours=24)))

    def test_future_review_rejected(self):
        rev = review()
        rev['reviewed_at'] = (AT + timedelta(hours=1)).isoformat()
        self.assertFalse(self.assess(rev)['eligible'])

    def test_feed_stale_and_unavailable_fail_closed(self):
        with self.assertRaises(RuntimeError):
            radar.collect(FakeClient((500, {})), AT)
        commit = {'sha': 'abc', 'commit': {'committer': {'date': '2020-01-01T00:00:00Z'}}}
        with self.assertRaises(RuntimeError):
            radar.collect(FakeClient((200, [commit])), AT)

    def test_history_does_not_count_foreign_urls(self):
        c = FakeClient((200, [['timestamp', 'original'], ['20080101120000', 'https://evil.com/'],
                             ['20100101120000', 'https://' + DOMAIN + '/']]))
        self.assertEqual(radar.history(c, DOMAIN)['years'], [2010])

    def test_no_network_for_unapproved_endpoints(self):
        with self.assertRaises(ValueError):
            radar.Client(delay=0).get('http://localhost/secret')

    def test_notification_reuses_closed_issue_after_state_loss(self):
        existing = {'title': '[radar] ' + DOMAIN, 'state': 'closed', 'html_url': 'fixture-existing'}
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = json.dumps([existing]).encode()
        with patch('urllib.request.urlopen', return_value=response) as request:
            self.assertEqual(radar.notify('owner/repo', DOMAIN, {}, 'fake-token'), 'fixture-existing')
            self.assertEqual(request.call_count, 1)
            self.assertEqual(request.call_args.args[0].get_method(), 'GET')

    def test_notification_posts_once_when_truly_new(self):
        def response(value):
            r = Mock()
            r.__enter__ = Mock(return_value=r)
            r.__exit__ = Mock(return_value=False)
            r.read.return_value = json.dumps(value).encode()
            return r
        with patch('urllib.request.urlopen', side_effect=[response([]), response({'html_url': 'fixture-new'})]) as request:
            self.assertEqual(radar.notify('owner/repo', DOMAIN, {'score': 100}, 'fake-token'), 'fixture-new')
            self.assertEqual(request.call_count, 2)
            self.assertEqual(request.call_args.args[0].get_method(), 'POST')

    def test_notification_search_failure_prevents_post(self):
        with patch('urllib.request.urlopen', side_effect=TimeoutError) as request:
            with self.assertRaises(TimeoutError):
                radar.notify('owner/repo', DOMAIN, {}, 'fake-token')
            self.assertEqual(request.call_count, 1)


if __name__ == '__main__':
    unittest.main()
