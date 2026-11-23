"""Read a CMDR-Coriolis linked/synced build using a local API key."""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from inara_profile import config_value, redact, NoRedirect

MAX_RESPONSE = 2_000_000

class CoriolisError(Exception):
    pass

def fetch_build(api_key, short_key, fmt='json', opener=None):
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError('CORIOLIS_API_KEY is required.')
    if not isinstance(short_key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', short_key):
        raise ValueError('A valid shortlink key is required; pass the key only, not a URL.')
    if fmt not in ('json', 'slef'):
        raise ValueError('Format must be json or slef.')
    url = f'https://cmdr.coriolis.io/api/shortlink/{short_key}/{fmt}/'
    request = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + api_key, 'Accept': 'application/json'}, method='GET')
    opener = opener or urllib.request.build_opener(NoRedirect()).open
    try:
        with opener(request, timeout=20) as response:
            raw = response.read(MAX_RESPONSE + 1)
    except urllib.error.HTTPError as exc:
        try:
            if exc.code == 403:
                try:
                    details = json.loads(exc.read(8192))
                    if details.get('cloudflare_error') and details.get('error_code') == 1010:
                        raise CoriolisError('Cloudflare blocked this client (HTTP 403, error 1010); the API key was not validated.') from None
                except (ValueError, AttributeError, OSError):
                    pass
            raise CoriolisError(f'HTTP {exc.code}; build lookup failed. Verify the key, account link and synced build.') from None
        finally:
            exc.close()
    except (OSError, urllib.error.URLError):
        raise CoriolisError('Network error; request not retried.') from None
    if len(raw) > MAX_RESPONSE:
        raise CoriolisError('Response exceeded size limit.')
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise CoriolisError('Response was not valid JSON.') from None
    if not isinstance(result, (dict, list)):
        raise CoriolisError('Response was not a JSON object or array.')
    return result

def main():
    parser = argparse.ArgumentParser(description='Read one linked CMDR-Coriolis build; no data is uploaded.')
    parser.add_argument('--check-config', action='store_true')
    parser.add_argument('--short-key', help='Shortlink key of a build already linked/synced to CMDR-Coriolis')
    parser.add_argument('--format', choices=['json', 'slef'], default='json')
    args = parser.parse_args()
    key = config_value('CORIOLIS_API_KEY')
    if args.check_config:
        print('CORIOLIS_API_KEY present:', bool(key))
        return 0 if key else 2
    try:
        result = fetch_build(key, args.short_key, args.format)
        print(json.dumps(redact(result, key), ensure_ascii=False, indent=2))
        return 0
    except (CoriolisError, ValueError) as exc:
        print(redact(str(exc), key), file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
