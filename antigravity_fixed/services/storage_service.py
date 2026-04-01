"""
Storage Service
---------------
Wraps boto3 for uploading files to AWS S3 or Cloudflare R2.
R2 is recommended (zero egress cost) — set S3_ENDPOINT_URL in .env.
"""

import uuid
import boto3
from botocore.config import Config
from config import settings
import structlog

log = structlog.get_logger()

_s3_client = None


def get_s3():
    global _s3_client
    if _s3_client is None:
        kwargs = dict(
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            config=Config(signature_version="s3v4"),
        )
        if settings.S3_ENDPOINT_URL:
            kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
        _s3_client = boto3.client("s3", **kwargs)
    return _s3_client


def upload_bytes(data: bytes, folder: str, filename: str, content_type: str) -> str:
    """
    Uploads raw bytes to S3/R2.
    Returns the object key (not a signed URL — use get_signed_url for downloads).
    """
    key = f"{folder}/{uuid.uuid4()}-{filename}"
    try:
        get_s3().put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        log.info("file_uploaded", key=key, size=len(data))
        return key
    except Exception as e:
        log.error("s3_upload_failed", error=str(e))
        raise


def get_signed_url(key: str, expires_in: int = 3600) -> str:
    """Returns a pre-signed download URL valid for `expires_in` seconds."""
    try:
        return get_s3().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key},
            ExpiresIn=expires_in,
        )
    except Exception as e:
        log.error("signed_url_failed", key=key, error=str(e))
        raise


def delete_object(key: str) -> None:
    try:
        get_s3().delete_object(Bucket=settings.S3_BUCKET, Key=key)
        log.info("file_deleted", key=key)
    except Exception as e:
        log.error("s3_delete_failed", key=key, error=str(e))
