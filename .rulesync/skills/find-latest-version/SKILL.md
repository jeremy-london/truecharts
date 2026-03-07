---
name: find-latest-version
description: "Run and manage TrueCharts app/chart updates in this repo with .updater/update.py."
targets: ["*"]
---

# Updater Runbook (TrueCharts)

Use this skill whenever you need to update chart versions, prepare weekly update commits, or guide an AI coding agent through safe update operations in this repository.

## Core Rules
- Always run updates via `uv run .updater/update.py`.
- Prefer `--dry-run` first.
- Do not manually create version folders unless explicitly requested.
- Keep metadata in sync: `catalog.json`, `<train>/<app>/app_versions.json`, `Chart.yaml`, `ix_values.yaml`.

## Common Commands

### 1) Weekly dry-run for all configured apps
```bash
uv run .updater/update.py --dry-run
```

### 2) Run real updates for all configured apps
```bash
uv run .updater/update.py
```

### 3) Update only specific apps
```bash
uv run .updater/update.py --app sabnzbd --app ombi --dry-run
uv run .updater/update.py --app sabnzbd --app ombi
```

### 4) Force chart bump (no upstream version change required)
```bash
uv run .updater/update.py --app uptime-kuma --force-bump --dry-run
uv run .updater/update.py --app uptime-kuma --force-bump
```

## No-SHA vs SHA Behavior
- Per-app digest behavior is controlled in `.updater/config.py` with `use_digest`.
- `use_digest: False` means tag-only (no `@sha256` in generated new chart folder).
- `use_digest: True` means updater validates digest and may write `tag@sha256:...`.

If a user asks for no digest pinning for an app:
1. Set `use_digest: False` in that app config block.
2. Re-run with `--dry-run`.
3. Run real update.

## Weekly Workflow (Recommended)
1. Pull latest branch.
2. Run `uv run .updater/update.py --dry-run`.
3. Review planned updates and any warnings.
4. Execute real run (all apps or targeted `--app` list).
5. Verify with:
   - `git status`
   - spot-check updated `ix_values.yaml` tags and `Chart.yaml` appVersion.
6. Push commits.

## Agent Workflow (When delegating to coding agent)
Give the agent this sequence:
1. Run `uv run .updater/update.py --dry-run`.
2. Report proposed app updates.
3. Apply requested config changes (`use_digest`, repo/tag format, app selection).
4. Re-run dry-run.
5. Run real update with explicit `--app` or `--force-bump` flags.
6. Report created commits and changed chart versions.

## Quick Validation Checklist
- Updater exits successfully.
- New version folder created for each updated app.
- `catalog.json` latest version/app version reflects new folder.
- `<train>/<app>/app_versions.json` top entry matches new version.
- `Chart.yaml` and `ix_values.yaml` in new folder are consistent.

## Known Useful Patterns
- Traefik often uses tag prefix `v` (for example `v3.6.10`).
- Numeric tags should be quoted in YAML to avoid float coercion issues in SCALE UI.
- Use `--force-bump` when you need a new chart release without changing app version.
