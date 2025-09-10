from django.conf import settings
from celery import shared_task
from .utils import get_remote_content_length, download_with_limit
import boto3
import os
import tempfile

@shared_task(bind=True)
def fetch_and_store_video(self, video_url, bucket_key, max_mb=200):
    max_bytes = max_mb * 1024 * 1024
    # try HEAD first
    cl = get_remote_content_length(video_url)
    if cl is not None and cl > max_bytes:
        return {"status": "rejected", "reason": "too_large_head", "size": cl}

    # download to temp and abort if exceeds max
    fd, tmp_path = tempfile.mkstemp(suffix=".tmp")
    os.close(fd)
    try:
        size = download_with_limit(video_url, max_bytes, tmp_path)
    except Exception as e:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        return {"status": "failed", "reason": str(e)}

    # upload to S3
    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=getattr(settings, "AWS_REGION", None)
    )
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    try:
        s3.upload_file(tmp_path, bucket, bucket_key)
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    return {"status": "ok", "size": size, "key": bucket_key}