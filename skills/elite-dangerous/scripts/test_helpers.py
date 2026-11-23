import importlib.util
import io
import json
import pathlib
import os
import unittest
from urllib.error import HTTPError

MODULE_PATH = pathlib.Path(os.environ.get('ELITE_SKILL_SCRIPTS', pathlib.Path(__file__).resolve().parent)) / 'inara_profile.py'

class ProfileClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('inara_profile', MODULE_PATH)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_request_is_a_single_read_only_profile_query(self):
        request = self.module.build_request('example-secret', 'WhitelistedApp', 'CMDR Example')
        self.assertEqual(request['header']['APIkey'], 'example-secret')
        self.assertEqual(request['header']['appName'], 'WhitelistedApp')
        self.assertEqual(request['header']['commanderName'], 'CMDR Example')
        self.assertEqual(request['events'][0]['eventName'], 'getCommanderProfile')
        self.assertEqual(request['events'][0]['eventData'], {})
        self.assertEqual(len(request['events']), 1)

    def test_empty_app_name_and_empty_key_rejected(self):
        for key, app in [('', 'app'), ('key', '')]:
            with self.assertRaises(ValueError):
                self.module.build_request(key, app)

    def test_response_success_and_request_protocol(self):
        captured = {}
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, *args):
                return json.dumps({'header': {'eventStatus': 200}, 'events': [{'eventStatus': 200, 'eventData': {'commanderName': 'Example'}}]}).encode()
        def opener(request, timeout):
            captured['url'] = request.full_url
            captured['method'] = request.get_method()
            captured['body'] = json.loads(request.data)
            return Response()
        profile = self.module.fetch_profile('example-secret', 'WhitelistedApp', opener=opener)
        self.assertEqual(profile['commanderName'], 'Example')
        self.assertEqual(captured['url'], 'https://inara.cz/inapi/v1/')
        self.assertEqual(captured['method'], 'POST')
        self.assertEqual(captured['body']['events'][0]['eventName'], 'getCommanderProfile')

    def test_api_error_does_not_echo_secret(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, *args):
                return json.dumps({'header': {'eventStatus': 400, 'eventStatusText': 'example-secret'}, 'events': []}).encode()
        with self.assertRaises(self.module.InaraError) as cm:
            self.module.fetch_profile('example-secret', 'app', opener=lambda *a, **k: Response())
        self.assertNotIn('example-secret', str(cm.exception))

    def test_malformed_status_does_not_echo_secret(self):
        class Response:
            def __init__(self, payload): self.payload = payload
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, *args): return json.dumps(self.payload).encode()
        secret = 'example-secret'
        payloads = [
            {'header': {'eventStatus': [secret]}, 'events': []},
            {'header': {'eventStatus': 200}, 'events': [{'eventStatus': {secret: 'value'}}]},
            {'header': {'eventStatus': True}, 'events': []},
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(self.module.InaraError) as cm:
                    self.module.fetch_profile(secret, 'app', opener=lambda *a, **k: Response(payload))
                self.assertNotIn(secret, str(cm.exception))
                self.assertIn('malformed', str(cm.exception))

    def test_http_error_does_not_echo_response_body(self):
        def opener(request, timeout):
            raise HTTPError(request.full_url, 403, 'example-secret', {}, io.BytesIO(b'example-secret'))
        with self.assertRaises(self.module.InaraError) as cm:
            self.module.fetch_profile('example-secret', 'app', opener=opener)
        self.assertNotIn('example-secret', str(cm.exception))

    def test_http_error_body_is_closed_after_failure(self):
        body = io.BytesIO(b'error body')
        errors = []
        def opener(request, timeout):
            errors.append(HTTPError(request.full_url, 403, 'forbidden', {}, body))
            raise errors[-1]
        with self.assertRaises(self.module.InaraError):
            self.module.fetch_profile('secret', 'app', opener=opener)
        self.assertTrue(body.closed)

    def test_header_error_reported_when_events_are_absent(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, *args): return b'{"header":{"eventStatus":400,"eventStatusText":"This application has no access allowed."}}'
        with self.assertRaises(self.module.InaraError) as cm:
            self.module.fetch_profile('secret', 'app', opener=lambda *a, **k: Response())
        self.assertIn('header status 400', str(cm.exception))
        self.assertIn('application has no access', str(cm.exception))

    def test_header_error_reported_even_if_event_array_is_empty(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, *args): return b'{"header":{"eventStatus":400},"events":[]}'
        with self.assertRaises(self.module.InaraError) as cm:
            self.module.fetch_profile('secret', 'app', opener=lambda *a, **k: Response())
        self.assertIn('header status 400', str(cm.exception))

    def test_warning_preserves_message_without_api_key(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, *args):
                return json.dumps({'header': {'eventStatus': 200}, 'events': [{'eventStatus': 202, 'eventStatusText': 'Some warning example-secret', 'eventData': {'commanderName': 'Example'}}]}).encode()
        profile = self.module.fetch_profile('example-secret', 'app', opener=lambda *a, **k: Response())
        self.assertIn('Some warning', profile['_inara_warning'])
        self.assertNotIn('example-secret', profile['_inara_warning'])

    def test_no_results_and_malformed_response_are_not_success(self):
        class Response:
            def __init__(self, data): self.data = data
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, *args): return json.dumps(self.data).encode()
        for payload in ({'header': {'eventStatus': 200}, 'events': [{'eventStatus': 204}]}, {'header': {'eventStatus': 200}, 'events': []}):
            with self.assertRaises(self.module.InaraError):
                self.module.fetch_profile('key', 'app', opener=lambda *a, _p=payload, **k: Response(_p))

class CoriolisImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = MODULE_PATH.parent / 'coriolis_link.py'
        spec = importlib.util.spec_from_file_location('coriolis_link', p)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_import_url_round_trips_journal_loadout(self):
        import base64, gzip, urllib.parse
        loadout = {'event': 'Loadout', 'timestamp': '2026-01-01T00:00:00Z', 'Ship': 'python', 'ShipID': 19, 'Modules': []}
        url = self.module.make_import_url(loadout)
        parsed = urllib.parse.urlparse(url)
        self.assertEqual((parsed.scheme, parsed.netloc, parsed.path), ('https', 'coriolis.io', '/import'))
        payload = urllib.parse.parse_qs(parsed.query)['data'][0]
        decoded = json.loads(gzip.decompress(base64.urlsafe_b64decode(payload)))
        self.assertEqual(decoded, loadout)

    def test_wrong_event_rejected(self):
        with self.assertRaises(ValueError): self.module.make_import_url({'event': 'Location'})

    def test_offset_timestamp_is_not_mislabeled_utc(self):
        import contextlib, tempfile
        with tempfile.TemporaryDirectory() as root:
            event = {'event': 'Loadout', 'timestamp': '2026-01-01T12:00:00+03:00', 'Ship': 'python', 'Modules': []}
            events = [{'event': 'Fileheader', 'gameversion': '4.2.1.1'}, {'event': 'LoadGame', 'FID': 'F111'}, event]
            (pathlib.Path(root) / 'Journal.test.log').write_text(''.join(json.dumps(e) + '\n' for e in events), encoding='utf-8')
            output = io.StringIO()
            from unittest.mock import patch
            with patch('sys.argv', ['coriolis_link.py', '--journal-dir', root]), contextlib.redirect_stderr(output), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(self.module.main(), 0)
            self.assertNotIn('12:00:00+03:00 (UTC)', output.getvalue())

    def test_latest_loadout_uses_event_time_and_ship_filter(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            p = pathlib.Path(root)
            for filename, events in [('Journal.2.log', [{'event': 'Loadout', 'timestamp': '2025-01-01T00:00:00Z', 'ShipID': 1}]), ('Journal.1.log', [{'event': 'Loadout', 'timestamp': '2026-01-01T00:00:00Z', 'ShipID': 1}, {'event': 'Loadout', 'timestamp': '2026-02-01T00:00:00Z', 'ShipID': 2}])]:
                events[:0] = [{'event': 'Fileheader', 'gameversion': '4.2.1.1'}, {'event': 'LoadGame', 'FID': 'F111'}]
                (p / filename).write_text(''.join(json.dumps(e)+'\n' for e in events), encoding='utf-8')
            self.assertEqual(self.module.latest_loadout(p)['ShipID'], 2)
            self.assertEqual(self.module.latest_loadout(p, ship_id=1)['timestamp'], '2026-01-01T00:00:00Z')
            with self.assertRaises(ValueError): self.module.latest_loadout(p, ship_id=3)

    def test_equal_timestamps_in_one_journal_use_later_event(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            events = [{'event': 'Fileheader', 'gameversion': '4.2.1.1'},
                      {'event': 'LoadGame', 'FID': 'F111'},
                      {'event': 'Loadout', 'timestamp': '2026-01-01T00:00:00Z', 'ShipID': 1},
                      {'event': 'Loadout', 'timestamp': '2026-01-01T00:00:00Z', 'ShipID': 2}]
            (pathlib.Path(root) / 'Journal.1.log').write_text(''.join(json.dumps(e) + '\n' for e in events), encoding='utf-8')
            self.assertEqual(self.module.latest_loadout(root)['ShipID'], 2)

    def test_equal_timestamps_in_different_journals_are_ambiguous(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            for index in (1, 2):
                events = [{'event': 'Fileheader', 'gameversion': '4.2.1.1'},
                          {'event': 'LoadGame', 'FID': 'F111'},
                          {'event': 'Loadout', 'timestamp': '2026-01-01T00:00:00Z', 'ShipID': index}]
                (pathlib.Path(root) / f'Journal.{index}.log').write_text(''.join(json.dumps(e) + '\n' for e in events), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'ambiguous'):
                self.module.latest_loadout(root)

    def test_unknown_commander_loadout_is_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            events = [{'event': 'Fileheader', 'gameversion': '4.2.1.1'},
                      {'event': 'Loadout', 'timestamp': '2026-01-01T00:00:00Z', 'ShipID': 1}]
            (pathlib.Path(root) / 'Journal.1.log').write_text(''.join(json.dumps(e) + '\n' for e in events), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'commander identity'):
                self.module.latest_loadout(root)

    def test_unknown_game_version_is_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            events = [{'event': 'LoadGame', 'FID': 'F111'},
                      {'event': 'Loadout', 'timestamp': '2026-01-01T00:00:00Z', 'ShipID': 1}]
            (pathlib.Path(root) / 'Journal.1.log').write_text(''.join(json.dumps(e) + '\n' for e in events), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'game version'):
                self.module.latest_loadout(root)

    def test_mixed_live_and_legacy_journals_are_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            p = pathlib.Path(root)
            for index, version in [(1, '3.8.0.0'), (2, '4.2.1.1')]:
                events = [{'event': 'Fileheader', 'gameversion': version},
                          {'event': 'LoadGame', 'FID': 'F111'},
                          {'event': 'Loadout', 'timestamp': f'2026-01-0{index}T00:00:00Z', 'ShipID': 1}]
                (p / f'Journal.{index}.log').write_text(''.join(json.dumps(e) + '\n' for e in events), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'live and legacy'):
                self.module.latest_loadout(p)

    def test_mixed_commanders_with_same_ship_id_are_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            p = pathlib.Path(root)
            for index, fid in [(1, 'F111'), (2, 'F222')]:
                events = [{'event': 'Fileheader', 'gameversion': '4.2.1.1'},
                          {'event': 'LoadGame', 'FID': fid, 'Commander': f'CMDR {index}'},
                          {'event': 'Loadout', 'timestamp': f'2026-01-0{index}T00:00:00Z', 'ShipID': 1}]
                (p / f'Journal.{index}.log').write_text(''.join(json.dumps(e) + '\n' for e in events), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'multiple commanders'):
                self.module.latest_loadout(p, ship_id=1)

class CoriolisAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys
        sys.path.insert(0, str(MODULE_PATH.parent))
        spec = importlib.util.spec_from_file_location('coriolis_api', MODULE_PATH.parent / 'coriolis_api.py')
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_read_only_get_uses_correct_endpoint_and_bearer(self):
        seen = {}
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, *args): return b'{"ship": "python"}'
        def opener(request, timeout):
            seen.update(url=request.full_url, method=request.get_method(), auth=request.get_header('Authorization'))
            return Response()
        result = self.module.fetch_build('secret-example', 'Ab_123', 'slef', opener=opener)
        self.assertEqual(result, {'ship': 'python'})
        self.assertEqual(seen['url'], 'https://cmdr.coriolis.io/api/shortlink/Ab_123/slef/')
        self.assertEqual(seen['method'], 'GET')
        self.assertEqual(seen['auth'], 'Bearer secret-example')

    def test_rejects_path_and_bad_format(self):
        for key, fmt in [('../secrets', 'json'), ('valid', 'html'), ('', 'json')]:
            with self.assertRaises(ValueError): self.module.fetch_build('secret', key, fmt)

    def test_http_error_never_contains_key_or_body(self):
        def opener(request, timeout):
            raise HTTPError(request.full_url, 401, 'secret-example', {}, io.BytesIO(b'secret-example'))
        with self.assertRaises(self.module.CoriolisError) as cm:
            self.module.fetch_build('secret-example', 'Ab123', 'json', opener=opener)
        self.assertNotIn('secret-example', str(cm.exception))

    def test_http_error_body_is_closed_after_failure(self):
        body = io.BytesIO(b'error body')
        errors = []
        def opener(request, timeout):
            errors.append(HTTPError(request.full_url, 401, 'forbidden', {}, body))
            raise errors[-1]
        with self.assertRaises(self.module.CoriolisError):
            self.module.fetch_build('secret', 'Ab123', 'json', opener=opener)
        self.assertTrue(body.closed)

    def test_cloudflare_1010_is_reported_as_access_block_not_bad_key(self):
        def opener(request, timeout):
            body = json.dumps({'cloudflare_error': True, 'error_code': 1010, 'detail': 'blocked'}).encode()
            raise HTTPError(request.full_url, 403, 'forbidden', {}, io.BytesIO(body))
        with self.assertRaises(self.module.CoriolisError) as cm:
            self.module.fetch_build('secret', 'Ab123', 'json', opener=opener)
        self.assertIn('Cloudflare', str(cm.exception))
        self.assertIn('1010', str(cm.exception))

    def test_rejects_non_json_response(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, *args): return b'<html>bad gateway</html>'
        with self.assertRaises(self.module.CoriolisError):
            self.module.fetch_build('secret', 'test', 'json', opener=lambda *a, **k: Response())

if __name__ == '__main__': unittest.main()
