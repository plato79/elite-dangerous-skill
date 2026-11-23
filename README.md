# CMDR Insight

An unofficial, agent-independent [Agent Skills](https://agentskills.io/) package for Elite Dangerous players. It helps with ships, engineering, materials, Guardian technology, exploration, trade, and other activities using public sources and, with the player's permission, local journals and snapshots.

The skill also includes optional, read-only helpers for INARA profiles and CMDR-Coriolis builds, plus a local Coriolis import-link generator. These integrations have important limits described below; local game data is never automatically uploaded.

## Install

The portable skill is the entire [`skills/elite-dangerous`](skills/elite-dangerous/) directory, not just `SKILL.md`. It follows the open Agent Skills format and is intended for skills-compatible agents, including Claude Code, Codex, and Hermes. Installation paths, available tools, permissions and invocation vary by host; compatibility with every agent or sandbox is not guaranteed.

With Node.js installed, the open Skills CLI can install it for multiple agents. For example, from the project where you want the skill:

```sh
npx --yes skills add plato79/elite-dangerous-skill --skill elite-dangerous --agent codex claude-code --copy --yes
```

This example installs project-scoped copies for Codex and Claude Code. For other supported agents, omit `--agent codex claude-code` and `--yes` to choose interactively, or follow your host's instructions. Review third-party skills before installing them.

Alternatively, install manually. Clone the repository:

```sh
git clone https://github.com/plato79/elite-dangerous-skill.git
cd elite-dangerous-skill
```

Copy `skills/elite-dangerous` in full, including `scripts/` and `references/`, to your host's skills directory. Examples of personal locations:

- [Codex](https://developers.openai.com/codex/skills/): `~/.agents/skills/elite-dangerous`
- [Claude Code](https://code.claude.com/docs/en/skills): `~/.claude/skills/elite-dangerous`
- [Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills): your active profile's skills directory; use its documentation for the correct location.
- Other agents: follow the host's documentation for installing an Agent Skills folder. If it does not support skills, you can provide `SKILL.md` and the companion files as context manually, subject to its capabilities.

For example, on macOS/Linux from the cloned repository (choose the host you use; back up or remove an existing destination before copying):

```sh
# Codex
mkdir -p ~/.agents/skills
cp -R skills/elite-dangerous ~/.agents/skills/

# Claude Code
mkdir -p ~/.claude/skills
cp -R skills/elite-dangerous ~/.claude/skills/
```

On Windows, copy the folder using File Explorer to the equivalent location under your user profile. Restart or refresh your agent if needed, then ask it to use `elite-dangerous`. Local journals, shell execution, browsing and network requests work only if the host provides and permits them; the skill's general advice does not require all these capabilities.

If your host runs tools inside a sandbox or container, explicitly grant access to the journal directory and pass through only the environment variables needed for the optional integrations. Consult your host's security documentation; variables set on the host may not automatically reach the sandbox. On macOS/Linux, use `python3` if `python` is unavailable.

## Data sources and privacy

- Windows journals are normally under `~/Saved Games/Frontier Developments/Elite Dangerous`. On other platforms supply the journal directory. Local snapshots can be stale, incomplete, or specific to a vehicle; the agent should report timestamps and gaps.
- API keys are optional for general advice and local journal analysis. Supply secrets privately through environment variables, never in chat, command arguments, repository files, or issue reports. On Windows the helpers also read the current user's persistent environment.
- The skill does not upload journals or modify INARA/Coriolis accounts automatically. A generated Coriolis import URL encodes the ship loadout; opening or sharing it exposes that data. Check imported modules and engineering, as compatibility and rendering have not been verified end-to-end here.
- INARA's API does not expose a full private inventory or fleet export, or its market/station datasets. Use local journals and suitable current website data with their source and freshness.

## INARA setup and approval

1. Create your personal INARA API key in [INARA settings](https://inara.cz/elite/cmdr-settings-api/) and set it privately as `INARA_API_KEY`.
2. This project's proposed application name is exactly `CMDR Insight`. INARA must approve the application name before API access works; approval is **not yet confirmed**. The maintainer must contact INARA as described in the [developer guide](https://inara.cz/elite/inara-api-devguide/).
3. Once INARA approves that exact name, set `INARA_APP_NAME` to it. Do not impersonate another application. Verify availability without revealing secrets:

```sh
python skills/elite-dangerous/scripts/inara_profile.py --check-config
```

Run the examples in this README from the cloned repository root, or substitute the installed skill's actual path. When configured and approved, `python skills/elite-dangerous/scripts/inara_profile.py` sends a single read-only `getCommanderProfile` request. An HTTP 200 response can still contain an INARA error status; an app-denied response does not establish that the personal key is invalid.

## Coriolis

`python skills/elite-dangerous/scripts/coriolis_link.py --journal-dir <journal-directory>` generates a local import link from the most recent timestamped `Loadout`. Nothing is uploaded by that command. Use `--ship-id` to select a particular ship. The helper requires complete journals with a preceding commander FID and game version, and rejects mixed commanders or live/legacy datasets. Supply journals for the intended commander and game dataset only; beta detection is not guaranteed. Verify the resulting loadout before opening or sharing it. Ship IDs alone do not identify an account.

The separate `coriolis_api.py` helper reads one previously linked and synced CMDR-Coriolis build by shortlink key, using `CORIOLIS_API_KEY`. Its behavior is covered by offline tests, but a live request was blocked by Cloudflare during development; live retrieval and key validity have not been verified. See [the integration reference](skills/elite-dangerous/references/inara-coriolis.md) for prerequisites and limitations.

## Tests

Python 3.11 or newer; no third-party dependencies:

```sh
python skills/elite-dangerous/scripts/test_helpers.py
```

The tests use mock responses and synthetic loadouts; they do not contact either API.

## License and attribution

MIT. This is a community project and is not affiliated with Frontier Developments, INARA, Coriolis, or any agent provider. Elite Dangerous, INARA, and Coriolis are their respective owners' marks.
