import argparse
import datetime
import json
import shutil
import logging
from dataclasses import dataclass
import yaml
import re
import copy
import subprocess
import sys

from config import APPS as apps
from config import CHARTS_DIR
from version_checker import GHCRChecker, DockerHubChecker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load the catalog of the Helm charts
with open(CHARTS_DIR/"catalog.json", "r") as f:
    catalog = json.load(f)

# Initialize the version checkers
checkers = {
    "ghcr": GHCRChecker(),
    "dockerhub": DockerHubChecker()
}

@dataclass
class ChartVersion:
    """Represents version information for a Helm chart"""
    version: str
    app_version: str
    last_update: str
    digest: str = None
    tag: str = None
    
    @property
    def human_version(self):
        return f"{self.app_version}_{self.version}"
    
    def __eq__(self, other):
        return self.app_version == other.app_version and self.digest == other.digest

def increment_version(version):
    """Increment the patch version of a semantic version"""
    major, minor, patch = version.split(".")
    patch = str(int(patch) + 1)
    return ".".join([major, minor, patch])

def parse_version(tags, matcher:str = None, rewriter:str = None):
    """ Check if one of the tags matches the version pattern and rewrite it to the accepted format """
    for tag in tags:
        if matcher and (match:=re.search(matcher, tag)):
            raw_version = match[0]
            if rewriter:
                return tag, rewriter.format(raw_version)
            return tag, raw_version

    # Fallback: extract a numeric dotted version from available tags.
    for tag in tags:
        if match := re.search(r"\d+(?:\.\d+)*", tag):
            raw_version = match[0]
            if rewriter:
                return tag, rewriter.format(raw_version)
            return tag, raw_version

    return tags[0], rewriter.format("") if rewriter else "unknown"

def check_version(app):
    app_name, app_train = app["name"], app["train"]
    logger.info(f"Checking {app_name} in {app_train}")
    local_version = ChartVersion(
        version=catalog[app_train][app_name]["latest_version"],
        app_version=catalog[app_train][app_name]["latest_app_version"],
        last_update=catalog[app_train][app_name]["last_update"]
    )
    with open(CHARTS_DIR/f"{app_train}/{app_name}/{local_version.version}/ix_values.yaml", "r") as f:
        stored_tag = yaml.safe_load(f)["image"]["tag"]
    tag_parts = stored_tag.split("@", maxsplit=1)
    local_version.tag = tag_parts[0]
    local_version.digest = tag_parts[1] if len(tag_parts) > 1 else None
    
    checker = checkers[app["check_ver"]["type"]]
    remote_image_version = checker.get_latest_version(
        image=f"{app['check_ver']['package_owner']}/{app['check_ver']['package_name']}",
        label=app['check_ver'].get("anchor_tag", None)
    )
    remote_tags, remote_digest = remote_image_version.tags, remote_image_version.digest
    remote_tag, remote_app_version = parse_version(remote_tags, app["check_ver"].get("version_matcher", None), app["check_ver"].get("version_rewriter", None))
    remote_version = ChartVersion(
        version=increment_version(local_version.version),
        app_version=remote_app_version,
        last_update=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        digest=remote_digest,
        tag=remote_tag
    )
    
    return remote_digest != local_version.digest, local_version, remote_version  

def update_catalog(app_name:str, app_train:str, old_version:ChartVersion, new_version:ChartVersion):
    logger.info(f"Updating catalog.json for {app_train}/{app_name}")
    catalog[app_train][app_name].update({
        "latest_version": new_version.version,
        "latest_app_version": new_version.app_version,
        "latest_human_version": new_version.human_version,
        "last_update": new_version.last_update
    })
    with open(CHARTS_DIR/"catalog.json", "w") as f:
        json.dump(catalog, f, indent=4, ensure_ascii=False)
    logger.info(f"Finished updating catalog.json for {app_train}/{app_name}")

def update_app_version_json(app_name:str, app_train:str, old_version:ChartVersion, new_version:ChartVersion):
    app_version_json = f"{app_train}/{app_name}/app_versions.json"
    logger.info(f"Updating {app_version_json}")
    with open(CHARTS_DIR/app_version_json, "r") as f:
        all_versions_dict = json.load(f)
    ref_dict = all_versions_dict.get(old_version.version)
    # all_versions_dict[new_version.version] = copy.deepcopy(ref_dict)
    all_versions_dict = {**{new_version.version: copy.deepcopy(ref_dict)}, **all_versions_dict}
    all_versions_dict[new_version.version].update({
        "location": ref_dict["location"].replace(old_version.version, new_version.version),
        "version": new_version.version,
        "human_version": new_version.human_version,
        "last_update": new_version.last_update,
    })
    all_versions_dict[new_version.version]["chart_metadata"].update({
        "version": new_version.version,
        "appVersion": new_version.app_version,
    })
    with open(CHARTS_DIR/app_version_json, "w") as f:
        json.dump(all_versions_dict, f, indent=4, ensure_ascii=False)
    logger.info(f"Finished updating {app_version_json}")

def create_version_dir(app_name:str, app_train:str, old_version:ChartVersion, new_version:ChartVersion):
    old_dir = f"{app_train}/{app_name}/{old_version.version}"
    new_dir = f"{app_train}/{app_name}/{new_version.version}"
    logger.info(f"Creating new version directory at {new_dir}")
    shutil.copytree(CHARTS_DIR/old_dir, CHARTS_DIR/new_dir)
    logger.info(f"Version directary initialized with files from {old_dir}")
    with open(CHARTS_DIR/new_dir/"ix_values.yaml", "r") as f:
        ix_values = yaml.safe_load(f)
    if new_version.digest:
        ix_values["image"]["tag"] = f"{new_version.tag}@{new_version.digest}"
    else:
        ix_values["image"]["tag"] = new_version.tag
    with open(CHARTS_DIR/new_dir/"Chart.yaml", "r") as f:
        chart = yaml.safe_load(f)
    chart["version"] = new_version.version
    chart["appVersion"] = new_version.app_version
    logger.info("Updating Chart.yaml and ix_values.yaml with new version information")
    with open(CHARTS_DIR/new_dir/"ix_values.yaml", "w") as f:
        yaml.dump(ix_values, f)
    with open(CHARTS_DIR/new_dir/"Chart.yaml", "w") as f:
        yaml.dump(chart, f)
    logger.info(f"Finished creating new version directory at {new_dir}")
    return new_dir

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update chart versions from container registry tags")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files or creating commits",
    )
    args = parser.parse_args()

    for app in apps:
        app_name, app_train = app["name"], app["train"]
        need_update, old_version, new_version = check_version(app)
        if need_update:
            logger.info(f"Updating {app_name} from {old_version.human_version} to {new_version.human_version}")
            if args.dry_run:
                logger.info(
                    "Dry run: would update %s/%s, set tag to %s, and refresh catalog/app_versions/new chart directory",
                    app_train,
                    app_name,
                    f"{new_version.tag}@{new_version.digest}" if new_version.digest else new_version.tag,
                )
                continue
            update_catalog(app_name, app_train, old_version, new_version)
            update_app_version_json(app_name, app_train, old_version, new_version)
            versions_dir = create_version_dir(app_name, app_train, old_version, new_version)
            # Git add new files and commit changes
            try:
                subprocess.run(['git', '-C', str(CHARTS_DIR), 'add', 
                            versions_dir, 'catalog.json', f"{app_train}/{app_name}/app_versions.json"], 
                            check=True)
                subprocess.run(['git', '-C', str(CHARTS_DIR), 'commit',
                            '-m', f"update {app_name} to {new_version.human_version}"], 
                            check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Git operation failed: {str(e)}")
                sys.exit(1)
        else:
            logger.info(f"No update needed for {app_name} in {app_train}")
    
    if args.dry_run:
        logger.info("Dry run complete. No files were modified and no commits were created.")
    else:
        logger.info("All updates completed. Review commits with:")
        logger.info(f"  git -C {CHARTS_DIR} log")
        logger.info("Push changes when ready with:")
        logger.info(f"  git -C {CHARTS_DIR} push")
