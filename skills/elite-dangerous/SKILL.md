---
name: elite-dangerous
description: Use when helping with Elite Dangerous, INARA or Coriolis.
license: MIT
metadata:
  author: Hakan ATAÇ (plato79)
  version: "0.1.0"
---

# Elite Dangerous

Answer Elite Dangerous questions using current sources and the commander's local state. For personalized questions, use relevant local journals and snapshots when authorized by the user. Journals, INARA's website/API and Coriolis are distinct sources, not interchangeable live feeds. Do not upload or modify the user's data automatically.

## When to use

Use for ships, builds, outfitting, engineering, materials, Guardian or Thargoid technology, exploration, exobiology, mining, trade, missions, combat, reputation, factions, stations and navigation. For general game questions, local journals and credentials are optional.

## Sources and prerequisites

- Game mechanics, patch-dependent advice and locations: use the host's available web search and page-reading tools; prefer current official Frontier sources and corroborate community guides. State game version or uncertainty where relevant. If web access is unavailable, explain the limitation rather than inventing current information.
- Windows journals are in `~/Saved Games/Frontier Developments/Elite Dangerous`. Elsewhere ask for the actual directory if not discoverable. Journals are JSON Lines in `Journal.*.log`; inspect relevant timestamped snapshots such as `Cargo.json`, `Status.json`, `ModulesInfo.json`, `ShipLocker.json`, `Backpack.json`, `NavRoute.json`, `Market.json`, `Outfitting.json` and `Shipyard.json`. Distinguish station stock files from the commander's own fleet. Local files may be stale or incomplete and aren't a complete authoritative account save. Do not upload them without explicit consent.
- INARA site: https://inara.cz/elite/ . For prices, station services and nearest-search use the actual public website/browser, not an invented API. Check buy/sell direction, stock, pad size, distance, and absolute report timestamp; stale listings are not guaranteed.
- INARA API: https://inara.cz/elite/inara-api-docs/ and https://inara.cz/elite/inara-api-devguide/ . It requires `INARA_API_KEY` and an application name actually whitelisted by INARA; use `INARA_APP_NAME` only after approval; the proposed application identity is `CMDR Insight`. Never impersonate another application. Keep the key in an environment variable or Windows user environment, never chat, logs, arguments or a skill file. The helper reads the Windows user registry if the current process has not inherited the variable. If not approved, explain the blocker; do not claim the API was connected.
- INARA `getCommanderProfile` gives basic profile/ranks/main ship, not a full inventory, fleet or loadouts API. API `set`/`add`/`del` events modify INARA and some replace entire inventories: never send them without explicit user approval. The provided client sends only one read-only `getCommanderProfile` event; no uploads. Respect INARA rate limits, cache where appropriate and never repeatedly retry.
- Coriolis: https://coriolis.io/ . Use `scripts/coriolis_link.py` to construct its import link from a journal `Loadout` without sending it anywhere. Open or share it only at the user's request: the URL encodes ship data. Alternatively use Coriolis Settings → Import with raw Loadout JSON or SLEF. Verify imported ship, modules and engineering; unknown modules can be omitted. A Coriolis import link is not an anonymous JSON API. For a build linked and synced to the user's CMDR-Coriolis account, `scripts/coriolis_api.py` uses `CORIOLIS_API_KEY` read-only to retrieve JSON/SLEF by shortlink key. The key is sourced from the environment or Windows user environment, never chat or command arguments; see `references/inara-coriolis.md`.

## Procedure

1. Identify the objective and relevant constraints: activity, game version, ship, budget, location and permits. For personal questions inspect relevant local journals and snapshots afresh, using the latest applicable commander, vehicle and timestamps; reconstruct subsequent changes and state uncertainty. Retrieve only context needed, rather than assuming full coverage or reusing stale memory. Combine with current website data for facts not present locally.
2. Select the latest `Materials` snapshot by event timestamp, then account for every later inventory-changing event, including `TechnologyBroker`, collection/discard/trade, crafting, synthesis and mission rewards. Flag unknown or unhandled changes instead of reporting stale counts as current. Separate raw, manufactured, encoded, on-foot materials and cargo; `Cargo.json` may describe an SRV rather than the ship. Hardware Diagnostic Sensor's internal key is `diagnosticsensor`. Broker events show observed unlocks, not necessarily a complete lifetime history.
3. For requirements, enumerate relevant locked variants and recipes, remove verified existing unlocks, then calculate and compare stock programmatically. Separate standard permanent unlocks from per-copy modified items; distinguish commodities from engineering materials and preserve explicit assumptions.
4. Propose a practical next action based on current location and missing prerequisites. Verify time-sensitive market and route data before suggesting travel. Label estimates, unknown holdings and gaps in history.
5. For ship builds, compare the requested loadout or Coriolis export with the relevant latest journal `Loadout`; timestamp it. If a link is requested, run the helper and give the exact generated URL, not an invented outfitting code. Importing a build does not change the ship in game.
6. When useful and legitimately configured, query the INARA profile helper. Report its freshness/limitations, distinguish HTTP errors from INARA event statuses, and never reveal the API key. If blocked, use local journals and accessible public pages instead.

## Helper commands

Resolve `scripts/` relative to this skill's directory and invoke using the host's available shell or execution tool with the actual path. The optional helpers require Python 3.11+ and its standard library; if execution is unavailable, explain the limitation and use other authorized sources.

- `python scripts/inara_profile.py --check-config` checks key and app-name presence without requests or secrets. Presence does not prove approval.
- `python scripts/inara_profile.py` makes one read-only profile request, only after `INARA_APP_NAME` is configured with the exact approved application name. `--commander NAME` is optional and must use the journal-confirmed in-game name. Never pass the key on the command line.
- `python scripts/coriolis_link.py --journal-dir <dir>` prints a locally constructed import link from the latest loadout; optional `--ship-id N` selects a journal ShipID. Use complete journals for the intended commander and game dataset; the helper checks preceding FID and game version and rejects mixed commanders or live/legacy data, but beta detection is not guaranteed. Verify the loadout before opening or sharing it. Ship IDs are not sufficient to distinguish accounts. Links expose encoded ship data when opened or shared.
- `python scripts/coriolis_api.py --check-config` checks the CORIOLIS_API_KEY presence without sending a request. `python scripts/coriolis_api.py --short-key <key> --format json` attempts to read one already linked/synced CMDR-Coriolis build; `--format slef` selects SLEF. Pass the shortlink key, never the API key; the two are distinct. Treat the shortlink as potentially sensitive. Do not invent a shortlink or infer a whole fleet from this endpoint.
- Verify helper behavior with `python scripts/test_helpers.py`.

## Pitfalls and verification

- INARA may lag the game and journals may be incomplete. Report snapshot time, subsequent changes and source; absent unlock events do not prove something is locked.
- The INARA profile API and its Frontier import do not provide a full private inventory via the API; consult the journal or the user's authenticated site view.
- The Coriolis helper only produces an import URL; check a real import before claiming rendering or engineering fidelity. Browser access may fail or require login.
- Verify arithmetic and counts with code. Give actionable advice with evidence. See `references/inara-coriolis.md` for protocol and permissions and current Guardian broker sources for detailed Guardian workflows.
