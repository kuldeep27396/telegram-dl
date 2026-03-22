"""Core client implementation following SOLID principles.

Single Responsibility: Each class has one reason to change
Open/Closed: Open for extension, closed for modification
Liskov Substitution: Subclasses can replace parent classes
Interface Segregation: Many specific interfaces instead of one general
Dependency Inversion: Depend on abstractions, not concretions
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, List, Optional, Protocol

from telethon import TelegramClient
from telethon.errors import RPCError

try:
    from telethon.errors import SessionPasswordNeededError
except ImportError:
    SessionPasswordNeededError = Exception

try:
    from telethon.errors import ChannelNotFoundError as TelethonChannelNotFoundError
except ImportError:
    TelethonChannelNotFoundError = RPCError

from .exceptions import (
    AuthenticationError,
    ChannelNotFoundError,
    ConfigurationError,
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
    TelegramCredentials,
    VideoMetadata,
)
from .patterns import (
    DownloadSubject,
    DownloadTaskBuilder,
    Factory,
    LoggingObserver,
    Observer,
    ProgressBarObserver,
    RetryStrategy,
    RetryStrategyFactory,
    VideoRepository,
)


logger = logging.getLogger(__name__)


class ProgressCallback(Protocol):
    """Protocol for progress callbacks."""

    def __call__(self, progress: DownloadProgress) -> None:
        """Called when progress is updated."""
        pass


class ITelegramClient(Protocol):
    """Interface for Telegram client operations."""

    async def connect(self) -> None:
        """Connect to Telegram."""
        pass

    async def disconnect(self) -> None:
        """Disconnect from Telegram."""
        pass

    def iter_dialogs(self) -> Any:
        """Iterate dialogs."""
        pass

    def iter_messages(self, entity: Any, **kwargs: Any) -> Any:
        """Iterate messages."""
        pass

    def get_entity(self, entity: Any) -> Any:
        """Get entity."""
        pass


class TelegramDownloader:
    """Main downloader class following SOLID principles.

    Responsibilities:
    - Manage Telegram client lifecycle
    - Coordinate download operations
    - Notify observers of progress
    """

    def __init__(
        self,
        credentials: TelegramCredentials,
        config: Optional[DownloadConfig] = None,
    ):
        self._credentials = credentials
        self._config = config or DownloadConfig()
        self._client: Optional[TelegramClient] = None
        self._progress_subject = DownloadSubject()
        self._connected = False

    async def connect(self) -> "TelegramDownloader":
        """Connect to Telegram servers.

        Returns:
            Self for method chaining.
        """
        if self._connected:
            return self

        try:
            self._client = TelegramClient(
                self._config.session_name,
                self._credentials.api_id,
                self._credentials.api_hash,
            )
            await self._client.start(phone=self._credentials.phone)
            self._connected = True
            logger.info("Successfully connected to Telegram")
            return self
        except SessionPasswordNeededError as e:
            raise AuthenticationError(
                "2FA password required",
                details={"original_error": str(e)},
            ) from e
        except Exception as e:
            raise TelegramDLError(
                f"Failed to connect: {e}",
                details={"original_error": str(e)},
            ) from e

    async def disconnect(self) -> None:
        """Disconnect from Telegram servers."""
        if self._client:
            await self._client.disconnect()
            self._connected = False
            logger.info("Disconnected from Telegram")

    async def __aenter__(self) -> "TelegramDownloader":
        """Async context manager entry."""
        return await self.connect()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()

    @property
    def client(self) -> Optional[TelegramClient]:
        """Get the Telegram client."""
        return self._client

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    def attach_observer(self, observer: Observer) -> None:
        """Attach a progress observer."""
        self._progress_subject.attach(observer)

    def detach_observer(self, observer: Observer) -> None:
        """Detach a progress observer."""
        self._progress_subject.detach(observer)

    def _get_channel_repository(self, channel_id: int) -> VideoRepository:
        """Get video repository for channel."""
        if not self._client:
            raise TelegramDLError("Not connected. Call connect() first.")

        try:
            entity = self._client.loop.run_until_complete(
                self._client.get_entity(channel_id)
            )
            return VideoRepository(self._client, entity)
        except TelethonChannelNotFoundError as e:
            raise ChannelNotFoundError(
                channel_id,
                details={"original_error": str(e)},
            ) from e

    async def get_dialogs(self) -> List[ChannelInfo]:
        """Get all accessible dialogs (channels and groups).

        Returns:
            List of channel information.
        """
        if not self._client:
            raise TelegramDLError("Not connected. Call connect() first.")

        channels = []
        async for dialog in self._client.iter_dialogs():
            if dialog.is_channel or dialog.is_group:
                info = ChannelInfo(
                    id=dialog.id,
                    title=dialog.title,
                    username=dialog.entity.username
                    if hasattr(dialog.entity, "username")
                    else None,
                    is_channel=dialog.is_channel,
                    is_group=dialog.is_group,
                )
                channels.append(info)

        logger.info(f"Found {len(channels)} channels/groups")
        return channels

    async def get_channel_videos(
        self,
        channel_id: int,
        use_cache: bool = False,
    ) -> List[VideoMetadata]:
        """Get all videos from a channel.

        Args:
            channel_id: Channel ID.
            use_cache: Whether to use cached data.

        Returns:
            List of video metadata.
        """
        if not self._client:
            raise TelegramDLError("Not connected. Call connect() first.")

        try:
            entity = await self._client.get_entity(channel_id)
            repository = VideoRepository(self._client, entity)

            if not use_cache:
                await repository.refresh()

            videos = await repository.get_all()
            logger.info(f"Found {len(videos)} videos in channel {channel_id}")
            return videos

        except TelethonChannelNotFoundError as e:
            raise ChannelNotFoundError(
                channel_id,
                details={"original_error": str(e)},
            ) from e

    async def download_video(
        self,
        channel_id: int,
        video_id: int,
        output_dir: Optional[Path] = None,
        filename: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> DownloadResult:
        """Download a single video.

        Args:
            channel_id: Channel ID.
            video_id: Video message ID.
            output_dir: Output directory.
            filename: Custom filename.
            progress_callback: Progress callback function.

        Returns:
            Download result.
        """
        output_dir = output_dir or self._config.output_dir
        start_time = time.time()

        try:
            if not self._client:
                raise TelegramDLError("Not connected. Call connect() first.")

            entity = await self._client.get_entity(channel_id)
            video = None
            message = None

            async for msg in self._client.iter_messages(entity):
                if msg.id == video_id and msg.video:
                    video = VideoMetadata(
                        id=msg.id,
                        name=msg.file.name
                        if msg.file and msg.file.name
                        else f"video_{msg.id}.mp4",
                        size=msg.file.size if msg.file else 0,
                        date=msg.date,
                    )
                    message = msg
                    break

            if not video or not message:
                return DownloadResult(
                    video_id=video_id,
                    filename=filename or f"video_{video_id}.mp4",
                    status=DownloadStatus.FAILED,
                    error=f"Video {video_id} not found",
                )

            if filename:
                video.name = filename

            filepath = output_dir / video.name

            if self._config.skip_existing and filepath.exists():
                logger.info(f"Skipping existing file: {video.name}")
                self._progress_subject.update_progress(
                    video_id=video_id,
                    filename=video.name,
                    status=DownloadStatus.SKIPPED,
                )
                return DownloadResult(
                    video_id=video_id,
                    filename=video.name,
                    status=DownloadStatus.SKIPPED,
                    file_path=str(filepath),
                    file_size=filepath.stat().st_size,
                    download_time=time.time() - start_time,
                )

            self._progress_subject.update_progress(
                video_id=video_id,
                filename=video.name,
                status=DownloadStatus.DOWNLOADING,
                total_bytes=video.size,
            )

            await message.download_media(str(filepath))

            self._progress_subject.update_progress(
                video_id=video_id,
                filename=video.name,
                status=DownloadStatus.COMPLETED,
                bytes_downloaded=video.size,
                total_bytes=video.size,
            )

            if progress_callback:
                progress_callback(
                    DownloadProgress(
                        video_id=video_id,
                        filename=video.name,
                        status=DownloadStatus.COMPLETED,
                        bytes_downloaded=video.size,
                        total_bytes=video.size,
                        percentage=100,
                    )
                )

            return DownloadResult(
                video_id=video_id,
                filename=video.name,
                status=DownloadStatus.COMPLETED,
                file_path=str(filepath),
                file_size=filepath.stat().st_size,
                download_time=time.time() - start_time,
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to download video {video_id}: {error_msg}")

            self._progress_subject.update_progress(
                video_id=video_id,
                filename=filename or f"video_{video_id}.mp4",
                status=DownloadStatus.FAILED,
            )

            return DownloadResult(
                video_id=video_id,
                filename=filename or f"video_{video_id}.mp4",
                status=DownloadStatus.FAILED,
                error=error_msg,
                download_time=time.time() - start_time,
            )

    async def download_all_videos(
        self,
        channel_id: int,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[ProgressCallback] = None,
        skip_existing: Optional[bool] = None,
    ) -> List[DownloadResult]:
        """Download all videos from a channel.

        Args:
            channel_id: Channel ID.
            output_dir: Output directory.
            progress_callback: Progress callback.
            skip_existing: Skip existing files.

        Returns:
            List of download results.
        """
        output_dir = output_dir or self._config.output_dir
        skip_existing = (
            skip_existing if skip_existing is not None else self._config.skip_existing
        )

        videos = await self.get_channel_videos(channel_id)
        logger.info(f"Starting download of {len(videos)} videos")

        if progress_callback:
            self.attach_observer(_CallbackObserver(progress_callback))

        results = []
        for video in videos:
            result = await self.download_video(
                channel_id=channel_id,
                video_id=video.id,
                output_dir=output_dir,
                filename=video.name,
                progress_callback=progress_callback,
            )
            results.append(result)

        return results


class _CallbackObserver(Observer):
    """Observer that calls a callback function."""

    def __init__(self, callback: ProgressCallback) -> None:
        self._callback = callback

    def update(self, progress: DownloadProgress) -> None:
        """Call the callback."""
        self._callback(progress)


class DownloaderBuilder:
    """Builder for creating configured downloader instances.

    Follows Builder pattern for flexible configuration.
    """

    def __init__(self) -> None:
        self._credentials: Optional[TelegramCredentials] = None
        self._config: Optional[DownloadConfig] = None
        self._retry_strategy: Optional[RetryStrategy] = None
        self._observers: List[Observer] = []

    def with_credentials(
        self, api_id: int, api_hash: str, phone: str
    ) -> "DownloaderBuilder":
        """Set Telegram credentials."""
        self._credentials = TelegramCredentials(
            api_id=api_id,
            api_hash=api_hash,
            phone=phone,
        )
        return self

    def with_config(self, config: DownloadConfig) -> "DownloaderBuilder":
        """Set download configuration."""
        self._config = config
        return self

    def with_output_dir(self, output_dir: str) -> "DownloaderBuilder":
        """Set output directory."""
        if not self._config:
            self._config = DownloadConfig()
        self._config.output_dir = Path(output_dir)
        return self

    def with_retry_strategy(
        self, strategy: str, max_attempts: int = 3
    ) -> "DownloaderBuilder":
        """Set retry strategy."""
        self._retry_strategy = RetryStrategyFactory.create(strategy, max_attempts)
        return self

    def with_progress_bar(self) -> "DownloaderBuilder":
        """Add progress bar observer."""
        self._observers.append(ProgressBarObserver())
        return self

    def with_logging(self) -> "DownloaderBuilder":
        """Add logging observer."""
        self._observers.append(LoggingObserver(logger))
        return self

    def build(self) -> TelegramDownloader:
        """Build the downloader instance."""
        if not self._credentials:
            raise ConfigurationError("Credentials are required")

        downloader = TelegramDownloader(self._credentials, self._config)

        for observer in self._observers:
            downloader.attach_observer(observer)

        return downloader


def run_download(
    api_id: int,
    api_hash: str,
    phone: str,
    channel_id: int,
    output_dir: str = "./telegram_videos",
    session_name: str = "telegram_dl_session",
) -> None:
    """Synchronous entry point for downloading.

    Args:
        api_id: Telegram API ID.
        api_hash: Telegram API hash.
        phone: Phone number with country code.
        channel_id: Channel ID to download from.
        output_dir: Output directory.
        session_name: Session name.
    """
    asyncio.run(
        _run_download(api_id, api_hash, phone, channel_id, output_dir, session_name)
    )


async def _run_download(
    api_id: int,
    api_hash: str,
    phone: str,
    channel_id: int,
    output_dir: str,
    session_name: str,
) -> None:
    """Async implementation of run_download."""
    credentials = TelegramCredentials(api_id=api_id, api_hash=api_hash, phone=phone)
    config = DownloadConfig(output_dir=Path(output_dir), session_name=session_name)

    async with TelegramDownloader(credentials, config) as downloader:
        await downloader.download_all_videos(channel_id)
