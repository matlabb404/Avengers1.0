"""
Manual AWS SigV4 query-string presigning for Cloudflare R2.

Why this exists: botocore >= 1.36 injects a default CRC32 checksum into
put_object/upload_part presigned URLs. The checksum params become part of the
*signed* canonical request, but the client (the phone) never sends them, so R2
recomputes a different signature -> SignatureDoesNotMatch. This module signs by
hand and never adds a checksum, so it is immune to SDK version churn.

Only presigning is done here. Server-side ops (head, multipart create/complete/
abort, delete, download, upload_file) stay on boto3 in r2.py — they aren't
affected by the presign checksum bug.
"""
import hashlib
import hmac
from datetime import datetime, timezone
from urllib.parse import quote


_ALGORITHM = "AWS4-HMAC-SHA256"
_SERVICE = "s3"
_REGION = "auto"                 # R2 always uses 'auto'
_UNSIGNED = "UNSIGNED-PAYLOAD"


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _signing_key(secret: str, date_stamp: str) -> bytes:
    k_date = _hmac(("AWS4" + secret).encode("utf-8"), date_stamp)
    k_region = _hmac(k_date, _REGION)
    k_service = _hmac(k_region, _SERVICE)
    return _hmac(k_service, "aws4_request")


def _uri_encode(value: str, encode_slash: bool) -> str:
    # AWS canonicalization: encode everything except unreserved chars.
    safe = "-_.~" if encode_slash else "-_.~/"
    return quote(value, safe=safe)


def _presign(
    *,
    method: str,
    host: str,
    object_key: str,
    access_key: str,
    secret_key: str,
    bucket: str,
    expires: int,
    signed_headers: dict[str, str],
    extra_query: dict[str, str] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    # Path is /{bucket}/{key} (path-style). Each segment encoded, slashes kept.
    canonical_uri = "/" + _uri_encode(f"{bucket}/{object_key}", encode_slash=False)

    # Canonical headers (lowercased names, sorted). Always include host.
    headers = {k.lower(): v.strip() for k, v in signed_headers.items()}
    headers["host"] = host
    sorted_header_names = sorted(headers)
    canonical_headers = "".join(f"{n}:{headers[n]}\n" for n in sorted_header_names)
    signed_headers_str = ";".join(sorted_header_names)

    credential = f"{access_key}/{date_stamp}/{_REGION}/{_SERVICE}/aws4_request"

    query = {
        "X-Amz-Algorithm": _ALGORITHM,
        "X-Amz-Credential": credential,
        "X-Amz-Date": amz_date,
        "X-Amz-Expires": str(expires),
        "X-Amz-SignedHeaders": signed_headers_str,
    }
    if extra_query:
        query.update(extra_query)

    # Canonical query string: sorted by key, both key and value URI-encoded.
    canonical_query = "&".join(
        f"{_uri_encode(k, True)}={_uri_encode(v, True)}"
        for k, v in sorted(query.items())
    )

    canonical_request = "\n".join([
        method,
        canonical_uri,
        canonical_query,
        canonical_headers,
        signed_headers_str,
        _UNSIGNED,
    ])

    string_to_sign = "\n".join([
        _ALGORITHM,
        amz_date,
        f"{date_stamp}/{_REGION}/{_SERVICE}/aws4_request",
        _sha256_hex(canonical_request.encode("utf-8")),
    ])

    signature = hmac.new(
        _signing_key(secret_key, date_stamp),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"https://{host}{canonical_uri}?{canonical_query}&X-Amz-Signature={signature}"


# ── Public API (mirrors the boto3-based functions they replace) ──────────────

def presign_put(
    key: str,
    content_type: str,
    expires: int,
    *,
    host: str,
    access_key: str,
    secret_key: str,
    bucket: str,
) -> str:
    """Single-shot PUT. content-type is signed, so the client must send exactly
    this Content-Type header."""
    return _presign(
        method="PUT",
        host=host,
        object_key=key,
        access_key=access_key,
        secret_key=secret_key,
        bucket=bucket,
        expires=expires,
        signed_headers={"content-type": content_type},
    )


def presign_part(
    key: str,
    upload_id: str,
    part_number: int,
    expires: int,
    *,
    host: str,
    access_key: str,
    secret_key: str,
    bucket: str,
) -> str:
    """Multipart part PUT. No content-type signed (the client sends raw bytes
    with octet-stream), so only host is in the signed headers."""
    return _presign(
        method="PUT",
        host=host,
        object_key=key,
        access_key=access_key,
        secret_key=secret_key,
        bucket=bucket,
        expires=expires,
        signed_headers={},
        extra_query={
            "partNumber": str(part_number),
            "uploadId": upload_id,
        },
    )
