import json
import pathlib
import re

CHARTS_DIR = pathlib.Path(__file__).resolve().parent.parent
CATALOG_PATH = CHARTS_DIR / "catalog.json"


def _load_catalog() -> dict:
    with open(CATALOG_PATH, "r") as f:
        return json.load(f)


def build_catalog_version_matcher(train: str, app_name: str, default: str = r"\d+(\.\d+)+$") -> str:
    """
    Build a matcher using the app's current latest_app_version from catalog.json.
    For dotted numeric versions, allow a nearby segment range so minor format
    changes (e.g. 4-part -> 3-part) still match.
    """
    try:
        latest_app_version = str(_load_catalog()[train][app_name]["latest_app_version"]).strip()
    except (FileNotFoundError, KeyError, TypeError, json.JSONDecodeError):
        return default

    if re.fullmatch(r"\d+", latest_app_version):
        return r"\d+$"

    if re.fullmatch(r"\d+(?:\.\d+)+", latest_app_version):
        parts = len(latest_app_version.split("."))
        repeat_count = parts - 1
        min_repeat = max(1, repeat_count - 1)
        max_repeat = repeat_count + 1
        return rf"\d+(?:\.\d+){{{min_repeat},{max_repeat}}}$"

    return default

APPS = [
    {
        "name": "bazarr",
        "train": "stable",
            "check_ver": {
                "type": "dockerhub",
                "package_owner": "linuxserver",
                "package_name": "bazarr",
                "anchor_tag": "latest",
                "version_matcher": build_catalog_version_matcher("stable", "bazarr"),
                "version_rewriter": "{}",
                "use_digest": False,
            }
    },
    {
        "name": "flaresolverr",
        "train": "stable",
            "check_ver": {
                "type": "dockerhub",
                "package_owner": "flaresolverr",
                "package_name": "flaresolverr",
                "anchor_tag": "latest",
                "version_matcher": build_catalog_version_matcher("stable", "flaresolverr"),
                "version_rewriter": "{}",
            }
    },
    {
        "name": "home-assistant",
        "train": "stable",
            "check_ver": {
                "type": "dockerhub",
                "package_owner": "homeassistant",
                "package_name": "home-assistant",
                "anchor_tag": "latest",
                "version_matcher": build_catalog_version_matcher("stable", "home-assistant"),
                "version_rewriter": "{}",
            }
    },
    {
        "name": "mosquitto",
        "train": "stable",
            "check_ver": {
                "type": "dockerhub",
                "package_owner": "library",
                "package_name": "eclipse-mosquitto",
                "anchor_tag": "latest",
                "version_matcher": build_catalog_version_matcher("stable", "mosquitto"),
                "version_rewriter": "{}",
            }
    },
    {
        "name": "sabnzbd",
        "train": "stable",
            "check_ver": {
                "type": "dockerhub",
                "package_owner": "linuxserver",
                "package_name": "sabnzbd",
                "anchor_tag": "latest",
                "version_matcher": build_catalog_version_matcher("stable", "sabnzbd"),
                "version_rewriter": "{}",
                "use_digest": False,
            }
    },
    {
        "name": "ombi",
        "train": "stable",
            "check_ver": {
                "type": "dockerhub",
                "package_owner": "linuxserver",
                "package_name": "ombi",
                "anchor_tag": "latest",
                "version_matcher": build_catalog_version_matcher("stable", "ombi"),
                "version_rewriter": "{}",
                "use_digest": False,
            }
    },
    {
        "name": "plex",
        "train": "stable",
            "check_ver": {
                "type": "dockerhub",
                "package_owner": "linuxserver",
                "package_name": "plex",
                "anchor_tag": "latest",
                "version_matcher": build_catalog_version_matcher("stable", "plex"),
                "version_rewriter": "{}",
            }
    },
    {
        "name": "portainer",
        "train": "stable",
            "check_ver": {
                "type": "dockerhub",
                "package_owner": "portainer",
                "package_name": "portainer-ce",
                "anchor_tag": "latest",
                "version_matcher": build_catalog_version_matcher("stable", "portainer"),
                "version_rewriter": "{}",
            }
    },
    {
        "name": "prowlarr",
        "train": "stable",
            "check_ver": {
                "type": "dockerhub",
                "package_owner": "linuxserver",
                "package_name": "prowlarr",
                "anchor_tag": "latest",
                "version_matcher": build_catalog_version_matcher("stable", "prowlarr"),
                "version_rewriter": "{}",
                "tag_strip_prefix": "version-",
            }
    },
    {
        "name": "qbittorrent",
        "train": "stable",
            "check_ver": {
                "type": "dockerhub",
                "package_owner": "linuxserver",
                "package_name": "qbittorrent",
                "anchor_tag": "latest",
                "version_matcher": build_catalog_version_matcher("stable", "qbittorrent"),
                "version_rewriter": "{}",
            }
    },
    {
        "name": "radarr",
        "train": "stable",
            "check_ver": {
                "type": "dockerhub",
                "package_owner": "linuxserver",
                "package_name": "radarr",
                "anchor_tag": "latest",
                "version_matcher": build_catalog_version_matcher("stable", "radarr"),
                "version_rewriter": "{}",
            }
    },
    {
        "name": "sonarr",
        "train": "stable",
            "check_ver": {
                "type": "dockerhub",
                "package_owner": "linuxserver",
                "package_name": "sonarr",
                "anchor_tag": "latest",
                "version_matcher": build_catalog_version_matcher("stable", "sonarr"),
                "version_rewriter": "{}",
            }
    },
    {
        "name": "tautulli",
        "train": "stable",
            "check_ver": {
                "type": "dockerhub",
                "package_owner": "linuxserver",
                "package_name": "tautulli",
                "anchor_tag": "latest",
                "version_matcher": build_catalog_version_matcher("stable", "tautulli"),
                "version_rewriter": "{}",
                "tag_prefix": "v",
                "use_digest": False,
            }
    },
    {
        "name": "traefik",
        "train": "premium",
            "check_ver": {
                "type": "dockerhub",
                "package_owner": "library",
                "package_name": "traefik",
                "anchor_tag": "latest",
                "version_matcher": build_catalog_version_matcher("premium", "traefik"),
                "version_rewriter": "{}",
                "tag_prefix": "v",
                "use_digest": True,
            }
    },
    {
        "name": "uptime-kuma",
        "train": "stable",
            "check_ver": {
                "type": "dockerhub",
                "package_owner": "louislam",
                "package_name": "uptime-kuma",
                "anchor_tag": "latest",
                "version_matcher": build_catalog_version_matcher("stable", "uptime-kuma"),
                "version_rewriter": "{}",
                "use_digest": False,
            }
    },
    {
        "name": "zigbee2mqtt",
        "train": "stable",
            "check_ver": {
                "type": "dockerhub",
                "package_owner": "koenkk",
                "package_name": "zigbee2mqtt",
                "anchor_tag": "latest",
                "version_matcher": build_catalog_version_matcher("stable", "zigbee2mqtt"),
                "version_rewriter": "{}",
                "use_digest": False,
            }
    },
]
