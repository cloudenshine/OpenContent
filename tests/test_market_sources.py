"""Deterministic market-input/analysis tests. Synthetic HTML is test-only.

Real connectivity is exercised separately by scripts/acceptance_narrative.py
--live-market. Unit fixtures are never imported into production modules.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from email.message import Message
import io
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from opencontent.kernel import Kernel
from opencontent.vault import Problem, digest
from opencontent.capabilities.market import LongMarketAnalyzer, ShortMarketAnalyzer, normalize_record
from opencontent.capabilities.market_sources import (
    MAX_INPUT_BYTES, SOURCES, _NoRedirect, _fetch_public_page, parse_qimao_ranking, resolve_market_input,
)

STAMP = "2025-01-02T03:04:05+00:00"
SOURCE = "qimao-boy-hot-daily"
URL = SOURCES[SOURCE]["url"]


def records(n=3, **updates):
    return [{"title": f"Test book {i}", "rank": i, "author": f"Test author {i}", "genre": "科幻",
             "url": f"https://example.com/book/{i}", "observed_at": STAMP, **updates} for i in range(1, n + 1)]


def ranking_html(n=3):
    # Structural fixture based on the reviewed official page, with invented test titles.
    rows = []
    for i in range(1, n + 1):
        rows.append(f'''<li class="rank-list-item"><span class="rank-number">{i}</span>
        <a class="s-book-title" href="https://www.qimao.com/shuku/{i}/">Test book {i}</a>
        <span class="s-book-info"><a>Test author {i}</a><a>幻想</a><a>科幻</a><em>连载中</em><em>12.5万字</em></span>
        <span class="s-book-intro">A test introduction.</span><em class="rank-num">1.2</em><em class="rank-unit">万</em></li>''')
    return ('<html><span>基于昨日书籍热度排行</span><ul class="rank-list">' + ''.join(rows) + '</ul></html>').encode()


class Response:
    def __init__(self, body, *, url=URL, content_type="text/html", status=200, encoding=None, length=None):
        self.buffer = io.BytesIO(body)
        self.url, self.status = url, status
        self.headers = Message()
        self.headers['Content-Type'] = content_type
        if encoding:
            self.headers['Content-Encoding'] = encoding
        if length is not None:
            self.headers['Content-Length'] = length

    def __enter__(self): return self
    def __exit__(self, *args): pass
    def geturl(self): return self.url
    def read1(self, n): return self.buffer.read(n)


class MarketSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.k = Kernel(self.tmp.name)

    def resolve(self, request, task="long-scan", run="market-test"):
        return resolve_market_input(request, task, self.k, run)

    def test_import_requires_explicit_nonempty_mapping(self):
        for value in (None, {}, [], "", {"qimao": []}):
            with self.subTest(value=value):
                if value == {"qimao": []}:
                    raw, meta = self.resolve({"raw_data": value})
                    with self.assertRaises(Problem): LongMarketAnalyzer(self.k).analyze(raw, source_metadata=meta)
                else:
                    with self.assertRaises(Problem): self.resolve({"raw_data": value})
        with self.assertRaises(Problem): self.resolve({})

    def test_import_is_unverified_even_if_claimed_source_looks_live(self):
        raw, meta = self.resolve({"raw_data": {"qimao": records(source_id=SOURCE)}})
        self.assertEqual(meta['mode'], 'imported')
        self.assertEqual(meta['verification'], 'user_supplied_unverified')
        self.assertEqual(meta['sources'], [])
        self.assertEqual(raw['qimao'][0]['observed_at'], STAMP)

    def test_ambiguous_input_never_prefers_one_silently(self):
        with self.assertRaises(Problem): self.resolve({'raw_data': {'x': records()}, 'source_ids': [SOURCE]})
        with self.assertRaises(Problem): self.resolve({'source_ids': [SOURCE], 'market_source': SOURCE})

    def test_source_choice_is_fixed_and_task_specific(self):
        for ids in ([], [SOURCE, SOURCE], [1], 'qimao', ['https://127.0.0.1/'], ['qidian']):
            with self.subTest(ids=ids), patch('opencontent.capabilities.market_sources._fetch_public_page') as fetch:
                with self.assertRaises(Problem): self.resolve({'source_ids': ids})
                fetch.assert_not_called()
        with patch('opencontent.capabilities.market_sources._fetch_public_page') as fetch:
            with self.assertRaises(Problem): self.resolve({'source_ids': [SOURCE]}, task='short-scan')
            fetch.assert_not_called()

    def test_live_snapshot_preserves_origin_hash_and_observed_time(self):
        html = ranking_html()
        with patch('opencontent.capabilities.market_sources._fetch_public_page', side_effect=[b'User-agent:*\nAllow:/\n', html]), \
             patch('opencontent.capabilities.market_sources.now', return_value=STAMP):
            raw, meta = self.resolve({'source_ids': [SOURCE]})
        self.assertEqual(meta['verification'], 'retrieved_public_page')
        source = meta['sources'][0]
        self.assertEqual(source['sha256'], digest(html))
        self.assertEqual(source['url'], URL)
        self.assertEqual((self.k.vault.root / source['snapshot_path']).read_bytes(), html)
        self.assertEqual(raw['qimao'][0]['observed_at'], STAMP)
        self.assertEqual(raw['qimao'][0]['metric']['value'], 12000)

    def test_upstream_failure_and_robots_denial_never_fallback(self):
        for failure in (Problem('network timeout', 502), b'User-agent:*\nDisallow:/\n'):
            with self.subTest(failure=failure), patch('opencontent.capabilities.market_sources._fetch_public_page', side_effect=[failure]) as fetch:
                with self.assertRaises(Problem): self.resolve({'source_ids': [SOURCE]})
                self.assertEqual(fetch.call_count, 1)
        self.assertFalse(list(self.k.vault.root.glob('OpenContent/Market/**/*.md')))

    def test_partial_two_source_fetch_never_returns_a_successful_partial_scan(self):
        with patch('opencontent.capabilities.market_sources._fetch_public_page', side_effect=[b'User-agent:*\nAllow:/\n', ranking_html(), Problem('blocked', 502)]):
            with self.assertRaises(Problem): self.resolve({'source_ids': list(SOURCES)})
        self.assertFalse(list(self.k.vault.root.glob('.opencontent/runs/market-*.html')))

    def test_parser_rejects_empty_blocked_changed_and_malformed_pages(self):
        for body in (b'', b'<html>Please log in or complete captcha</html>', ranking_html(2),
                     ranking_html().replace(b'rank-list"', b'new-list"'),
                     ranking_html().replace(b'>2</span>', b'>1</span>'),
                     ranking_html().replace(b'12.5', b'NaN'),
                     ranking_html().replace(b'https://www.qimao.com/shuku/1/', b'https://127.0.0.1/'),
                     ranking_html().replace(b'1.2</em>', b'bad</em>'), b'\xff'):
            with self.subTest(body=body[:80]):
                with self.assertRaises(Problem): parse_qimao_ranking(body, SOURCE, STAMP)

    def test_parser_never_executes_embedded_scripts_or_uses_hidden_json(self):
        html = ranking_html() + b'<script>window.data={"title":"Injected book"}; throw new Error();</script>'
        parsed = parse_qimao_ranking(html, SOURCE, STAMP)
        self.assertEqual(len(parsed), 3)
        self.assertEqual(parsed[0]['title'], 'Test book 1')

    def test_parser_bounds_depth_and_bytes(self):
        for body in (b'x' * (MAX_INPUT_BYTES + 1), b'<div>' * 110 + ranking_html() + b'</div>' * 110):
            with self.assertRaises(Problem): parse_qimao_ranking(body, SOURCE, STAMP)

    def test_import_json_file_is_bounded_vault_relative_and_utf8(self):
        path = self.k.vault.root / 'market.json'
        path.write_text(json.dumps({'qimao': records()}))
        raw, meta = self.resolve({'market_input_path': 'market.json'})
        self.assertEqual(len(raw['qimao']), 3)
        self.assertEqual(meta['verification'], 'user_supplied_unverified')
        for value in ('../outside.json', '/tmp/outside.json', 'market.txt', 1):
            with self.subTest(value=value), self.assertRaises(Problem): self.resolve({'market_input_path': value})
        path.write_text('{bad')
        with self.assertRaises(Problem): self.resolve({'market_input_path': 'market.json'})

    def test_import_rejects_symlink_hardlink_and_nonregular_file(self):
        path = self.k.vault.root / 'target.json'
        path.write_text('{}')
        alias = self.k.vault.root / 'alias.json'
        alias.symlink_to(path)
        with self.assertRaises(Problem): self.resolve({'market_input_path': 'alias.json'})
        alias.unlink()
        os.link(path, alias)
        with self.assertRaises(Problem): self.resolve({'market_input_path': 'alias.json'})
        alias.unlink()
        if hasattr(os, 'mkfifo'):
            os.mkfifo(alias)
            with self.assertRaises(Problem): self.resolve({'market_input_path': 'alias.json'})

    def test_invalid_scan_id_is_rejected_before_fetch_or_read(self):
        for scan_id in ('', '../escape', '/tmp/x', 'bad:name', 'x' * 81, None):
            with self.subTest(scan_id=scan_id), patch('opencontent.capabilities.market_sources._fetch_public_page') as fetch:
                with self.assertRaises(Problem): self.resolve({'source_ids': [SOURCE]}, run=scan_id)
                fetch.assert_not_called()


class MarketTransportTests(unittest.TestCase):
    def fetch(self, response=None, error=None, proxies=None, addresses=None):
        opener = Mock()
        if error:
            opener.open.side_effect = error
        else:
            opener.open.return_value = response or Response(b'<html>ok</html>')
        with patch('opencontent.capabilities.market_sources.build_opener', return_value=opener), \
             patch('opencontent.capabilities.market_sources.getproxies', return_value=proxies or {}), \
             patch('opencontent.capabilities.market_sources.proxy_bypass', return_value=False), \
             patch('opencontent.capabilities.market_sources.socket.getaddrinfo', return_value=addresses or [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443))]):
            return _fetch_public_page(URL)

    def test_normal_bounded_html_response(self):
        self.assertEqual(self.fetch(), b'<html>ok</html>')

    def test_unapproved_url_never_reaches_network(self):
        for url in ('http://www.qimao.com/paihang/', 'https://localhost/', URL + '?x=1', 'https://www.qimao.com.evil.example/'):
            with self.subTest(url=url), patch('opencontent.capabilities.market_sources.build_opener') as opener:
                with self.assertRaises(Problem): _fetch_public_page(url)
                opener.assert_not_called()

    def test_direct_private_dns_rejected(self):
        for address in ('127.0.0.1', '10.1.2.3', '169.254.169.254', '::1'):
            with self.subTest(address=address), self.assertRaises(Problem):
                self.fetch(addresses=[(socket.AF_INET, socket.SOCK_STREAM, 6, '', (address, 443))])

    def test_configured_proxy_route_is_honored_without_local_dns(self):
        opener = Mock()
        opener.open.return_value = Response(b'page')
        with patch('opencontent.capabilities.market_sources.build_opener', return_value=opener), \
             patch('opencontent.capabilities.market_sources.getproxies', return_value={'https': 'http://configured-proxy:8080'}), \
             patch('opencontent.capabilities.market_sources.proxy_bypass', return_value=False), \
             patch('opencontent.capabilities.market_sources.socket.getaddrinfo', side_effect=AssertionError('Do not bypass proxy DNS')):
            self.assertEqual(_fetch_public_page(URL), b'page')

    def test_bad_status_type_size_encoding_and_redirect_fail(self):
        responses = [Response(b''), Response(b'x', status=403), Response(b'{}', content_type='application/json'),
                     Response(b'\xff'), Response(b'x', encoding='gzip'), Response(b'x', length=str(MAX_INPUT_BYTES + 1)),
                     Response(b'x', length='invalid'), Response(b'x' * (MAX_INPUT_BYTES + 1)),
                     Response(b'x', url='https://www.qimao.com/login/')]
        for response in responses:
            with self.subTest(response=response), self.assertRaises(Problem): self.fetch(response)

    def test_transport_exceptions_are_visible_problems(self):
        for error in (URLError('timeout'), TimeoutError(), HTTPError(URL, 429, 'too many requests', {}, None)):
            with self.subTest(error=error), self.assertRaises(Problem): self.fetch(error=error)

    def test_redirect_handler_never_follows_cross_host_or_login(self):
        for url in ('https://127.0.0.1/', 'https://www.qimao.com/login/', URL):
            with self.subTest(url=url), self.assertRaises(Problem):
                _NoRedirect().redirect_request(None, None, 302, '', {}, url)

    def test_wall_deadline_checked_during_body_stream(self):
        with patch('opencontent.capabilities.market_sources.time.monotonic', side_effect=[0, 21]):
            with self.assertRaises(Problem): self.fetch()


class MarketAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.k = Kernel(self.tmp.name)

    def analyze(self, rows=None, short=False, scan_id='analysis-test'):
        analyzer = ShortMarketAnalyzer(self.k) if short else LongMarketAnalyzer(self.k)
        return analyzer.analyze({'test': records(2 if short else 3) if rows is None else rows}, scan_id)

    def test_import_provenance_observation_clock_and_both_record_artifacts(self):
        for short in (False, True):
            with self.subTest(short=short):
                report = self.analyze(short=short, scan_id=f'analysis-{short}')
                self.assertEqual(report['source_metadata']['verification'], 'user_supplied_unverified')
                self.assertEqual(report['observed_at_range']['earliest'], STAMP)
                self.assertNotEqual(report['analyzed_at'], STAMP)
                self.assertNotIn('captured_at', report)
                for field in ('records_path', 'report_path', 'report_json_path'):
                    self.assertTrue((self.k.vault.root / report[field]).is_file())
                saved = json.loads((self.k.vault.root / report['records_path']).read_text())
                self.assertEqual(saved, report['records'])
                self.assertEqual(saved[0]['url'], 'https://example.com/book/1')

    def test_short_missing_annotations_do_not_invent_emotions_or_opportunities(self):
        report = self.analyze(short=True)
        self.assertEqual(report['top_emotions'], [])
        self.assertEqual(report['top_reversals'], [])
        self.assertEqual(report['opportunity_candidates'], [])
        self.assertEqual(report['field_coverage']['emotional_hook'], 0)

    def test_short_candidates_derive_only_from_supplied_annotations(self):
        report = self.analyze(records(2, emotional_hook='团圆', reversal_type='误会澄清'), short=True)
        self.assertEqual(report['top_emotions'], [('团圆', 2)])
        self.assertEqual(report['opportunity_candidates'][0]['emotion_core'], '团圆')
        self.assertIsNone(report['opportunity_candidates'][0]['shelf_life_days'])
        self.assertIsNone(report['opportunity_candidates'][0]['rescan_recommended_before'])
        self.assertEqual(report['opportunity_candidates'][0]['classification'], 'creative_hypothesis')
        self.assertIn('未知', report['opportunity_candidates'][0]['saturation_risk'])

    def test_missing_metrics_and_genre_remain_unknown(self):
        row = records()[0]
        del row['genre']
        result = normalize_record(row, 'test')
        for key in ('genre', 'words_ten_thousand', 'popularity_metric', 'status', 'intro'):
            self.assertIsNone(result[key])

    def test_invalid_record_never_coerced_into_valid_default(self):
        bad = {'title': [None, '', 123], 'rank': [None, '1', True, 0, -1, 1.2], 'url': [None, '', 'javascript:alert(1)', 'https://localhost/', 'https://user:pass@example.com/a'],
               'observed_at': [None, '', '2025-01-01', '2025-01-01T00:00:00', 'not-a-time', (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()],
               'words': ['unknown', -1, True, float('nan'), float('inf'), 10 ** 1000], 'tags': ['foo', [1]],
               'reads': ['100', -5], 'intro': [123, '\ue111']}
        for field, values in bad.items():
            for value in values:
                row = records()[0]
                row[field] = value
                with self.subTest(field=field, value=str(value)[:50]), self.assertRaises(Problem): normalize_record(row, 'test')

    def test_duplicates_cannot_inflate_quality_gate(self):
        for mutation in ('url', 'title', 'rank', 'tracking_url'):
            rows = records()
            if mutation == 'tracking_url':
                rows[1]['url'] = rows[0]['url'] + '/?utm_source=spam#fragment'
            elif mutation == 'title':
                rows[1]['title'], rows[1]['author'] = rows[0]['title'], rows[0]['author']
            else:
                rows[1][mutation] = rows[0][mutation]
            with self.subTest(mutation=mutation), self.assertRaises(Problem): self.analyze(rows)
        self.assertFalse(list(self.k.vault.root.glob('OpenContent/Market/**/*.md')))

    def test_every_platform_must_pass_minimum_and_every_row_must_be_valid(self):
        with self.assertRaises(Problem): LongMarketAnalyzer(self.k).analyze({'one': records(3), 'two': records(1)})
        rows = records(4)
        del rows[-1]['url']
        with self.assertRaises(Problem): self.analyze(rows)
        for rows in ([], None, {}, [1, 2, 3]):
            with self.subTest(rows=rows), self.assertRaises(Problem): LongMarketAnalyzer(self.k).analyze({'one': rows})

    def test_direct_analyzer_rejects_unsafe_run_id_before_writing(self):
        for scan_id in ('../escape', '', 'unsafe:id', 'x' * 81):
            with self.subTest(scan_id=scan_id), self.assertRaises(Problem): self.analyze(scan_id=scan_id)
        self.assertFalse(list(self.k.vault.root.glob('OpenContent/Market/**/*.md')))

    def test_metric_names_preserved_not_cross_platform_compared(self):
        rows = records()
        rows[0]['reads'] = 0
        rows[1]['likes'] = 42
        rows[2]['recommendation'] = 9
        report = self.analyze(rows)
        self.assertEqual([r['metric']['name'] for r in report['records']], ['reads', 'likes', 'recommendation'])
        self.assertEqual(report['records'][0]['popularity_metric'], 0)
        self.assertNotIn('total_popularity', report)


if __name__ == '__main__':
    unittest.main()
