"""ที่เก็บไฟล์เสียง — local สำหรับ dev, s3/r2 สำหรับของจริง

local backend มีไว้ให้ M0 รันได้โดยไม่ต้องมี cloud credential
"""
from pathlib import Path
import shutil
from uuid import uuid4

from .config import settings


def _local_root() -> Path:
    root = Path(settings().media_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def local_path(key: str) -> Path:
    root = _local_root().resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError("Invalid storage path")
    return path


def new_key(filename: str) -> str:
    suffix = Path(filename).suffix.lower() or ".bin"
    return f"raw/{uuid4().hex}{suffix}"


def upload_target(key: str) -> dict:
    """คืนที่อยู่ให้เบราว์เซอร์อัปโหลดตรง — ไฟล์เสียง 60 นาทีไม่ควรวิ่งผ่าน app server"""
    s = settings()
    if s.storage_backend == "s3":
        import boto3

        client = boto3.client(
            "s3",
            endpoint_url=s.s3_endpoint_url or None,
            region_name=s.s3_region,
        )
        url = client.generate_presigned_url(
            "put_object",
            Params={"Bucket": s.s3_bucket, "Key": key},
            ExpiresIn=3600,
        )
        return {"method": "PUT", "url": url, "headers": {}}

    # local: อัปโหลดผ่าน API แทน presigned URL
    return {
        "method": "PUT",
        "url": f"{s.public_api_url}/api/upload/{key}",
        "headers": {},
    }


def write(key: str, data: bytes) -> None:
    s = settings()
    if s.storage_backend == "s3":
        import boto3

        boto3.client("s3", endpoint_url=s.s3_endpoint_url or None,
                     region_name=s.s3_region).put_object(
            Bucket=s.s3_bucket, Key=key, Body=data)
        return
    path = local_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def fetch_to(key: str, dest: Path) -> Path:
    """ดึงไฟล์ลงดิสก์ของ worker เพื่อให้ ffmpeg อ่านได้"""
    s = settings()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if s.storage_backend == "s3":
        import boto3

        boto3.client("s3", endpoint_url=s.s3_endpoint_url or None,
                     region_name=s.s3_region).download_file(
            s.s3_bucket, key, str(dest))
        return dest
    src = local_path(key)
    if src.resolve() != dest.resolve():
        shutil.copyfile(src, dest)
    return dest


def delete_prefix(prefix: str) -> None:
    """ลบตามนโยบาย PDPA"""
    s = settings()
    if s.storage_backend == "s3":
        import boto3

        client = boto3.client("s3", endpoint_url=s.s3_endpoint_url or None,
                              region_name=s.s3_region)
        listed = client.list_objects_v2(Bucket=s.s3_bucket, Prefix=prefix)
        for obj in listed.get("Contents", []):
            client.delete_object(Bucket=s.s3_bucket, Key=obj["Key"])
        return
    root = _local_root()
    for path in root.glob(f"{prefix}*"):
        if path.is_file():
            path.unlink()
