"""Pydantic models for configuration and data validation."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import (
    BaseModel,
    Field,
    computed_field,
    field_validator,
    model_validator,
)


class LogLevel(str, Enum):
    """Log level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DownloadStatus(str, Enum):
    """Download status enumeration."""

    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class RetryStrategy(str, Enum):
    """Retry strategy enumeration."""

    EXPONENTIAL = "EXPONENTIAL"
    LINEAR = "LINEAR"
    FIXED = "FIXED"


class TelegramCredentials(BaseModel):
    """Telegram API credentials model.

    Validates API credentials for Telegram API access.
    """

    api_id: int = Field(..., gt=0, description="Telegram API ID")
    api_hash: str = Field(
        ..., min_length=32, max_length=64, description="Telegram API Hash"
    )
    phone: str = Field(
        ..., pattern=r"^\+[1-9]\d{6,14}$", description="Phone number with country code"
    )

    @field_validator("api_hash")
    @classmethod
    def validate_api_hash(cls, v: str) -> str:
        """Validate API hash is alphanumeric."""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("API hash must be alphanumeric")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone number format."""
        if not v.startswith("+"):
            raise ValueError("Phone number must start with +")
        return v


class DownloadConfig(BaseModel):
    """Download configuration model."""

    output_dir: Path = Field(default_factory=lambda: Path("./telegram_videos"))
    session_name: str = Field(default="telegram_dl_session")
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay: float = Field(default=1.0, gt=0)
    timeout: int = Field(default=300, gt=0)
    chunk_size: int = Field(default=1024 * 1024, gt=0)
    skip_existing: bool = Field(default=True)
    parallel_downloads: int = Field(default=1, ge=1, le=10)

    @model_validator(mode="after")
    def validate_output_dir(self) -> "DownloadConfig":
        """Validate output directory exists or can be created."""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise ValueError(f"Cannot create output directory: {e}")
        return self


class LoggingConfig(BaseModel):
    """Logging configuration model."""

    level: LogLevel = Field(default=LogLevel.INFO)
    file_path: Optional[Path] = None
    format_string: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    @model_validator(mode="after")
    def validate_file_path(self) -> "LoggingConfig":
        """Validate log file can be created."""
        if self.file_path:
            try:
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
            except PermissionError as e:
                raise ValueError(f"Cannot create log file: {e}")
        return self


class AppConfig(BaseModel):
    """Application configuration model."""

    credentials: TelegramCredentials
    download: DownloadConfig = Field(default_factory=DownloadConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


class VideoMetadata(BaseModel):
    """Video metadata model."""

    id: int
    name: str
    size: int = Field(default=0, ge=0)
    date: Optional[datetime] = None
    mime_type: Optional[str] = None
    duration: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate video name is not empty."""
        if not v.strip():
            raise ValueError("Video name cannot be empty")
        return v

    @property
    def extension(self) -> str:
        """Get file extension from name or mime type."""
        if "." in self.name:
            return self.name.rsplit(".", 1)[-1].lower()
        return "mp4"


class ChannelInfo(BaseModel):
    """Channel information model."""

    id: int
    title: str
    username: Optional[str] = None
    is_channel: bool = True
    is_group: bool = False
    video_count: int = Field(default=0, ge=0)


class DownloadProgress(BaseModel):
    """Download progress model."""

    video_id: int
    filename: str
    status: DownloadStatus
    bytes_downloaded: int = Field(default=0, ge=0)
    total_bytes: int = Field(default=0, ge=0)
    speed: float = Field(default=0.0, ge=0)
    elapsed_time: float = Field(default=0.0, ge=0)

    @computed_field
    @property
    def percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_bytes <= 0:
            return 0.0
        return min(100.0, max(0.0, (self.bytes_downloaded / self.total_bytes) * 100))

    @property
    def speed_formatted(self) -> str:
        """Format speed in human readable format."""
        if self.speed < 1024:
            return f"{self.speed:.2f} B/s"
        elif self.speed < 1024 * 1024:
            return f"{self.speed / 1024:.2f} KB/s"
        else:
            return f"{self.speed / (1024 * 1024):.2f} MB/s"


class DownloadResult(BaseModel):
    """Download result model."""

    video_id: int
    filename: str
    status: DownloadStatus
    file_path: Optional[str] = None
    file_size: int = Field(default=0, ge=0)
    download_time: float = Field(default=0.0, ge=0)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Check if download was successful."""
        return self.status == DownloadStatus.COMPLETED
