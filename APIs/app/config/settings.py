import os
from functools import lru_cache
from dotenv import load_dotenv

# Load .env file (does nothing in production if vars are set elsewhere)
load_dotenv()

class Settings:
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    
    # Paystack
    PAYSTACK_SECRET_KEY: str = os.getenv("PAYSTACK_SECRET_KEY", "")
    PAYSTACK_PUBLIC_KEY: str = os.getenv("PAYSTACK_PUBLIC_KEY", "")
    
    # AWS
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_S3_BUCKET: str = os.getenv("AWS_S3_BUCKET", "")
    USE_S3: bool = os.getenv("USE_S3", "false").lower() == "true"

    # Cloudflare R2 (S3-compatible)
    R2_ACCOUNT_ID: str = os.getenv("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET: str = os.getenv("R2_BUCKET", "")
    R2_PUBLIC_BASE_URL: str = os.getenv("R2_PUBLIC_BASE_URL", "") 

    # ── Media uploads (R2 presign) ──────────────────────────────────────────
    MEDIA_MAX_UPLOAD_BYTES: int = int(os.getenv("MEDIA_MAX_UPLOAD_BYTES", str(512 * 1024 * 1024)))        # 512 MB
    MEDIA_MULTIPART_THRESHOLD_BYTES: int = int(os.getenv("MEDIA_MULTIPART_THRESHOLD_BYTES", str(8 * 1024 * 1024)))  # >8 MB -> multipart
    MEDIA_MULTIPART_PART_BYTES: int = int(os.getenv("MEDIA_MULTIPART_PART_BYTES", str(8 * 1024 * 1024)))  # 8 MB parts (>=5 MiB required)
    MEDIA_PRESIGN_EXPIRY_SECONDS: int = int(os.getenv("MEDIA_PRESIGN_EXPIRY_SECONDS", "900"))             # 15 min
    MEDIA_PENDING_TTL_SECONDS: int = int(os.getenv("MEDIA_PENDING_TTL_SECONDS", "3600"))                  # reap after 1 h

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Booking timeouts
    BOOKING_PAYMENT_TIMEOUT_MINUTES: int = int(
        os.getenv("BOOKING_PAYMENT_TIMEOUT_MINUTES", "15")
    )
    
    # Platform
    PLATFORM_FEE_PERCENTAGE: float = float(
        os.getenv("PLATFORM_FEE_PERCENTAGE", "10")
    )
    PAYMENT_CALLBACK_URL: str = os.getenv(
        "PAYMENT_CALLBACK_URL", 
        "http://localhost:8000/payment/callback"
    )


    # ── Push Notifications ─────────────────────────────────────────
    # ── FCM (Android) ──
    FIREBASE_CREDENTIALS_PATH: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "")             # path to service-account JSON

    # ── APNs (iOS) ──
    APNS_AUTH_KEY_PATH: str = os.getenv("APNS_AUTH_KEY_PATH", "")                           # path to the .p8 auth key
    APNS_KEY_ID: str = os.getenv("APNS_KEY_ID", "")                                         # the key id (kid)
    APNS_TEAM_ID: str = os.getenv("APNS_TEAM_ID", "")                                       # Apple Team ID (iss)
    APNS_BUNDLE_ID: str = os.getenv("APNS_BUNDLE_ID", "")                                   # app bundle id (apns-topic)
    APNS_USE_SANDBOX: bool = os.getenv("APNS_USE_SANDBOX", "false").lower() == "true"       # True for dev builds, False for prod
    
    def validate(self):
        """Fail fast at startup if critical secrets are missing."""
        required = {
            "DATABASE_URL": self.DATABASE_URL,
            "JWT_SECRET_KEY": self.JWT_SECRET_KEY,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Check your .env file."
            )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance. Use this everywhere instead of os.getenv."""
    settings = Settings()
    settings.validate()
    return settings