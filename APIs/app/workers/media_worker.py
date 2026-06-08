"""
arq worker for media post-processing.

Runs as its own process:  arq app.workers.media_worker.WorkerSettings

What it does:
  - process_media(asset_id): for a freshly-UPLOADED video, pull the original
    from R2, extract a poster frame (ffmpeg), read width/height/duration
    (ffprobe), compute a blurhash from the poster, upload the poster, and flip
    the asset to READY. (Images are already READY at finalize — they never get
    enqueued.)
  - reap_orphans (cron, every 10 min): clears presigned-but-never-uploaded assets.

DB + ffmpeg + boto3 are all blocking, so the actual work runs in a thread via
asyncio.to_thread and never blocks the arq event loop.

Place at: app/workers/media_worker.py   (add an empty app/workers/__init__.py)
Deps:     pip install arq blurhash-python   (ffprobe ships with ffmpeg)
"""
import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone

import blurhash
from arq import cron
from PIL import Image

from app.config.db.postgresql import SessionLocal
from app.models.media_model import MediaAsset, MediaKind, MediaStatus
from app.models import (  
    account_model,
    booking_model,
    customer_model,
    vendor_model,
    service_model,
    payment_model,
    api_test_model,
    social_model,
)
from app.modules import media_module
from app.services import queue
from app.services.media import r2

logger = logging.getLogger(__name__)

FFMPEG = "/usr/bin/ffmpeg"
FFPROBE = "/usr/bin/ffprobe"   # ships with ffmpeg; adjust if your path differs
MAX_TRIES = 3


# ─────────────────────────────────────────────────────────────
# arq job entrypoints (async) — offload blocking work to a thread
# ─────────────────────────────────────────────────────────────

async def process_media(ctx, asset_id: str):
    try:
        await asyncio.to_thread(_process_media_sync, asset_id)
    except Exception:
        logger.exception("process_media failed for asset=%s (try %s)", asset_id, ctx["job_try"])
        # Let arq retry transient failures; only flag FAILED once tries run out.
        if ctx["job_try"] >= MAX_TRIES:
            await asyncio.to_thread(_mark_failed, asset_id, "Processing failed after retries")
        raise


async def reap_orphans_job(ctx):
    await asyncio.to_thread(_reap_orphans_sync)


# ─────────────────────────────────────────────────────────────
# Blocking implementations
# ─────────────────────────────────────────────────────────────

def _process_media_sync(asset_id: str) -> None:
    db = SessionLocal()
    tmpdir = None
    try:
        asset = db.query(MediaAsset).filter(MediaAsset.id == asset_id).first()
        if not asset:
            return
        if asset.status == MediaStatus.READY:
            return  # idempotent — already done
        if asset.status not in (MediaStatus.UPLOADED, MediaStatus.PROCESSING):
            return

        asset.status = MediaStatus.PROCESSING
        db.commit()

        tmpdir = tempfile.mkdtemp(prefix="media_")
        src = os.path.join(tmpdir, "src")
        r2.download(asset.object_key, src)

        if asset.kind == MediaKind.VIDEO:
            width, height, duration_ms = _probe(src)

            poster = os.path.join(tmpdir, "poster.jpg")
            _poster(src, poster)
            poster_key = _poster_key(asset.object_key)
            r2.upload_file(poster, poster_key, "image/jpeg")

            asset.width = width or asset.width
            asset.height = height or asset.height
            asset.duration_ms = duration_ms or asset.duration_ms
            asset.derivatives = {"thumbnail": r2.public_url(poster_key)}
            if not asset.blurhash:
                asset.blurhash = _blurhash(poster)
        # MediaKind.FILE: nothing to derive

        asset.status = MediaStatus.READY
        asset.ready_at = datetime.now(timezone.utc)
        asset.failure_reason = None
        db.commit()
        logger.info("Media asset %s -> READY", asset_id)

    finally:
        db.close()
        if tmpdir and os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir, ignore_errors=True)


def _mark_failed(asset_id: str, reason: str) -> None:
    db = SessionLocal()
    try:
        asset = db.query(MediaAsset).filter(MediaAsset.id == asset_id).first()
        if asset and asset.status != MediaStatus.READY:
            asset.status = MediaStatus.FAILED
            asset.failure_reason = reason[:500]
            db.commit()
    finally:
        db.close()


def _reap_orphans_sync() -> None:
    db = SessionLocal()
    try:
        media_module.reap_orphans(db)
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
# ffmpeg / ffprobe / blurhash helpers
# ─────────────────────────────────────────────────────────────

def _probe(path: str):
    """Return (width, height, duration_ms) from the first video stream."""
    out = subprocess.run(
        [FFPROBE, "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", path],
        capture_output=True, text=True,
    )
    try:
        data = json.loads(out.stdout or "{}")
    except json.JSONDecodeError:
        return None, None, None

    vstream = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "video"), None
    )
    width = vstream.get("width") if vstream else None
    height = vstream.get("height") if vstream else None

    duration = data.get("format", {}).get("duration")
    duration_ms = int(float(duration) * 1000) if duration else None
    return width, height, duration_ms


def _poster(video_path: str, out_path: str) -> None:
    """Grab a frame ~1s in; fall back to the first frame for very short clips."""
    seek = [FFMPEG, "-y", "-ss", "00:00:01.000", "-i", video_path,
            "-frames:v", "1", "-q:v", "3", out_path]
    r = subprocess.run(seek, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0 or not os.path.exists(out_path):
        first = [FFMPEG, "-y", "-i", video_path, "-frames:v", "1", "-q:v", "3", out_path]
        r = subprocess.run(first, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if r.returncode != 0 or not os.path.exists(out_path):
            raise RuntimeError(f"ffmpeg poster generation failed: {r.stderr}")


def _blurhash(image_path: str) -> str:
    """Downscale first (blurhash only needs a tiny image) then encode 4x3."""
    with Image.open(image_path) as im:
        im = im.convert("RGB")
        im.thumbnail((100, 100))
        return blurhash.encode(im, x_components=4, y_components=3)


def _poster_key(object_key: str) -> str:
    base = object_key.rsplit(".", 1)[0]
    return f"{base}_poster.jpg"


# ─────────────────────────────────────────────────────────────
# arq worker settings
# ─────────────────────────────────────────────────────────────

class WorkerSettings:
    functions = [process_media]
    cron_jobs = [cron(reap_orphans_job, minute=set(range(0, 60, 10)))]  # every 10 min
    redis_settings = queue.redis_settings()
    max_jobs = 10
    job_timeout = 600   # seconds — generous for large video
    max_tries = MAX_TRIES
    keep_result = 3600