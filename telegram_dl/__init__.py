"""telegram-dl - A production-ready Python CLI tool to download videos from Telegram channels.

Example usage:
    >>> from telegram_dl import TelegramDownloader, TelegramCredentials
    >>> from telegram_dl.models import DownloadConfig
    >>> from pathlib import Path
    >>>
    >>> async def main():
    ...     credentials = TelegramCredentials(
    ...         api_id=12345,
    ...         api_hash="abc123",
    ...         phone="+1234567890"
    ...     )
    ...     async with TelegramDownloader(credentials) as dl:
    ...         videos = await dl.get_channel_videos(-1001234567890)
    ...         await dl.download_all_videos(-1001234567890)
    >>>
    >>> asyncio.run(main())
"""

from .client import (
    DownloaderBuilder,
    ITelegramClient,
    ProgressCallback,
    TelegramDownloader,
)
from .exceptions import (
    AuthenticationError,
    ChannelNotFoundError,
    ConfigurationError,
    ConnectionError,
    DownloadError,
    TelegramDLError,
    VideoNotFoundError,
)
from .models import (
    AppConfig,
    ChannelInfo,
    DownloadConfig,
    DownloadProgress,
    DownloadResult,
    DownloadStatus,
    LogLevel,
    LoggingConfig,
    RetryStrategy,
    TelegramCredentials,
    VideoMetadata,
)
from .patterns import (
    ExponentialBackoffRetry,
    Factory,
    FixedDelayRetry,
    LoggingObserver,
    Observer,
    ProgressBarObserver,
    Repository,
    RetryStrategyFactory,
    Subject,
    VideoRepository,
)

__version__ = "2.0.0"

__all__ = [
    # Version
    "__version__",
    # Client
    "TelegramDownloader",
    "DownloaderBuilder",
    "ITelegramClient",
    "ProgressCallback",
    # Config
    "AppConfig",
    "DownloadConfig",
    "LoggingConfig",
    "TelegramCredentials",
    # Models
    "ChannelInfo",
    "DownloadProgress",
    "DownloadResult",
    "DownloadStatus",
    "LogLevel",
    "RetryStrategy",
    "VideoMetadata",
    # Exceptions
    "TelegramDLError",
    "AuthenticationError",
    "ChannelNotFoundError",
    "ConfigurationError",
    "ConnectionError",
    "DownloadError",
    "VideoNotFoundError",
    # Patterns
    "Observer",
    "Subject",
    "Repository",
    "Factory",
    "RetryStrategyFactory",
    "ExponentialBackoffRetry",
    "FixedDelayRetry",
    "ProgressBarObserver",
    "LoggingObserver",
    "VideoRepository",
]
