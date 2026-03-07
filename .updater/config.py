import pathlib

APPS = [
    # {
    #     "name": "bazarr",
    #     "train": "stable",
    #         "check_ver": {
    #             "type": "dockerhub",
    #             "package_owner": "linuxserver",
    #             "package_name": "bazarr",
    #             "anchor_tag": "latest",
    #             "version_matcher": r"\\d+(\\.\\d+)+$",
    #             "version_rewriter": "{}.0.0",
    #         }
    # },
    # {
    #     "name": "flaresolverr",
    #     "train": "stable",
    #         "check_ver": {
    #             "type": "dockerhub",
    #             "package_owner": "flaresolverr",
    #             "package_name": "flaresolverr",
    #             "anchor_tag": "latest",
    #             "version_matcher": r"\\d+(\\.\\d+)+$",
    #             "version_rewriter": "{}.0.0",
    #         }
    # },
    # {
    #     "name": "home-assistant",
    #     "train": "stable",
    #         "check_ver": {
    #             "type": "dockerhub",
    #             "package_owner": "homeassistant",
    #             "package_name": "home-assistant",
    #             "anchor_tag": "latest",
    #             "version_matcher": r"\\d+(\\.\\d+)+$",
    #             "version_rewriter": "{}.0.0",
    #         }
    # },
    # {
    #     "name": "mosquitto",
    #     "train": "stable",
    #         "check_ver": {
    #             "type": "dockerhub",
    #             "package_owner": "library",
    #             "package_name": "eclipse-mosquitto",
    #             "anchor_tag": "latest",
    #             "version_matcher": r"\\d+(\\.\\d+)+$",
    #             "version_rewriter": "{}.0.0",
    #         }
    # },
    # {
    #     "name": "nzbget",
    #     "train": "stable",
    #         "check_ver": {
    #             "type": "dockerhub",
    #             "package_owner": "linuxserver",
    #             "package_name": "nzbget",
    #             "anchor_tag": "latest",
    #             "version_matcher": r"\\d+(\\.\\d+)+$",
    #             "version_rewriter": "{}.0.0",
    #         }
    # },
    # {
    #     "name": "ombi",
    #     "train": "stable",
    #         "check_ver": {
    #             "type": "dockerhub",
    #             "package_owner": "linuxserver",
    #             "package_name": "ombi",
    #             "anchor_tag": "latest",
    #             "version_matcher": r"\\d+(\\.\\d+)+$",
    #             "version_rewriter": "{}.0.0",
    #         }
    # },
    # {
    #     "name": "overseerr",
    #     "train": "stable",
    #         "check_ver": {
    #             "type": "dockerhub",
    #             "package_owner": "sctx",
    #             "package_name": "overseerr",
    #             "anchor_tag": "latest",
    #             "version_matcher": r"\\d+(\\.\\d+)+$",
    #             "version_rewriter": "{}.0.0",
    #         }
    # },
    {
        "name": "plex",
        "train": "stable",
            "check_ver": {
                "type": "dockerhub",
                "package_owner": "linuxserver",
                "package_name": "plex",
                "anchor_tag": "latest",
                "version_matcher": r"\\d+(\\.\\d+)+$",
                "version_rewriter": "{}.0.0",
            }
    },
    # {
    #     "name": "portainer",
    #     "train": "stable",
    #         "check_ver": {
    #             "type": "dockerhub",
    #             "package_owner": "portainer",
    #             "package_name": "portainer-ce",
    #             "anchor_tag": "latest",
    #             "version_matcher": r"\\d+(\\.\\d+)+$",
    #             "version_rewriter": "{}.0.0",
    #         }
    # },
    # {
    #     "name": "prowlarr",
    #     "train": "stable",
    #         "check_ver": {
    #             "type": "dockerhub",
    #             "package_owner": "linuxserver",
    #             "package_name": "prowlarr",
    #             "anchor_tag": "latest",
    #             "version_matcher": r"\\d+(\\.\\d+)+$",
    #             "version_rewriter": "{}.0.0",
    #         }
    # },
    # {
    #     "name": "qbittorrent",
    #     "train": "stable",
    #         "check_ver": {
    #             "type": "dockerhub",
    #             "package_owner": "linuxserver",
    #             "package_name": "qbittorrent",
    #             "anchor_tag": "latest",
    #             "version_matcher": r"\\d+(\\.\\d+)+$",
    #             "version_rewriter": "{}.0.0",
    #         }
    # },
    # {
    #     "name": "radarr",
    #     "train": "stable",
    #         "check_ver": {
    #             "type": "dockerhub",
    #             "package_owner": "linuxserver",
    #             "package_name": "radarr",
    #             "anchor_tag": "latest",
    #             "version_matcher": r"\\d+(\\.\\d+)+$",
    #             "version_rewriter": "{}.0.0",
    #         }
    # },
    # {
    #     "name": "sonarr",
    #     "train": "stable",
    #         "check_ver": {
    #             "type": "dockerhub",
    #             "package_owner": "linuxserver",
    #             "package_name": "sonarr",
    #             "anchor_tag": "latest",
    #             "version_matcher": r"\\d+(\\.\\d+)+$",
    #             "version_rewriter": "{}.0.0",
    #         }
    # },
    # {
    #     "name": "tautulli",
    #     "train": "stable",
    #         "check_ver": {
    #             "type": "dockerhub",
    #             "package_owner": "linuxserver",
    #             "package_name": "tautulli",
    #             "anchor_tag": "latest",
    #             "version_matcher": r"\\d+(\\.\\d+)+$",
    #             "version_rewriter": "{}.0.0",
    #         }
    # },
    # {
    #     "name": "traefik",
    #     "train": "premium",
    #         "check_ver": {
    #             "type": "dockerhub",
    #             "package_owner": "library",
    #             "package_name": "traefik",
    #             "anchor_tag": "latest",
    #             "version_matcher": r"\\d+(\\.\\d+)+$",
    #             "version_rewriter": "{}.0.0",
    #         }
    # },
    # {
    #     "name": "uptime-kuma",
    #     "train": "stable",
    #         "check_ver": {
    #             "type": "dockerhub",
    #             "package_owner": "louislam",
    #             "package_name": "uptime-kuma",
    #             "anchor_tag": "latest",
    #             "version_matcher": r"\\d+(\\.\\d+)+$",
    #             "version_rewriter": "{}.0.0",
    #         }
    # },
    # {
    #     "name": "zigbee2mqtt",
    #     "train": "stable",
    #         "check_ver": {
    #             "type": "dockerhub",
    #             "package_owner": "koenkk",
    #             "package_name": "zigbee2mqtt",
    #             "anchor_tag": "latest",
    #             "version_matcher": r"\\d+(\\.\\d+)+$",
    #             "version_rewriter": "{}.0.0",
    #         }
    # },
]

CHARTS_DIR = pathlib.Path(__file__).parent.parent
