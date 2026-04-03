import shutil 
from pathlib import Path
import os
import boto3
import mimetypes
from botocore.exceptions import NoCredentialsError
from fastapi import HTTPException
import subprocess
from pathlib import Path
from PIL import Image
import time
import uuid

BASE_STATIC = "static"
UPLOAD_DIR = "uploads"
MEDIA_DIR = "static/media"
VIDEO_DIR = "static/videos"
THUMB_DIR = "static/videos/thumbnails"

for path in [UPLOAD_DIR, MEDIA_DIR, VIDEO_DIR, THUMB_DIR]:
    os.makedirs(path, exist_ok=True)
    
MAX_AGE = 60 * 60 * 2  # 2 hours

s3_client = boto3.client(
    's3',
    aws_access_key_id='YOUR_KEY',
    aws_secret_access_key='YOUR_SECRET'
)

UPLOAD_STATUS = {}

USE_S3 = os.getenv("USE_S3", "false").lower() == "true"

def save_file(file, folder_path: str) -> str:
    file_name = file.filename
    ext = os.path.splitext(file_name)[1]  # ✅ FIX#

    # Try to get extension from MIME type
    if not ext:
        mime_type = getattr(file, "content_type", None)
        ext = mimetypes.guess_extension(mime_type) if mime_type else ".bin"
    
    if ext == ".bin" and mime_type.startswith("image/"):
        ext = ".jpg"  # default to jpg for images without extension 
    elif ext == ".bin" and mime_type.startswith("video/"):
        ext = ".mp4"  # default to mp4 for videos without extension

    file_name += ext

    full_path = f"{folder_path}/{file_name}"

    if USE_S3:
        return save_file_to_s3(file, "your-bucket-name", full_path)
    else:
        # Your existing VPS/Local logic
        dest = Path(f"static/{folder_path}/{file_name}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            file.file.seek(0)  # Reset file pointer after saving
        return {
            "url": f"/static/{full_path}",
            "path": str(dest)
        }

def save_file_to_s3(file, bucket_name: str, s3_path: str) -> str:
    try:
        # Move cursor to the beginning of the file
        file.file.seek(0) 
        s3_client.upload_fileobj(file.file, bucket_name, s3_path)
        return {
            "url": f"https://{bucket_name}.s3.amazonaws.com/{s3_path}",
            "path": None  # no local path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 Upload Failed: {str(e)}")

def process_video_upload(upload_id: str, temp_path: str):
    try:
        UPLOAD_STATUS[upload_id] = {"status": "processing"}

        # Basic detection (improve later if needed)
        content_type = "image/jpeg" if (temp_path.endswith(".png") or temp_path.endswith(".jpg") or temp_path.endswith(".jpeg")) else "video/mp4"

        temp_file = TempFileWrapper(temp_path, upload_id, content_type)

        result = save_file(temp_file, "media")
        file_url = result["url"]
        local_path = result["path"]

        media_response = {
            "type": None,
            "original": file_url,
            "thumbnail": None,
            "sizes": None
        }

        # 🎥 VIDEO
        if content_type.startswith("video/"):
            media_response["type"] = "video"

            if local_path:
                thumbnail = generate_thumbnail(local_path, upload_id)

                # 🔍 verify file exists on disk
                full_fs_path = thumbnail.replace("/static", "static")
                
                if not os.path.exists(full_fs_path):
                    raise Exception(f"Thumbnail not found at {full_fs_path}")

                media_response["thumbnail"] = full_fs_path
                media_response["original"] = media_response["original"].replace("/static", "static")

        # 🖼 IMAGE
        elif content_type.startswith("image/"):
            media_response["type"] = "image"

            if local_path:
                sizes = generate_image_sizes(local_path, upload_id)
                media_response["sizes"] = sizes
                media_response["thumbnail"] = sizes.get("small")
                media_response["original"] = sizes.get("large")
                media_response["original"] = media_response["original"].replace("/static", "static")

        temp_file.close()

        UPLOAD_STATUS[upload_id] = {
            "status": "completed",
            "media": media_response
        }

    except Exception as e:
        UPLOAD_STATUS[upload_id] = {
            "status": "failed",
            "error": str(e)
        }

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def generate_thumbnail(video_path: str, upload_id: str) -> str:
    thumbnail_dir = Path("static/videos/thumbnails")
    thumbnail_dir.mkdir(parents=True, exist_ok=True)

    thumbnail_path = thumbnail_dir / f"{upload_id}.jpg"

    command = [
        "/usr/bin/ffmpeg",
        "-i", video_path,
        "-ss", "00:00:01.000",  # 👈 capture at 1 second
        "-vframes", "1",
        "-q:v", "2",            # quality (lower = better)
        str(thumbnail_path)
    ]

    result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
    
    if result.returncode != 0:
        print(f"FFmpeg failed: {result.stderr}")
    
    
    # ❗ verify file was actually created
    if not thumbnail_path.exists():
        raise Exception("Thumbnail generation failed")

    return f"/static/videos/thumbnails/{upload_id}.jpg"

class TempFileWrapper:
    def __init__(self, path, upload_id, content_type):
        ext = Path(path).suffix or ".bin"
        self.file = open(path, "rb")
        self.filename = f"{upload_id}"
        self.content_type = content_type

    def close(self):
        if self.file:
            self.file.close()

def process_image(image_path: str, upload_id: str) -> str:
    img = Image.open(image_path)

    # Convert to RGB (important for PNG → JPG)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    output_path = f"static/media/{upload_id}_{int(time.time())}.jpg"

    # Resize (optional but recommended)
    img.thumbnail((1920, 1920))  # max resolution

    # Compress
    img.save(output_path, "JPEG", quality=75, optimize=True)

    return f"/{output_path}"

def generate_image_sizes(image_path, upload_id):
    sizes = {
        "small": (300, 300),
        "medium": (720, 720),
        "large": (1920, 1920)
    }

    urls = {}
    original = Image.open(image_path)

    for name, size in sizes.items():
        img = original.copy()
        img.thumbnail(size)

        path = f"static/media/{upload_id}_{name}.jpg"
        img.save(path, "JPEG", quality=75)

        urls[name] = f"/static/media/{upload_id}_{name}.jpg"

    return urls

def cleanup_uploads():
    now = time.time()

    for file in os.listdir(UPLOAD_DIR):
        path = os.path.join(UPLOAD_DIR, file)

        if os.path.isfile(path):
            if now - os.path.getmtime(path) > MAX_AGE:
                os.remove(path)