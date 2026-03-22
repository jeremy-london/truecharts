import base64
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)


@dataclass
class ImageVersion:
    """Represents version information for a container image"""

    tags: List[str]
    digest: str
    last_updated: datetime


class VersionChecker(ABC):
    """Abstract base class for container registry version checkers"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()

    @abstractmethod
    def get_latest_version(
        self, image: str, label: Optional[str] = None
    ) -> ImageVersion:
        """
        Get the latest version information for a container image

        Args:
            image: Image name (e.g., 'library/ubuntu' or 'truecharts/app')
            label: Optional label/tag to filter by (e.g., 'stable', 'latest', 'preview')

        Returns:
            ImageVersion object containing tags and digest information
        """
        pass


class DockerHubChecker(VersionChecker):
    """Version checker for Docker Hub registry"""

    def __init__(self, timeout: int = 30):
        super().__init__(timeout)
        self.base_url = "https://hub.docker.com/v2/"

    def get_latest_version(
        self, image: str, label: Optional[str] = None
    ) -> ImageVersion:
        # Handle official images that start with 'library/'
        if "/" not in image:
            image = f"library/{image}"

        # Get all tags
        url = urljoin(self.base_url, f"repositories/{image}/tags")
        params = {"page_size": 100, "ordering": "last_updated"}

        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        logger.debug(f"Initial API response: {data}")

        if not data.get("results"):
            raise ValueError(f"No tags found for image {image}")

        # Filter and sort results
        results = data["results"]
        target_tag = None

        if label:
            # Find the specific tag if label is provided
            matching_results = [r for r in results if r.get("name") == label]
            if not matching_results:
                raise ValueError(
                    f"No tags matching label '{label}' found for image {image}"
                )
            target_tag = matching_results[0]
        else:
            # Get the most recent result
            target_tag = results[0]

        logger.debug(f"Target tag data: {target_tag}")

        # Get the digest from the images list
        if not target_tag.get("images"):
            raise ValueError("No image data found in tag")

        # Get the digest from the first image (should be the most relevant one)
        digest = target_tag["digest"]
        matching_tags = []

        # Paginate through all results to find matching tags
        num_page_to_check = 2
        current_page = data
        while True:
            for result in current_page["results"]:
                if result.get("digest") and result["digest"] == digest:
                    matching_tags.append(result["name"])

            next_page = current_page.get("next")
            num_page_to_check -= 1
            if not next_page or num_page_to_check == 0:
                break

            response = self.session.get(next_page, timeout=self.timeout)
            response.raise_for_status()
            current_page = response.json()

        return ImageVersion(
            tags=sorted(matching_tags),
            digest=digest,
            last_updated=datetime.strptime(
                target_tag["last_updated"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
        )


class GHCRChecker(VersionChecker):
    """Version checker for GitHub Container Registry"""

    MEDIA_TYPES = {
        "manifest_v2": "application/vnd.docker.distribution.manifest.v2+json",
        "manifest_list_v2": "application/vnd.docker.distribution.manifest.list.v2+json",
        "oci_index": "application/vnd.oci.image.index.v1+json",
        "oci_manifest": "application/vnd.oci.image.manifest.v1+json",
        "docker_manifest": "application/vnd.docker.distribution.manifest.v1+json",
    }

    def __init__(self, timeout: int = 30):
        super().__init__(timeout)
        self.base_url = "https://ghcr.io/v2/"
        self.session.headers.update({"User-Agent": "Docker-Client/20.10.2 (linux)"})

    def _auth(self, package_owner: str, package_name: str) -> str:
        """Generate authentication token for GHCR"""
        token = base64.b64encode(f"v1:{package_owner}/{package_name}:0".encode())
        return token.decode("utf-8")

    def _get_manifest(
        self, package_owner: str, package_name: str, tag: str
    ) -> Tuple[Dict, str]:
        """Get manifest for a specific tag"""
        url = urljoin(self.base_url, f"{package_owner}/{package_name}/manifests/{tag}")
        headers = {
            "Authorization": f"Bearer {self._auth(package_owner, package_name)}",
            "Accept": (
                f"{self.MEDIA_TYPES['manifest_list_v2']}, "
                f"{self.MEDIA_TYPES['manifest_v2']}, "
                f"{self.MEDIA_TYPES['docker_manifest']}, "
                f"{self.MEDIA_TYPES['oci_index']}, "
                f"{self.MEDIA_TYPES['oci_manifest']}"
            ),
        }

        logger.debug(f"Getting manifest from {url}")
        logger.debug(f"Headers: {headers}")

        response = self.session.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()

        # Get the digest from the Docker-Content-Digest header
        digest = response.headers.get("Docker-Content-Digest", "")
        manifest = response.json()

        logger.debug(f"Manifest response: {manifest}")
        logger.debug(f"Docker-Content-Digest: {digest}")

        return manifest, digest

    def get_latest_version(
        self, image: str, label: Optional[str] = None
    ) -> ImageVersion:
        # Split image into owner and name
        package_owner, package_name = image.split("/")
        logger.debug(f"Getting version for {package_owner}/{package_name}")

        # Get list of tags
        url = urljoin(self.base_url, f"{package_owner}/{package_name}/tags/list")
        headers = {"Authorization": f"Bearer {self._auth(package_owner, package_name)}"}

        logger.debug(f"Getting tags from {url}")
        response = self.session.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        tags_data = response.json()

        if not tags_data.get("tags"):
            raise ValueError(f"No tags found for image {image}")

        # Filter tags if label is provided
        tags = tags_data["tags"]
        logger.debug(f"Available tags: {tags}")

        if label:
            target_tag = label
            other_tags = [t for t in tags if t != label]
        else:
            # When no label is specified, prioritize 'nightly' and 'development' tags
            if "nightly" in tags:
                target_tag = "nightly"
            elif "development" in tags:
                target_tag = "development"
            else:
                target_tag = tags[0]
            other_tags = [t for t in tags if t != target_tag]

        logger.debug(f"Target tag: {target_tag}")
        logger.debug(f"Other tags: {other_tags}")

        # Get manifest for the target tag
        _, digest = self._get_manifest(package_owner, package_name, target_tag)
        if not digest:
            raise ValueError("Could not find manifest digest")

        logger.debug(f"Target digest: {digest}")

        # Find all tags pointing to this digest
        matching_tags = [target_tag]
        for tag in other_tags:
            try:
                _, tag_digest = self._get_manifest(package_owner, package_name, tag)
                if tag_digest == digest:
                    matching_tags.append(tag)
            except Exception as e:
                logger.debug(f"Error getting manifest for tag {tag}: {e}")
                continue

        logger.debug(f"Matching tags: {matching_tags}")

        # Use current time as last_updated since GHCR doesn't provide it in the API
        return ImageVersion(
            tags=sorted(matching_tags), digest=digest, last_updated=datetime.now()
        )
