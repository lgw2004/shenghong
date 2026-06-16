import io
import json

from minio import Minio

from app.core.config import settings

_client: Minio | None = None


def _public_policy() -> dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{settings.minio_bucket}/*"],
            }
        ],
    }


def get_minio_client() -> Minio:
    """获取 MinIO 客户端单例"""
    global _client
    if _client is None:
        _client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            session_token=settings.minio_session_token or None,
            secure=settings.minio_secure,
            region=settings.minio_region,
        )
        # 确保 bucket 存在
        if not _client.bucket_exists(settings.minio_bucket):
            _client.make_bucket(settings.minio_bucket)
        # 设置 bucket 为公开可读
        _client.set_bucket_policy(
            settings.minio_bucket, json.dumps(_public_policy())
        )
    return _client


def build_object_url(object_name: str) -> str:
    """构建公开访问 URL（无预签名参数）"""
    scheme = "https" if settings.minio_secure else "http"
    return f"{scheme}://{settings.minio_endpoint}/{settings.minio_bucket}/{object_name}"


async def upload_screenshot(root_word_id: int, image_bytes: bytes, filename: str) -> str:
    """上传截图到 MinIO，返回公开可访问的 URL"""
    client = get_minio_client()
    object_name = f"{root_word_id}/{filename}"

    client.put_object(
        bucket_name=settings.minio_bucket,
        object_name=object_name,
        data=io.BytesIO(image_bytes),
        length=len(image_bytes),
        content_type="image/png",
    )

    url = build_object_url(object_name)
    print(f"[MinIO] upload_screenshot -> root_word_id={root_word_id}, filename={filename}")
    print(f"[MinIO] public_url = {url}")
    return url
