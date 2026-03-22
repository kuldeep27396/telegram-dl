"""Tests for telegram_dl package."""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from telegram_dl.models import (
    ChannelInfo,
    DownloadConfig,
    DownloadProgress,
    DownloadResult,
    DownloadStatus,
    LogLevel,
    TelegramCredentials,
    VideoMetadata,
)
from telegram_dl.exceptions import (
    AuthenticationError,
    ChannelNotFoundError,
    ConfigurationError,
    DownloadError,
    TelegramDLError,
    VideoNotFoundError,
)
from telegram_dl.patterns import (
    ExponentialBackoffRetry,
    Factory,
    FixedDelayRetry,
    Observer,
    ProgressBarObserver,
    RetryStrategyFactory,
    Subject,
)


class TestTelegramCredentials:
    """Tests for TelegramCredentials model."""

    def test_valid_credentials(self):
        """Test creating valid credentials."""
        creds = TelegramCredentials(
            api_id=12345,
            api_hash="abcd1234abcd1234abcd1234abcd1234",
            phone="+1234567890",
        )
        assert creds.api_id == 12345
        assert creds.api_hash == "abcd1234abcd1234abcd1234abcd1234"
        assert creds.phone == "+1234567890"

    def test_invalid_api_id(self):
        """Test that negative API ID is rejected."""
        with pytest.raises(ValueError):
            TelegramCredentials(
                api_id=-1,
                api_hash="abcd1234abcd1234abcd1234abcd1234",
                phone="+1234567890",
            )

    def test_invalid_phone_format(self):
        """Test that invalid phone format is rejected."""
        with pytest.raises(ValueError):
            TelegramCredentials(
                api_id=12345,
                api_hash="abcd1234abcd1234abcd1234abcd1234",
                phone="1234567890",  # Missing +
            )

    def test_api_hash_validation(self):
        """Test API hash validation."""
        with pytest.raises(ValueError):
            TelegramCredentials(
                api_id=12345,
                api_hash="invalid!!!hash",
                phone="+1234567890",
            )


class TestDownloadConfig:
    """Tests for DownloadConfig model."""

    def test_default_config(self):
        """Test default configuration."""
        config = DownloadConfig()
        assert config.output_dir == Path("./telegram_videos")
        assert config.max_retries == 3
        assert config.skip_existing is True
        assert config.parallel_downloads == 1

    def test_custom_config(self, tmp_path):
        """Test custom configuration."""
        config = DownloadConfig(
            output_dir=tmp_path,
            max_retries=5,
            skip_existing=False,
        )
        assert config.output_dir == tmp_path
        assert config.max_retries == 5
        assert config.skip_existing is False


class TestVideoMetadata:
    """Tests for VideoMetadata model."""

    def test_valid_video(self):
        """Test creating valid video metadata."""
        video = VideoMetadata(
            id=123,
            name="test_video.mp4",
            size=1024000,
            duration=120,
        )
        assert video.id == 123
        assert video.name == "test_video.mp4"
        assert video.size == 1024000
        assert video.extension == "mp4"

    def test_empty_name_rejected(self):
        """Test that empty name is rejected."""
        with pytest.raises(ValueError):
            VideoMetadata(id=123, name="   ")


class TestDownloadProgress:
    """Tests for DownloadProgress model."""

    def test_progress_calculation(self):
        """Test progress percentage calculation."""
        progress = DownloadProgress(
            video_id=1,
            filename="test.mp4",
            status=DownloadStatus.DOWNLOADING,
            bytes_downloaded=500,
            total_bytes=1000,
        )
        # Percentage is computed from bytes_downloaded and total_bytes
        expected_percentage = (500 / 1000) * 100 if 1000 > 0 else 0
        assert progress.percentage == expected_percentage

    def test_speed_formatted(self):
        """Test speed formatting."""
        progress = DownloadProgress(
            video_id=1,
            filename="test.mp4",
            status=DownloadStatus.DOWNLOADING,
            bytes_downloaded=500,
            total_bytes=1000,
            speed=1024 * 1024,
        )
        assert "MB/s" in progress.speed_formatted


class TestDownloadResult:
    """Tests for DownloadResult model."""

    def test_successful_result(self):
        """Test successful download result."""
        result = DownloadResult(
            video_id=1,
            filename="test.mp4",
            status=DownloadStatus.COMPLETED,
            file_path="/path/to/test.mp4",
            file_size=1024000,
        )
        assert result.success is True

    def test_failed_result(self):
        """Test failed download result."""
        result = DownloadResult(
            video_id=1,
            filename="test.mp4",
            status=DownloadStatus.FAILED,
            error="Network error",
        )
        assert result.success is False


class TestExceptions:
    """Tests for custom exceptions."""

    def test_base_exception(self):
        """Test base exception."""
        exc = TelegramDLError("Test error", {"key": "value"})
        assert exc.message == "Test error"
        assert exc.details == {"key": "value"}

    def test_authentication_error(self):
        """Test authentication error."""
        exc = AuthenticationError()
        assert exc.message == "Authentication failed"

    def test_channel_not_found_error(self):
        """Test channel not found error."""
        exc = ChannelNotFoundError(12345)
        assert exc.details["channel_id"] == 12345

    def test_video_not_found_error(self):
        """Test video not found error."""
        exc = VideoNotFoundError(67890)
        assert exc.details["video_id"] == 67890


class TestPatterns:
    """Tests for design patterns."""

    def test_observer_pattern(self):
        """Test observer pattern."""
        subject = Subject()
        observer = MagicMock(spec=Observer)

        subject.attach(observer)
        progress = DownloadProgress(
            video_id=1,
            filename="test.mp4",
            status=DownloadStatus.DOWNLOADING,
        )
        subject.notify(progress)

        observer.update.assert_called_once_with(progress)

    def test_subject_detach(self):
        """Test detaching observer."""
        subject = Subject()
        observer = MagicMock(spec=Observer)

        subject.attach(observer)
        subject.detach(observer)

        progress = DownloadProgress(
            video_id=1,
            filename="test.mp4",
            status=DownloadStatus.DOWNLOADING,
        )
        subject.notify(progress)

        observer.update.assert_not_called()

    def test_exponential_backoff_retry(self):
        """Test exponential backoff retry strategy."""
        strategy = ExponentialBackoffRetry(max_attempts=3, min_wait=1.0, max_wait=10.0)
        retry = strategy.get_retry_callable(MagicMock())
        assert retry is not None

    def test_fixed_delay_retry(self):
        """Test fixed delay retry strategy."""
        strategy = FixedDelayRetry(max_attempts=3, delay=2.0)
        retry = strategy.get_retry_callable(MagicMock())
        assert retry is not None

    def test_retry_strategy_factory_exponential(self):
        """Test retry strategy factory with exponential."""
        strategy = RetryStrategyFactory.create("exponential", max_attempts=5)
        assert isinstance(strategy, ExponentialBackoffRetry)

    def test_retry_strategy_factory_fixed(self):
        """Test retry strategy factory with fixed."""
        strategy = RetryStrategyFactory.create("fixed", max_attempts=3, delay=2.0)
        assert isinstance(strategy, FixedDelayRetry)


class TestDownloadStatus:
    """Tests for DownloadStatus enum."""

    def test_all_statuses_exist(self):
        """Test all expected statuses exist."""
        assert DownloadStatus.PENDING.value == "PENDING"
        assert DownloadStatus.DOWNLOADING.value == "DOWNLOADING"
        assert DownloadStatus.COMPLETED.value == "COMPLETED"
        assert DownloadStatus.FAILED.value == "FAILED"
        assert DownloadStatus.SKIPPED.value == "SKIPPED"


class TestLogLevel:
    """Tests for LogLevel enum."""

    def test_all_levels_exist(self):
        """Test all expected log levels exist."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"


class TestChannelInfo:
    """Tests for ChannelInfo model."""

    def test_channel_info(self):
        """Test channel info creation."""
        channel = ChannelInfo(
            id=-1001234567890,
            title="Test Channel",
            username="test_channel",
            is_channel=True,
        )
        assert channel.id == -1001234567890
        assert channel.title == "Test Channel"
        assert channel.username == "test_channel"
        assert channel.is_channel is True
        assert channel.is_group is False


class TestIntegration:
    """Integration tests (mocked)."""

    def test_credentials_to_dict(self):
        """Test credentials serialization."""
        creds = TelegramCredentials(
            api_id=12345,
            api_hash="abcd1234abcd1234abcd1234abcd1234",
            phone="+1234567890",
        )
        data = creds.model_dump()
        assert data["api_id"] == 12345
        assert data["phone"] == "+1234567890"

    def test_video_metadata_to_dict(self):
        """Test video metadata serialization."""
        video = VideoMetadata(
            id=1,
            name="test.mp4",
            size=1024,
            duration=120,
        )
        data = video.model_dump()
        assert data["id"] == 1
        assert data["name"] == "test.mp4"
        # extension is a property, test it separately
        assert video.extension == "mp4"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
