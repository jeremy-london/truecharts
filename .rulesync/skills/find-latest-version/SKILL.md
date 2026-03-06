---
name: find-latest-version
description: "Find the latest version of a given chart or application using semantic versioning."
targets: ["*"]
---

# Find Latest Version Skill

## Purpose
This skill provides a method to find the latest version of a given chart or application, typically by parsing version strings and determining the highest semver-compliant version.

## Usage
- Use this skill when you need to determine the most recent version from a list of available versions.
- Can be used in automation scripts, CI pipelines, or as part of chart update workflows.

## Implementation Outline
1. **Input:** List of version strings (e.g., from a directory listing, API response, or file).
2. **Parse:** Normalize and parse the version strings, ignoring non-semver or malformed entries if needed.
3. **Compare:** Use semantic versioning rules to compare versions.
4. **Output:** Return the highest (latest) version found.
5. **TrueNAS SCALE Folder-Based Chart Versioning:**
    - When updating an app/chart, do NOT overwrite the existing version folder.
    - Instead, create a new folder named for the new chart version (e.g., 20.2.4/ for bazarr).
    - Copy all files from the previous version's folder into the new version folder.
    - Update the appVersion and version fields in the new folder's Chart.yaml to the new values.
    - This folder-based approach is required for TrueNAS SCALE to detect and offer updates in the UI.
    - Do not modify or delete previous version folders; always add a new one for each update.

## Example (Python)
```python
import semver

def find_latest_version(versions):
    valid_versions = [v for v in versions if semver.VersionInfo.isvalid(v)]
    if not valid_versions:
        return None
    return str(max(map(semver.VersionInfo.parse, valid_versions)))

# Example usage:
versions = ['1.2.0', '1.2.1', '1.3.0-beta', '1.3.0']
print(find_latest_version(versions))  # Output: '1.3.0'
```

## Notes
- For non-Python environments, use a semver library in your language of choice.
- If pre-releases should be considered, adjust the comparison logic accordingly.
- This skill is generic and can be adapted for different workflows or scripting environments.
