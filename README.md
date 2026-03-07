
# TrueNAS SCALE catalog
## Replicating My TrueNAS SCALE App Setup

Below is a list of all the applications I use on my system, as managed via this TrueCharts catalog. To replicate this setup, ensure you have added this catalog as described above, then install the following apps:


### Installed Applications

- bazarr
- cert-manager
- cloudnative-pg
- clusterissuer
- flaresolverr
- home-assistant
- mosquitto
- nzbget
- ollama-api-passthrough
- ombi
- open-webui
- openebs
- plex
- prometheus-operator
- portainer
- prowlarr
- qbittorrent
- radarr
- sonarr
- tautulli
- traefik
- truenas-scale-ui
- uptime-kuma
- zigbee2mqtt

#### Example Application Statuses

Most of these apps are running and up to date. Some (like `clusterissuer`, `ollama-api-passthrough`, `open-webui`, and `truenas-scale-ui`) may be stopped depending on your needs.

#### How to Install

1. Go to **Apps** in the TrueNAS SCALE UI.
2. Use the **Discover Apps** or **Manage Catalogs** to ensure this catalog is added.
3. Search for each app listed above and install it.
4. Configure each app as needed for your environment.

#### Example App Info (bazarr)

**Name:** bazarr  
**App Version:** 1.5.3  
**Chart Version:** 20.2.3  
**Catalog:** Copyoftruecharts  
**Train:** stable  
**Status:** Running, Up to date  
**Resource Usage:** 166.01 MiB RAM, 0% CPU, 500 b/s - 300 b/s Network  
**Source:** [ghcr.io/onedr0p/bazarr](https://ghcr.io/onedr0p/bazarr)  
**Docs:** [TrueCharts Bazarr](https://truecharts.org/charts/stable/bazarr)

Repeat for each app as needed. For more details on each app, see the [TrueCharts documentation](https://truecharts.org).
### Charts mainted by the upper-stream fork:

- **premium train:**
  - authelia
  - grafana
  - nextcloud
  - prometheus
  - traefik

- **stable train**
  - anything-llm
  - audiobookshelf
  - autobrr
  - bazarr
  - changedetection.io
  - cloudflared
  - code-server
  - codeproject-ai-server
  - crafty-4
  - factorio
  - frigate
  - flaresolverr
  - gamevault-backend
  - home-assistant
  - immich
  - jellyfin
  - jellystat
  - lidarr
  - lldap
  - local-ai
  - maintainerr
  - meshcentral
  - minio
  - nzbget
  - ollama
  - paperless-ngx
  - plex
  - prowlarr
  - qbitmanage
  - qBittorrent
  - radarr
  - readarr
  - recyclarr
  - satisfactory
  - sabnzbd
  - sftpgo
  - sonarr
  - stun-turn-server
  - syncthing
  - tautulli
  - tdarr
  - unpackerr


### How to update other charts in this catalog:

This fork comes with a semi-automatic updater in `updater` which checks for newer images of apps specified in `updater/config.py` and creates corresponding charts to use the latest images. You can add an app into the configuration, e.g.

```python
import pathlib

CHARTS_DIR = <path/to/this/project>
APPS = [
    {
        "name": "wg-easy",                  # Name of the chart
        "train": "stable",                  # Train
        "check_ver": {
            "type": "ghcr",                 # Where to look for newer images. GitHub (ghcr) or DockerHub (dockerhub)
            "package_owner": "wg-easy",     # <package_owner>/<package_name> is the repo for the images
            "package_name": "wg-easy",
            "anchor_tag": "latest",         # [Optional] Only images with the <anchor_tag> are considered when updating.
            "version_matcher": r"^\d+$",    # [Optional] To extract version from tag
            "version_rewriter": "{}.0.0"    # [Optional] Rewrite the version from tag into another format
        },
    }
    ...
]
```

Then, by running

```bash
cd <path/to/this/project>/updater
python update.py
```

It honestly replicates the follwoing steps used by the upper-stream fork:

1. `catalog.json`:
   Search for your application and update following part for your app
   ```"latest_version": "3.0.9",
            "latest_app_version": "2.0.3",
            "latest_human_version": "2.0.3_3.0.9",
            "last_update": "2024-05-29 12:35:14",
   ```
   - **latest_version**: `3.0.9` --> `3.1.0` (bump the _chart_ version one version up)
   - **latest_app_version**: `2.0.3` --> `3.1.0` (insert the _app_ version you're updating to)
   - **latest_human_version**: `2.0.3_3.0.9` --> `2.1.0_3.1.0` (_chart_ version & _app_ version combined together)
   - **last_update**: `2024-05-29 12:35:14` --> `2024-09-03 17:00:00` (take the approx. date & time when you're updating the app)
2. `stable\maintainerr\app_versions.json`:
   Dublicate everything between
   ```
    "3.0.9": {
        "healthy": true,
        "supported": true,
        "healthy_error": null,
   ```
   and
   ```
    },
   ```
   just before these lines where the information for the next older version starts:
   ```
    "3.0.9": {
        "healthy": true,
        "supported": true,
        "healthy_error": null,
   ```
   - Change these occurances:
     - 1x `2024-05-29 12:35:14` (take the date & time value you used at step one when modifying `catalog.json`)
     - 2x `2.0.3` (take the _app_ version value you used at step one when modifying `catalog.json`)
     - 5x `3.0.9` (take the _chart_ version value you used at step one when modifying `catalog.json`)
3. Dublicate the folder `stable\maintainerr\3.0.9` and change the folder name to the _chart_ version value you used at step one when modifying `catalog.json`
4. Change these occurances within `stable\maintainerr\3.1.0\Chart.yaml`:
   - 1x `2.0.3` (take the _app_ version value you used at step one when modifying `catalog.json`)
   - 1x `3.0.9` (take the _chart_ version value you used at step one when modifying `catalog.json`)
5. `stable\maintainerr\3.1.0\ix_values.yaml`:
   Update these lines where the image is specified:
   ```
   	image:
   	repository: jorenn92/maintainerr
   	pullPolicy: IfNotPresent
   	tag: 2.0.3
   ```
   With some exceptions I always use the images which TrueCharts uses. I copy them from the TrueCharts repository:
   https://github.com/truecharts/charts/blob/master/charts/stable/maintainerr/values.yaml
