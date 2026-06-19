from io import BytesIO
from typing import BinaryIO

import boto3
from botocore.client import Config

from app.core.config import get_settings


def s3_client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


async def ensure_bucket() -> None:
    settings = get_settings()
    client = s3_client()
    buckets = [item["Name"] for item in client.list_buckets().get("Buckets", [])]
    if settings.s3_bucket_name not in buckets:
        client.create_bucket(Bucket=settings.s3_bucket_name)


def put_object(key: str, body: bytes, content_type: str) -> None:
    settings = get_settings()
    s3_client().put_object(
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=body,
        ContentType=content_type,
    )


def get_object_stream(key: str) -> tuple[BinaryIO, int]:
    settings = get_settings()
    response = s3_client().get_object(Bucket=settings.s3_bucket_name, Key=key)
    return response["Body"], response.get("ContentLength", 0)
