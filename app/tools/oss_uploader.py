from __future__ import annotations

from pathlib import Path
from app.core.config import Settings


class OSSUploader:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def upload(self, video_path: Path, object_key: str) -> dict:
        if not self.settings.oss_enabled:
            return {"uploaded": False, "reason": "OSS is disabled", "url": None, "object_key": object_key}

        try:
            import oss2  # type: ignore
        except ImportError as exc:
            return {
                "uploaded": False,
                "reason": f"oss2 is not installed: {exc}",
                "url": None,
                "object_key": object_key,
            }

        auth = None
        if self.settings.oss_security_token:
            auth = oss2.StsAuth(
                self.settings.oss_access_key_id,
                self.settings.oss_access_key_secret,
                self.settings.oss_security_token,
            )
        else:
            auth = oss2.Auth(
                self.settings.oss_access_key_id,
                self.settings.oss_access_key_secret,
            )

        bucket = oss2.Bucket(auth, self.settings.oss_endpoint, self.settings.oss_bucket)
        result = bucket.put_object(object_key, video_path.read_bytes())

        if self.settings.oss_public_base_url:
            url = f"{self.settings.oss_public_base_url.rstrip('/')}/{object_key}"
        else:
            endpoint = (self.settings.oss_endpoint or "").replace("https://", "").replace("http://", "")
            url = f"https://{self.settings.oss_bucket}.{endpoint}/{object_key}"

        return {
            "uploaded": True,
            "object_key": object_key,
            "etag": getattr(result, "etag", None),
            "request_id": getattr(result, "request_id", None),
            "url": url,
        }
