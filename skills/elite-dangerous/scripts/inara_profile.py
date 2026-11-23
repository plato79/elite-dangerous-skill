"""Read-only INARA profile helper. Never prints the API key."""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

URL = 'https://inara.cz/inapi/v1/'
MAX_RESPONSE = 2_000_000

class InaraError(Exception):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def config_value(name):
    value = os.environ.get(name, '').strip()
    if value:
        return value
    if sys.platform == 'win32':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
                value, _ = winreg.QueryValueEx(key, name)
                return value.strip() if isinstance(value, str) else ''
        except (OSError, ValueError):
            return ''
    return ''

def build_request(api_key, app_name, commander_name=None):
    if not api_key or not api_key.strip() or not app_name or not app_name.strip():
        raise ValueError('INARA_API_KEY and an INARA-approved INARA_APP_NAME are required.')
    header = {'appName': app_name.strip(), 'appVersion': '0.1.0', 'isBeingDeveloped': True, 'APIkey': api_key}
    if commander_name:
        header['commanderName'] = commander_name
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    return {'header': header, 'events': [{'eventName': 'getCommanderProfile', 'eventTimestamp': timestamp, 'eventData': {}}]}

def fetch_profile(api_key, app_name, commander_name=None, opener=None):
    payload = build_request(api_key, app_name, commander_name)
    req = urllib.request.Request(URL, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                                 headers={'Content-Type': 'application/json', 'Accept': 'application/json'}, method='POST')
    opener = opener or urllib.request.build_opener(NoRedirect()).open
    try:
        with opener(req, timeout=20) as response:
            raw = response.read(MAX_RESPONSE + 1)
    except urllib.error.HTTPError as exc:
        exc.close()
        raise InaraError(f'HTTP error {exc.code}; request not retried.') from None
    except (OSError, urllib.error.URLError):
        raise InaraError('Network error; request not retried.') from None
    if len(raw) > MAX_RESPONSE:
        raise InaraError('Response exceeded size limit.')
    try:
        obj = json.loads(raw)
        header = obj['header']
        header_status = header['eventStatus']
        if type(header_status) is not int or header_status not in (200, 202, 204, 400):
            raise ValueError('Invalid header status')
        if header_status not in (200, 202):
            if header.get('eventStatusText') == 'This application has no access allowed.':
                raise InaraError(f'INARA header status {header_status}; application has no access. Request app-name approval from INARA.')
            raise InaraError(f'INARA header status {header_status}; check key and approved app name.')
        events = obj['events']
        if not isinstance(events, list) or len(events) != 1:
            raise ValueError('Unexpected event count')
        status = events[0]['eventStatus']
        if type(status) is not int or status not in (200, 202, 204, 400):
            raise ValueError('Invalid event status')
        if status == 204:
            raise InaraError('INARA returned no profile (event status 204).')
        if status not in (200, 202):
            raise InaraError(f'INARA profile event status {status}.')
        profile = events[0]['eventData']
        if not isinstance(profile, dict):
            raise ValueError('Profile is not an object')
        if header_status == 202 or status == 202:
            messages = [item.get('eventStatusText') for item in (header, events[0]) if item.get('eventStatus') == 202]
            messages = [redact(msg, api_key)[:500] for msg in messages if isinstance(msg, str) and msg]
            warning = '; '.join(messages) if messages else 'INARA returned status 202 without an explanation.'
            profile = {**profile, '_inara_warning': warning}
        return profile
    except (ValueError, KeyError, TypeError, IndexError, UnicodeDecodeError):
        raise InaraError('INARA returned a malformed or incomplete response.') from None

def redact(value, secret):
    if isinstance(value, str):
        return value.replace(secret, '[REDACTED]') if secret else value
    if isinstance(value, list):
        return [redact(v, secret) for v in value]
    if isinstance(value, dict):
        return {redact(k, secret): redact(v, secret) for k, v in value.items()}
    return value

def main():
    parser = argparse.ArgumentParser(description='Get the current user INARA profile (read-only).')
    parser.add_argument('--commander', help='Journal-confirmed in-game commander name')
    parser.add_argument('--check-config', action='store_true', help='Check configuration without making a request')
    args = parser.parse_args()
    key = config_value('INARA_API_KEY')
    app = config_value('INARA_APP_NAME')
    if args.check_config:
        print('INARA_API_KEY present:', bool(key))
        print('INARA_APP_NAME present:', bool(app))
        print('App name must be approved by INARA; presence alone does not verify approval.')
        return 0 if key and app else 2
    try:
        profile = fetch_profile(key, app, args.commander)
        print(json.dumps(redact(profile, key), ensure_ascii=False, indent=2))
        return 0
    except (InaraError, ValueError) as exc:
        print(redact(str(exc), key), file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
