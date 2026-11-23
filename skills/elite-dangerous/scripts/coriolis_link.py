"""Make a local Coriolis import URL from a Frontier journal Loadout event."""
import argparse
import base64
import datetime as dt
import gzip
import json
from pathlib import Path
import sys
from urllib.parse import urlencode

def latest_loadout(journal_dir, ship_id=None):
    directory = Path(journal_dir)
    if not directory.is_dir():
        raise ValueError('Journal directory does not exist.')
    best = None
    best_time = None
    best_path = None
    ambiguous = False
    skipped = 0
    commanders = set()
    game_modes = set()
    for path in sorted(directory.glob('Journal.*.log')):
        commander = None
        game_mode = None
        with path.open(encoding='utf-8-sig') as stream:
            for line in stream:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    skipped += 1
                    continue
                if isinstance(event, dict) and event.get('event') == 'Fileheader':
                    version = event.get('gameversion')
                    major = version.split('.', 1)[0] if isinstance(version, str) else ''
                    game_mode = ('live' if int(major) >= 4 else 'legacy') if major.isdigit() else None
                if isinstance(event, dict) and event.get('event') in ('LoadGame', 'Commander') and isinstance(event.get('FID'), str) and event['FID']:
                    commander = event['FID']
                if not isinstance(event, dict) or event.get('event') != 'Loadout':
                    continue
                if not commander:
                    raise ValueError('A loadout has no preceding commander identity (FID); use complete journals for one commander.')
                commanders.add(commander)
                if len(commanders) > 1:
                    raise ValueError('Journals contain loadouts from multiple commanders; use a separate directory for each commander.')
                if not game_mode:
                    raise ValueError('A loadout has no preceding recognized game version; use complete journals.')
                game_modes.add(game_mode)
                if len(game_modes) > 1:
                    raise ValueError('Journals contain live and legacy loadouts; use separate directories.')
                if ship_id is not None and event.get('ShipID') != ship_id:
                    continue
                try:
                    timestamp = dt.datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                    if timestamp.tzinfo is None:
                        raise ValueError('missing timezone')
                except (KeyError, AttributeError, ValueError):
                    skipped += 1
                    continue
                if best_time is None or timestamp > best_time:
                    best_time, best = timestamp, event
                    best_path, ambiguous = path, False
                elif timestamp == best_time:
                    if path != best_path:
                        ambiguous = True
                    else:
                        best = event
    if skipped:
        print(f'Warning: {skipped} invalid or incomplete journal lines/events were skipped.', file=sys.stderr)
    if best is None:
        raise ValueError('No matching timestamped Loadout event found in the journals.')
    if ambiguous:
        raise ValueError('Latest loadouts in different journals have equal timestamps and ambiguous ordering.')
    return best

def make_import_url(loadout):
    if not isinstance(loadout, dict) or loadout.get('event') != 'Loadout' or not loadout.get('Ship') or not isinstance(loadout.get('Modules'), list):
        raise ValueError('Input must be a journal Loadout containing Ship and Modules.')
    raw = json.dumps(loadout, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    encoded = base64.urlsafe_b64encode(gzip.compress(raw, mtime=0)).decode('ascii')
    return 'https://coriolis.io/import?' + urlencode({'data': encoded})

def main():
    parser = argparse.ArgumentParser(description='Generate a Coriolis import URL locally; no network request is made.')
    default = Path.home() / 'Saved Games' / 'Frontier Developments' / 'Elite Dangerous'
    parser.add_argument('--journal-dir', default=str(default), help='Journal directory; default is the Windows Saved Games location')
    parser.add_argument('--ship-id', type=int, help='Select a particular journal ShipID')
    args = parser.parse_args()
    try:
        loadout = latest_loadout(args.journal_dir, args.ship_id)
        url = make_import_url(loadout)
        print(f"Loadout timestamp: {loadout['timestamp']}; link encodes ship data.", file=sys.stderr)
        print(url)
        return 0
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
