"""Design patterns implementation for telegram-dl package."""

from abc import ABC, abstractmethod
from typing import Any, Callable, List, Optional, Protocol
from datetime import datetime
from pathlib import Path
import asyncio
from tenacity import (
    AsyncRetrying,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from tqdm import tqdm

from .models import (
    DownloadConfig,
    DownloadProgress,
    DownloadResult,
    DownloadStatus,
    VideoMetadata,
)
from .exceptions import DownloadError


class RetryStrategy(ABC):
    """Abstract base class for retry strategies."""

    @abstractmethod
    def get_retry_callable(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Get retry callable."""
        pass


class ExponentialBackoffRetry(RetryStrategy):
    """Exponential backoff retry strategy."""

    def __init__(
        self, max_attempts: int = 3, min_wait: float = 1.0, max_wait: float = 10.0
    ):
        self.max_attempts = max_attempts
        self.min_wait = min_wait
        self.max_wait = max_wait

    def get_retry_callable(
        self, func: Callable, *args: Any, **kwargs: Any
    ) -> AsyncRetrying:
        """Get exponential backoff retry callable."""
        return AsyncRetrying(
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_exponential(min=self.min_wait, max=self.max_wait),
            retry=retry_if_exception_type(Exception),
        )


class FixedDelayRetry(RetryStrategy):
    """Fixed delay retry strategy."""

    def __init__(self, max_attempts: int = 3, delay: float = 1.0):
        self.max_attempts = max_attempts
        self.delay = delay

    def get_retry_callable(
        self, func: Callable, *args: Any, **kwargs: Any
    ) -> AsyncRetrying:
        """Get fixed delay retry callable."""
        return AsyncRetrying(
            stop=stop_after_attempt(self.max_attempts),
            wait=lambda x: self.delay,
            retry=retry_if_exception_type(Exception),
        )


class Observer(Protocol):
    """Observer protocol for publish-subscribe pattern."""

    def update(self, progress: DownloadProgress) -> None:
        """Update observer with progress."""
        pass


class Subject:
    """Subject class for observer pattern."""

    def __init__(self) -> None:
        self._observers: List[Observer] = []

    def attach(self, observer: Observer) -> None:
        """Attach an observer."""
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        """Detach an observer."""
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, progress: DownloadProgress) -> None:
        """Notify all observers."""
        for observer in self._observers:
            observer.update(progress)


class ProgressBarObserver(Observer):
    """Progress bar observer using tqdm."""

    def __init__(self) -> None:
        self._bars: dict[int, tqdm] = {}

    def update(self, progress: DownloadProgress) -> None:
        """Update progress bar."""
        if progress.video_id not in self._bars:
            self._bars[progress.video_id] = tqdm(
                total=progress.total_bytes,
                unit="B",
                unit_scale=True,
                desc=progress.filename[:30],
            )

        bar = self._bars[progress.video_id]
        bar.n = progress.bytes_downloaded
        bar.refresh()

        if progress.status in (DownloadStatus.COMPLETED, DownloadStatus.FAILED):
            bar.close()
            del self._bars[progress.video_id]


class LoggingObserver(Observer):
    """Logging observer."""

    def __init__(self, logger: Optional[Any] = None) -> None:
        self.logger = logger

    def update(self, progress: DownloadProgress) -> None:
        """Log progress update."""
        if self.logger:
            self.logger.info(
                f"{progress.filename}: {progress.status.value} "
                f"({progress.percentage:.1f}%)"
            )


class DownloadSubject(Subject):
    """Subject for download progress notifications."""

    def __init__(self) -> None:
        super().__init__()
        self._progress: dict[int, DownloadProgress] = {}

    def update_progress(
        self,
        video_id: int,
        filename: str,
        status: DownloadStatus,
        bytes_downloaded: int = 0,
        total_bytes: int = 0,
        speed: float = 0,
        elapsed: float = 0,
    ) -> None:
        """Update progress and notify observers."""
        percentage = (bytes_downloaded / total_bytes * 100) if total_bytes > 0 else 0

        progress = DownloadProgress(
            video_id=video_id,
            filename=filename,
            status=status,
            bytes_downloaded=bytes_downloaded,
            total_bytes=total_bytes,
            percentage=percentage,
            speed=speed,
            elapsed_time=elapsed,
        )

        self._progress[video_id] = progress
        self.notify(progress)

    def get_progress(self, video_id: int) -> Optional[DownloadProgress]:
        """Get progress for specific video."""
        return self._progress.get(video_id)


class Repository(ABC):
    """Abstract base class for repository pattern."""

    @abstractmethod
    async def get_all(self) -> List[VideoMetadata]:
        """Get all items."""
        pass

    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[VideoMetadata]:
        """Get item by ID."""
        pass


class VideoRepository(Repository):
    """Repository for video metadata."""

    def __init__(self, client: Any, channel_entity: Any):
        self._client = client
        self._channel_entity = channel_entity
        self._videos_cache: List[VideoMetadata] = []
        self._videos_map: dict[int, VideoMetadata] = {}
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Ensure videos are loaded."""
        if not self._initialized:
            await self._load_videos()
            self._initialized = True

    async def _load_videos(self) -> None:
        """Load videos from Telegram."""
        self._videos_cache = []
        self._videos_map = {}

        async for message in self._client.iter_messages(
            self._channel_entity, reverse=True
        ):
            if message.video:
                video = VideoMetadata(
                    id=message.id,
                    name=message.file.name
                    if message.file and message.file.name
                    else f"video_{message.id}.mp4",
                    size=message.file.size if message.file else 0,
                    date=message.date,
                    mime_type=message.file.mime_type if message.file else None,
                    duration=message.video.duration if message.video else None,
                    width=message.video.width if message.video else None,
                    height=message.video.height if message.video else None,
                )
                self._videos_cache.append(video)
                self._videos_map[video.id] = video

    async def get_all(self) -> List[VideoMetadata]:
        """Get all videos."""
        await self._ensure_initialized()
        return self._videos_cache.copy()

    async def get_by_id(self, id: int) -> Optional[VideoMetadata]:
        """Get video by ID."""
        await self._ensure_initialized()
        return self._videos_map.get(id)

    async def refresh(self) -> None:
        """Refresh videos cache."""
        self._initialized = False
        await self._ensure_initialized()


class Builder(ABC):
    """Abstract base class for builder pattern."""

    @abstractmethod
    def reset(self) -> None:
        """Reset builder."""
        pass


class DownloadTaskBuilder(Builder):
    """Builder for download tasks."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Reset the builder."""
        self._video: Optional[VideoMetadata] = None
        self._output_dir: Optional[Path] = None
        self._retry_strategy: Optional[RetryStrategy] = None
        self._skip_existing: bool = True
        self._progress_subject: Optional[DownloadSubject] = None

    def set_video(self, video: VideoMetadata) -> "DownloadTaskBuilder":
        """Set video to download."""
        self._video = video
        return self

    def set_output_dir(self, output_dir: Path) -> "DownloadTaskBuilder":
        """Set output directory."""
        self._output_dir = output_dir
        return self

    def set_retry_strategy(self, strategy: RetryStrategy) -> "DownloadTaskBuilder":
        """Set retry strategy."""
        self._retry_strategy = strategy
        return self

    def set_skip_existing(self, skip: bool) -> "DownloadTaskBuilder":
        """Set skip existing files."""
        self._skip_existing = skip
        return self

    def set_progress_subject(self, subject: DownloadSubject) -> "DownloadTaskBuilder":
        """Set progress subject."""
        self._progress_subject = subject
        return self

    def build(self) -> dict[str, Any]:
        """Build download task."""
        if not self._video:
            raise ValueError("Video is required")
        if not self._output_dir:
            raise ValueError("Output directory is required")

        return {
            "video": self._video,
            "output_dir": self._output_dir,
            "retry_strategy": self._retry_strategy,
            "skip_existing": self._skip_existing,
            "progress_subject": self._progress_subject,
        }


class Factory(ABC):
    """Abstract base class for factory pattern."""

    @abstractmethod
    def create(self, *args: Any, **kwargs: Any) -> Any:
        """Create instance."""
        pass


class RetryStrategyFactory(Factory):
    """Factory for retry strategies."""

    @staticmethod
    def create(
        strategy_type: str, max_attempts: int = 3, delay: float = 1.0
    ) -> RetryStrategy:
        """Create retry strategy by type."""
        strategies = {
            "exponential": ExponentialBackoffRetry,
            "linear": FixedDelayRetry,
            "fixed": FixedDelayRetry,
        }

        strategy_class = strategies.get(strategy_type.lower(), ExponentialBackoffRetry)

        if strategy_type.lower() == "exponential":
            return strategy_class(max_attempts=max_attempts)
        return strategy_class(max_attempts=max_attempts, delay=delay)


class ConfigFactory(Factory):
    """Factory for configuration."""

    @staticmethod
    def create_download_config(
        output_dir: str = "./telegram_videos",
        max_retries: int = 3,
        skip_existing: bool = True,
    ) -> DownloadConfig:
        """Create download configuration."""
        return DownloadConfig(
            output_dir=Path(output_dir),
            max_retries=max_retries,
            skip_existing=skip_existing,
        )
