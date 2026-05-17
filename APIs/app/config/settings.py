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