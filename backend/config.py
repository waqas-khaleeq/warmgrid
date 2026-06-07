import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()


class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "changeme-secret-key-not-for-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./warmgrid.db")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
    DEFAULT_SEND_HOUR_START: int = int(os.getenv("DEFAULT_SEND_HOUR_START", "7"))
    DEFAULT_SEND_HOUR_END: int = int(os.getenv("DEFAULT_SEND_HOUR_END", "11"))
    WEEKLY_VOLUME_INCREASE: int = int(os.getenv("WEEKLY_VOLUME_INCREASE", "5"))
    MAX_DAILY_VOLUME: int = int(os.getenv("MAX_DAILY_VOLUME", "50"))
    IMAP_POLL_INTERVAL_MINUTES: int = int(os.getenv("IMAP_POLL_INTERVAL_MINUTES", "120"))
    HEALTH_CHECK_INTERVAL_HOURS: int = int(os.getenv("HEALTH_CHECK_INTERVAL_HOURS", "24"))

    def get_fernet(self) -> Fernet:
        key = self.ENCRYPTION_KEY
        if not key:
            raise ValueError("ENCRYPTION_KEY is not set in .env file")
        key_bytes = key.encode() if isinstance(key, str) else key
        return Fernet(key_bytes)

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        f = self.get_fernet()
        return f.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        f = self.get_fernet()
        return f.decrypt(ciphertext.encode()).decode()


settings = Settings()
