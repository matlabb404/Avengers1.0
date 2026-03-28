import shutil 
from pathlib import Path
import os
import boto3
import mimetypes
from botocore.exceptions import NoCredentialsError
from fastapi import HTTPException

s3_client = boto3.client(
    's3',
    aws_access_key_id='YOUR_KEY',
    aws_secret_access_key='YOUR_SECRET'
)

USE_S3 = os.getenv("USE_S3", "false").lower() == "true"

def save_file(file, folder_path: str) -> str:
    file_name = file.filename

    # Try to get extension from MIME type
    if not ext:
        mime_type = getattr(file, "content_type", None)
        ext = mimetypes.guess_extension(mime_type) if mime_type else ".bin"

    # file_name += ext

    full_path = f"{folder_path}/{file_name}"

    if USE_S3:
        return save_file_to_s3(file, "your-bucket-name", full_path)
    else:
        # Your existing VPS/Local logic
        dest = Path(f"static/{folder_path}/{file.filename}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return str(dest)

def save_file_to_s3(file, bucket_name: str, s3_path: str) -> str:
    try:
        # Move cursor to the beginning of the file
        file.file.seek(0) 
        s3_client.upload_fileobj(file.file, bucket_name, s3_path)
        return f"https://{bucket_name}.s3.amazonaws.com/{s3_path}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 Upload Failed: {str(e)}")
