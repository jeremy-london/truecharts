import os
import argparse
import datetime
import json
import shutil
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import yaml
import re
import copy
import subprocess
import sys
from urllib.parse import urljoin

from config import APPS as apps
from config import CHARTS_DIR
from version_checker import GHCRChecker, DockerHubChecker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Load the catalog of the Helm charts
with open(CHARTS_DIR / "catalog.json", "r") as f:
    catalog = json.load(f)

# Initialize the version checkers
checkers = {"ghcr": GHCRChecker(), "dockerhub": DockerHubChecker()}
_tag_validation_cache = {}


class QuotedString(str):
    """String type that forces quoted YAML emission."""


def _quoted_str_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')


yaml.add_representer(QuotedString, _quoted_str_representer)


@dataclass
class ChartVersion:
    """Represents version information for a Helm chart"""

    version: str
    app_version: str
    last_update: str
    digest: str = None
    tag: str = None
    repository: str = None

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


def numeric_version_tuple(version: str):
    if re.fullmatch(r"\d+(?:\.\d+)*", version):
        return tuple(int(p) for p in version.split("."))
    return None


def _checker_for_repository(repository: str):
    repository = repository.strip()
    if repository.startswith("ghcr.io/"):
        return checkers["ghcr"], repository.removeprefix("ghcr.io/")
    if repository.startswith("docker.io/"):
        return checkers["dockerhub"], repository.removeprefix("docker.io/")
    if repository.startswith("lscr.io/"):
        return checkers["dockerhub"], repository.removeprefix("lscr.io/")
    # Treat bare DockerHub refs as DockerHub repositories.
    if "/" in repository:
        first_segment = repository.split("/", 1)[0]
        if "." in first_segment:
            return None, None
        return checkers["dockerhub"], repository
    if repository:
        return checkers["dockerhub"], repository
    return None, None


def _canonical_repository(repository: str):
    checker, image = _checker_for_repository(repository)
    if not checker or not image:
        return repository
    if isinstance(checker, DockerHubChecker) and "/" not in image:
        image = f"library/{image}"
    return f"{checker.__class__.__name__}:{image}"


def validate_tag_exists(repository: str, tag: str) -> bool:
    cache_key = (repository, tag)
    if cache_key in _tag_validation_cache:
        return _tag_validation_cache[cache_key]
    checker, image = _checker_for_repository(repository)
    if not checker or not image:
        logger.debug(
            "Skipping tag validation for unsupported repository format: %s", repository
        )
        _tag_validation_cache[cache_key] = True
        return True
    try:
        checker.get_latest_version(image=image, label=tag)
        _tag_validation_cache[cache_key] = True
        return True
    except Exception as e:
        logger.error("Tag validation failed for %s:%s (%s)", repository, tag, e)
        _tag_validation_cache[cache_key] = False
        return False


def _semverish_tuple(tag: str):
    # Accept strict numeric semver-like tags and common release prefixes.
    # Examples: 1.2.3, 4.0.17.2952, v1.2.3, version-1.2.3
    match = re.fullmatch(r"(?:version-|v)?(\d+\.\d+\.\d+(?:\.\d+)*)", tag)
    if not match:
        return None
    ver = match.group(1)
    return tuple(int(part) for part in ver.split(".")), ver


def _major_minor_from_tag(tag: str):
    match = re.fullmatch(r"(?:version-|v)?(\d+)\.(\d+)(?:\.\d+)?(?:[-+].*)?", tag)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _list_tags_from_repository(repository: str):
    checker, image = _checker_for_repository(repository)
    if not checker or not image:
        return []

    if isinstance(checker, GHCRChecker):
        owner, name = image.split("/", 1)
        headers = {"Authorization": f"Bearer {checker._auth(owner, name)}"}
        base_url = urljoin(checker.base_url, f"{image}/tags/list")
        tags = []
        n = 100
        last = None
        pages = 0
        while pages < 30:
            url = f"{base_url}?n={n}" + (f"&last={last}" if last else "")
            response = checker.session.get(
                url, headers=headers, timeout=checker.timeout
            )
            response.raise_for_status()
            data = response.json()
            page_tags = data.get("tags") or []
            if not page_tags:
                break
            tags.extend(page_tags)
            pages += 1
            if len(page_tags) < n:
                break
            last = page_tags[-1]
        return tags

    if isinstance(checker, DockerHubChecker):
        tags = []
        if "/" not in image:
            image = f"library/{image}"
        url = urljoin(checker.base_url, f"repositories/{image}/tags")
        params = {"page_size": 100, "ordering": "last_updated"}
        pages = 0
        while url and pages < 5:
            response = checker.session.get(
                url, params=params if pages == 0 else None, timeout=checker.timeout
            )
            response.raise_for_status()
            data = response.json()
            tags.extend(
                [
                    result.get("name")
                    for result in data.get("results", [])
                    if result.get("name")
                ]
            )
            url = data.get("next")
            pages += 1
        return tags

    return []


def find_latest_semverish_tag(repository: str):
    tags = _list_tags_from_repository(repository)
    candidates = []
    for tag in tags:
        parsed = _semverish_tuple(tag)
        if parsed:
            ver_tuple, app_version = parsed
            candidates.append((tag, app_version, ver_tuple))
    if not candidates:
        return None, None
    best_tag, best_app_version, _ = max(
        candidates, key=lambda item: (item[2], len(item[2]))
    )
    return best_tag, best_app_version


def find_latest_major_minor_version(repository: str, major: int):
    tags = _list_tags_from_repository(repository)
    pairs = []
    for tag in tags:
        parsed = _major_minor_from_tag(tag)
        if parsed and parsed[0] == major:
            pairs.append(parsed)
    if not pairs:
        return None
    best_major, best_minor = max(pairs)
    return f"{best_major}.{best_minor}"


def parse_version(tags, matcher: str = None, rewriter: str = None):
    """Check if one of the tags matches the version pattern and rewrite it to the accepted format"""

    def format_version(raw_version: str) -> str:
        if rewriter:
            return rewriter.format(raw_version)
        return raw_version

    def candidate_key(candidate):
        raw_version = candidate[1]
        numeric = numeric_version_tuple(raw_version)
        # Prefer numeric versions first and compare numerically.
        if numeric is not None:
            return (1, numeric, raw_version.count("."), len(raw_version))
        # Fallback to shape/length ordering for non-numeric values.
        return (0, tuple(), raw_version.count("."), len(raw_version))

    candidates = []
    if matcher:
        for tag in tags:
            if match := re.search(matcher, tag):
                candidates.append((tag, match[0]))
    if candidates:
        tag, raw_version = max(candidates, key=candidate_key)
        return tag, format_version(raw_version)

    # Fallback: extract dotted numeric versions and choose the most specific one.
    fallback = []
    for tag in tags:
        if match := re.search(r"\d+\.\d+(?:\.\d+)*", tag):
            fallback.append((tag, match[0]))
    if fallback:
        tag, raw_version = max(fallback, key=candidate_key)
        return tag, format_version(raw_version)

    return tags[0], "unknown"


def check_version(app, skip_downgrades: bool = False):
    app_name, app_train = app["name"], app["train"]
    logger.info(f"Checking {app_name} in {app_train}")
    local_version = ChartVersion(
        version=catalog[app_train][app_name]["latest_version"],
        app_version=catalog[app_train][app_name]["latest_app_version"],
        last_update=catalog[app_train][app_name]["last_update"],
    )
    with open(
        CHARTS_DIR / f"{app_train}/{app_name}/{local_version.version}/ix_values.yaml",
        "r",
    ) as f:
        ix_values = yaml.safe_load(f)
    image_repository = str(ix_values["image"]["repository"])
    stored_tag = str(ix_values["image"]["tag"])
    tag_parts = stored_tag.split("@", maxsplit=1)
    local_version.tag = tag_parts[0]
    local_version.digest = tag_parts[1] if len(tag_parts) > 1 else None
    local_version.repository = image_repository
    local_tag_valid = validate_tag_exists(image_repository, local_version.tag)
    if not local_tag_valid:
        logger.warning(
            "Local tag is invalid for configured repository %s/%s: %s:%s",
            app_train,
            app_name,
            image_repository,
            local_version.tag,
        )

    checker = checkers[app["check_ver"]["type"]]
    image_ref = (
        f"{app['check_ver']['package_owner']}/{app['check_ver']['package_name']}"
    )
    source_repository = (
        f"ghcr.io/{image_ref}" if app["check_ver"]["type"] == "ghcr" else image_ref
    )
    same_repo = _canonical_repository(source_repository) == _canonical_repository(
        image_repository
    )
    remote_image_version = checker.get_latest_version(
        image=image_ref, label=app["check_ver"].get("anchor_tag", None)
    )
    remote_tags, remote_digest = remote_image_version.tags, remote_image_version.digest
    source_tag, remote_app_version = parse_version(
        remote_tags,
        app["check_ver"].get("version_matcher", None),
        app["check_ver"].get("version_rewriter", None),
    )
    source_tag_overridden_by_chart_repo = False
    latest_source_tag, latest_source_app_version = find_latest_semverish_tag(
        source_repository
    )
    parsed_num = numeric_version_tuple(remote_app_version)
    latest_num = (
        numeric_version_tuple(latest_source_app_version)
        if latest_source_app_version
        else None
    )
    if (
        latest_source_tag
        and latest_num
        and (parsed_num is None or latest_num > parsed_num)
        and not (same_repo and re.fullmatch(r"\d+", source_tag))
    ):
        logger.warning(
            "Using highest semver-like source tag for %s/%s: %s -> %s",
            app_train,
            app_name,
            source_tag,
            latest_source_tag,
        )
        source_tag = latest_source_tag
        remote_app_version = latest_source_app_version
    if not same_repo:
        latest_repo_tag, latest_repo_app_version = find_latest_semverish_tag(
            image_repository
        )
        repo_num = (
            numeric_version_tuple(latest_repo_app_version)
            if latest_repo_app_version
            else None
        )
        cur_num = numeric_version_tuple(remote_app_version)
        if latest_repo_tag and repo_num and (cur_num is None or repo_num > cur_num):
            logger.warning(
                "Using highest semver-like chart-repo tag for %s/%s: %s -> %s",
                app_train,
                app_name,
                source_tag,
                latest_repo_tag,
            )
            source_tag = latest_repo_tag
            remote_app_version = latest_repo_app_version
            source_tag_overridden_by_chart_repo = True
    if re.fullmatch(r"\d+", source_tag):
        major_minor = find_latest_major_minor_version(image_repository, int(source_tag))
        if major_minor:
            remote_app_version = major_minor
    remote_tag = source_tag
    tag_strip_prefix = app["check_ver"].get("tag_strip_prefix")
    if tag_strip_prefix and remote_tag.startswith(tag_strip_prefix):
        remote_tag = remote_tag[len(tag_strip_prefix) :]
    tag_prefix = app["check_ver"].get("tag_prefix")
    if tag_prefix and not remote_tag.startswith(tag_prefix):
        remote_tag = f"{tag_prefix}{remote_tag}"
    use_digest = app["check_ver"].get("use_digest", True)
    validated_digest = None
    if use_digest and remote_digest and not source_tag_overridden_by_chart_repo:
        try:
            # Validate digest with a real source-registry tag for this image.
            tag_image_version = checker.get_latest_version(
                image=image_ref, label=source_tag
            )
            if tag_image_version.digest == remote_digest:
                validated_digest = remote_digest
            else:
                logger.warning(
                    "Digest mismatch for %s/%s tag %s: expected %s got %s. Falling back to tag-only update.",
                    app_train,
                    app_name,
                    source_tag,
                    remote_digest,
                    tag_image_version.digest,
                )
        except Exception as e:
            logger.warning(
                "Unable to validate digest for %s/%s tag %s (%s). Falling back to tag-only update.",
                app_train,
                app_name,
                source_tag,
                e,
            )
    elif use_digest and remote_digest and source_tag_overridden_by_chart_repo:
        logger.debug(
            "Skipping digest validation for %s/%s because selected tag comes from chart repository tags.",
            app_train,
            app_name,
        )
    if (
        remote_app_version in {"", "unknown"}
        or not re.search(r"\d", remote_app_version)
        or remote_app_version.startswith(".")
    ):
        raise ValueError(
            f"Could not derive a valid app_version for {app_train}/{app_name} "
            f"from tags={remote_tags} using matcher={app['check_ver'].get('version_matcher')!r}"
        )
    if not validate_tag_exists(image_repository, remote_tag):
        fallback_tag, fallback_app_version = find_latest_semverish_tag(image_repository)
        if not fallback_tag:
            raise ValueError(
                f"Computed image tag does not exist for {app_train}/{app_name}: "
                f"{image_repository}:{remote_tag}, and no semver-like fallback tags were found"
            )
        if not validate_tag_exists(image_repository, fallback_tag):
            raise ValueError(
                f"Computed image tag does not exist for {app_train}/{app_name}: "
                f"{image_repository}:{remote_tag}, and fallback tag also failed validation: {fallback_tag}"
            )
        logger.warning(
            "Using fallback semver-like tag for %s/%s: %s -> %s",
            app_train,
            app_name,
            remote_tag,
            fallback_tag,
        )
        remote_tag = fallback_tag
        remote_app_version = fallback_app_version
        if use_digest:
            repo_checker, repo_image = _checker_for_repository(image_repository)
            if repo_checker and repo_image:
                try:
                    validated_digest = repo_checker.get_latest_version(
                        image=repo_image, label=remote_tag
                    ).digest
                except Exception as e:
                    logger.warning(
                        "Unable to retrieve digest for fallback tag %s on %s (%s). Falling back to tag-only update.",
                        remote_tag,
                        image_repository,
                        e,
                    )
                    validated_digest = None
    remote_version = ChartVersion(
        version=increment_version(local_version.version),
        app_version=remote_app_version,
        last_update=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        digest=validated_digest,
        tag=remote_tag,
        repository=image_repository,
    )

    if validated_digest:
        needs_update = (
            validated_digest != local_version.digest or remote_tag != local_version.tag
        )
    else:
        needs_update = (
            remote_tag != local_version.tag
            or remote_app_version != local_version.app_version
        )

    local_num = numeric_version_tuple(local_version.app_version)
    remote_num = numeric_version_tuple(remote_app_version)
    if (
        local_num
        and remote_num
        and remote_num < local_num
        and local_tag_valid
        and skip_downgrades
    ):
        logger.warning(
            "Skipping downgrade for %s/%s due to --skip-downgrades: local app_version=%s, remote app_version=%s",
            app_train,
            app_name,
            local_version.app_version,
            remote_app_version,
        )
        needs_update = False
    elif local_num and remote_num and remote_num < local_num and not local_tag_valid:
        logger.warning(
            "Allowing downgrade-style repair for %s/%s because local tag is invalid: local=%s remote=%s",
            app_train,
            app_name,
            local_version.app_version,
            remote_app_version,
        )

    return needs_update, local_version, remote_version


def update_catalog(
    app_name: str, app_train: str, old_version: ChartVersion, new_version: ChartVersion
):
    logger.info(f"Updating catalog.json for {app_train}/{app_name}")
    catalog[app_train][app_name].update(
        {
            "latest_version": new_version.version,
            "latest_app_version": new_version.app_version,
            "latest_human_version": new_version.human_version,
            "last_update": new_version.last_update,
        }
    )
    with open(CHARTS_DIR / "catalog.json", "w") as f:
        json.dump(catalog, f, indent=4, ensure_ascii=False)
    logger.info(f"Finished updating catalog.json for {app_train}/{app_name}")


def update_app_version_json(
    app_name: str, app_train: str, old_version: ChartVersion, new_version: ChartVersion
):
    app_version_json = f"{app_train}/{app_name}/app_versions.json"
    logger.info(f"Updating {app_version_json}")
    with open(CHARTS_DIR / app_version_json, "r") as f:
        all_versions_dict = json.load(f)
    ref_dict = all_versions_dict.get(old_version.version)
    # all_versions_dict[new_version.version] = copy.deepcopy(ref_dict)
    all_versions_dict = {
        **{new_version.version: copy.deepcopy(ref_dict)},
        **all_versions_dict,
    }
    all_versions_dict[new_version.version].update(
        {
            "location": ref_dict["location"].replace(
                old_version.version, new_version.version
            ),
            "version": new_version.version,
            "human_version": new_version.human_version,
            "last_update": new_version.last_update,
        }
    )
    all_versions_dict[new_version.version]["chart_metadata"].update(
        {
            "version": new_version.version,
            "appVersion": new_version.app_version,
        }
    )
    with open(CHARTS_DIR / app_version_json, "w") as f:
        json.dump(all_versions_dict, f, indent=4, ensure_ascii=False)
    logger.info(f"Finished updating {app_version_json}")


def create_version_dir(
    app_name: str, app_train: str, old_version: ChartVersion, new_version: ChartVersion
):
    old_dir = f"{app_train}/{app_name}/{old_version.version}"
    new_dir = f"{app_train}/{app_name}/{new_version.version}"
    logger.info(f"Creating new version directory at {new_dir}")
    shutil.copytree(CHARTS_DIR / old_dir, CHARTS_DIR / new_dir, dirs_exist_ok=True)
    logger.info(f"Version directary initialized with files from {old_dir}")
    with open(CHARTS_DIR / new_dir / "ix_values.yaml", "r") as f:
        ix_values = yaml.safe_load(f)
    image_tag = (
        f"{new_version.tag}@{new_version.digest}"
        if new_version.digest
        else new_version.tag
    )
    # Keep numeric-like tags quoted so downstream parsers don't coerce to float.
    if re.fullmatch(r"\d+(?:\.\d+)*", image_tag):
        ix_values["image"]["tag"] = QuotedString(image_tag)
    else:
        ix_values["image"]["tag"] = image_tag
    with open(CHARTS_DIR / new_dir / "Chart.yaml", "r") as f:
        chart = yaml.safe_load(f)
    chart["version"] = new_version.version
    chart["appVersion"] = new_version.app_version
    logger.info("Updating Chart.yaml and ix_values.yaml with new version information")
    with open(CHARTS_DIR / new_dir / "ix_values.yaml", "w") as f:
        yaml.dump(ix_values, f)
    with open(CHARTS_DIR / new_dir / "Chart.yaml", "w") as f:
        yaml.dump(chart, f)
    logger.info(f"Finished creating new version directory at {new_dir}")
    return new_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update chart versions from container registry tags"
    )
    parser.add_argument(
        "--app",
        action="append",
        help="Only process specific app name(s). Can be used multiple times.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files or creating commits",
    )
    parser.add_argument(
        "--force-bump",
        action="store_true",
        help="Create a new chart version even when no remote update is detected",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=os.cpu_count() or 4,
        help="Number of concurrent workers for version checks (default: 4)",
    )
    parser.add_argument(
        "--skip-downgrades",
        action="store_true",
        help="Skip updates when the discovered remote app version is numerically lower than local.",
    )
    args = parser.parse_args()
    selected_apps = set(args.app or [])
    workers = max(1, args.workers)

    candidate_apps = []
    for app in apps:
        if selected_apps and app["name"] not in selected_apps:
            continue
        candidate_apps.append(app)

    results = {}

    def run_check(app):
        app_name, app_train = app["name"], app["train"]
        try:
            need_update, old_version, new_version = check_version(
                app, skip_downgrades=args.skip_downgrades
            )
            return app_name, app_train, need_update, old_version, new_version, None
        except Exception as e:
            return app_name, app_train, None, None, None, str(e)

    if workers == 1 or len(candidate_apps) <= 1:
        for app in candidate_apps:
            app_name, app_train, need_update, old_version, new_version, err = run_check(
                app
            )
            results[(app_train, app_name)] = (
                need_update,
                old_version,
                new_version,
                err,
            )
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_map = {pool.submit(run_check, app): app for app in candidate_apps}
            for future in as_completed(future_map):
                app_name, app_train, need_update, old_version, new_version, err = (
                    future.result()
                )
                results[(app_train, app_name)] = (
                    need_update,
                    old_version,
                    new_version,
                    err,
                )

    for app in candidate_apps:
        app_name, app_train = app["name"], app["train"]
        need_update, old_version, new_version, err = results[(app_train, app_name)]
        if err:
            e = err
            logger.error("Skipping %s/%s: %s", app_train, app_name, e)
            continue
        if args.force_bump and not need_update:
            keep_local_tag = bool(
                old_version.repository
                and old_version.tag
                and validate_tag_exists(old_version.repository, old_version.tag)
            )
            if keep_local_tag:
                forced_app_version = old_version.app_version
                forced_tag = old_version.tag
                forced_digest = (
                    old_version.digest
                    if app["check_ver"].get("use_digest", True)
                    else None
                )
            else:
                logger.warning(
                    "Force bump for %s/%s will use resolved remote tag because local tag is invalid: %s:%s",
                    app_train,
                    app_name,
                    old_version.repository,
                    old_version.tag,
                )
                forced_app_version = new_version.app_version
                forced_tag = new_version.tag
                forced_digest = (
                    new_version.digest
                    if app["check_ver"].get("use_digest", True)
                    else None
                )
            use_digest = app["check_ver"].get("use_digest", True)
            new_version = ChartVersion(
                version=increment_version(old_version.version),
                app_version=forced_app_version,
                last_update=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                digest=forced_digest if use_digest else None,
                tag=forced_tag,
                repository=old_version.repository,
            )
            need_update = True
            logger.info("Force bump enabled for %s/%s", app_train, app_name)
        if need_update:
            logger.info(
                f"Updating {app_name} from {old_version.human_version} to {new_version.human_version}"
            )
            if args.dry_run:
                logger.info(
                    "Dry run: would update %s/%s, set tag to %s, and refresh catalog/app_versions/new chart directory",
                    app_train,
                    app_name,
                    f"{new_version.tag}@{new_version.digest}"
                    if new_version.digest
                    else new_version.tag,
                )
                continue
            update_catalog(app_name, app_train, old_version, new_version)
            update_app_version_json(app_name, app_train, old_version, new_version)
            versions_dir = create_version_dir(
                app_name, app_train, old_version, new_version
            )
            # Git add new files and commit changes
            try:
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(CHARTS_DIR),
                        "add",
                        versions_dir,
                        "catalog.json",
                        f"{app_train}/{app_name}/app_versions.json",
                    ],
                    check=True,
                )
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(CHARTS_DIR),
                        "commit",
                        "-m",
                        f"update {app_name} to {new_version.human_version}",
                    ],
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"Git operation failed: {str(e)}")
                sys.exit(1)
        else:
            logger.info(f"No update needed for {app_name} in {app_train}")

    if args.dry_run:
        logger.info(
            "Dry run complete. No files were modified and no commits were created."
        )
    else:
        logger.info("All updates completed. Review commits with:")
        logger.info(f"  git -C {CHARTS_DIR} log")
        logger.info("Push changes when ready with:")
        logger.info(f"  git -C {CHARTS_DIR} push")
