"""
app/training/spaces_uploader.py — Upload model artifacts to DigitalOcean Spaces.

Called at end of Azure training job.
Artifacts are versioned: spaces_path = oracle-models/{version}/{artifact_name}
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger(__name__)

SPACES_BUCKET = "oracle-models"
MODEL_EXTENSIONS = {".pkl", ".pt", ".txt", ".json"}


async def upload_model_artifacts(local_dir: Path) -> int:
    """
    Upload all model artifacts from local_dir to DigitalOcean Spaces.

    Args:
        local_dir: Root directory containing model subdirectories.
    Returns:
        Number of files uploaded.
    """
    try:
        import boto3
        from botocore.client import Config

        from app.config import get_settings

        settings = get_settings()

        spaces_key = getattr(settings, "spaces_key", None)
        spaces_secret = getattr(settings, "spaces_secret", None)
        spaces_region = getattr(settings, "spaces_region", "tor1")
        spaces_endpoint = f"https://{spaces_region}.digitaloceanspaces.com"

        if not spaces_key or not spaces_secret:
            log.warning("DO Spaces credentials not set — skipping upload")
            return 0

        client = boto3.client(
            "s3",
            region_name=spaces_region,
            endpoint_url=spaces_endpoint,
            aws_access_key_id=spaces_key,
            aws_secret_access_key=spaces_secret,
            config=Config(signature_version="s3v4"),
        )

        version = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        uploaded = 0

        for artifact_path in local_dir.rglob("*"):
            if not artifact_path.is_file():
                continue
            if artifact_path.suffix not in MODEL_EXTENSIONS:
                continue

            # Relative path from local_dir
            relative = artifact_path.relative_to(local_dir)
            spaces_key_path = f"{version}/{relative}"

            try:
                client.upload_file(
                    str(artifact_path),
                    SPACES_BUCKET,
                    spaces_key_path,
                    ExtraArgs={"ACL": "private"},
                )
                uploaded += 1
                log.debug(
                    "Uploaded %s → spaces://%s/%s",
                    artifact_path.name,
                    SPACES_BUCKET,
                    spaces_key_path,
                )
            except Exception:
                log.exception("Failed to upload %s", artifact_path)

        log.info("DO Spaces: uploaded %d artifacts (version=%s)", uploaded, version)
        return uploaded

    except ImportError:
        log.error("boto3 not installed — cannot upload to DO Spaces")
        return 0
    except Exception:
        log.exception("DO Spaces upload failed")
        return 0


async def download_model_artifacts(
    local_dir: Path,
    version: str = "latest",
) -> int:
    """
    Download model artifacts from DO Spaces to local_dir.
    Called during API startup if models aren't present locally.
    """
    try:
        import boto3
        from botocore.client import Config

        from app.config import get_settings

        settings = get_settings()

        spaces_key = getattr(settings, "spaces_key", None)
        spaces_secret = getattr(settings, "spaces_secret", None)
        spaces_region = getattr(settings, "spaces_region", "tor1")
        spaces_endpoint = f"https://{spaces_region}.digitaloceanspaces.com"

        if not spaces_key or not spaces_secret:
            log.warning("DO Spaces credentials not configured — models will not auto-download")
            return 0

        client = boto3.client(
            "s3",
            region_name=spaces_region,
            endpoint_url=spaces_endpoint,
            aws_access_key_id=spaces_key,
            aws_secret_access_key=spaces_secret,
            config=Config(signature_version="s3v4"),
        )

        # List objects in bucket with this version prefix
        if version == "latest":
            # Get the most recent version prefix
            response = client.list_objects_v2(Bucket=SPACES_BUCKET, Delimiter="/")
            prefixes = [p["Prefix"].rstrip("/") for p in response.get("CommonPrefixes", [])]
            if not prefixes:
                log.warning("No model versions found in DO Spaces")
                return 0
            version = sorted(prefixes)[-1]  # most recent by date-string sort

        paginator = client.get_paginator("list_objects_v2")
        downloaded = 0

        for page in paginator.paginate(Bucket=SPACES_BUCKET, Prefix=f"{version}/"):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                # Strip version prefix from key
                relative = key[len(f"{version}/") :]
                local_path = local_dir / relative
                local_path.parent.mkdir(parents=True, exist_ok=True)

                try:
                    client.download_file(SPACES_BUCKET, key, str(local_path))
                    downloaded += 1
                except Exception:
                    log.exception("Failed to download %s", key)

        log.info("DO Spaces: downloaded %d artifacts (version=%s)", downloaded, version)
        return downloaded

    except ImportError:
        log.error("boto3 not installed — cannot download from DO Spaces")
        return 0
    except Exception:
        log.exception("DO Spaces download failed")
        return 0
