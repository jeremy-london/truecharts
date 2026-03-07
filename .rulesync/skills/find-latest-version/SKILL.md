---
name: find-latest-version
description: "Find the latest version of a given chart or application using semantic versioning."
targets: ["*"]
---

def find_latest_version(versions):

# Find Latest Version Skill

## Purpose
This skill provides a unified, automated way to update all app/chart versions and metadata for TrueNAS SCALE using the provided update script.


## Usage
- **Do not manually manage version folders or app_versions.json.**
- To update all installed apps and ensure version tracking is correct, run the following commands:

```
cd .updater
uv sync
cd ..
uv run .updater/update.py
```

This will:
- Discover the latest available versions for all configured apps.
- Create new version folders as needed (never overwrite existing ones).
- Update or create the correct app_versions.json for each app.
- Update Chart.yaml and related files for new versions.
- Ensure TrueNAS SCALE update detection and UI compatibility.

## Notes
- The update script automates all version and metadata management. No manual editing is required.
- Always use the update script with the uv virtual environment for consistent results.
