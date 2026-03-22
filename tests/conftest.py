"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def valid_credentials():
    """Fixture providing valid test credentials."""
    from telegram_dl.models import TelegramCredentials

    return TelegramCredentials(
        api_id=12345,
        api_hash="abcd1234abcd1234abcd1234abcd1234",
        phone="+1234567890",
    )


@pytest.fixture
def valid_download_config(tmp_path):
    """Fixture providing valid download configuration."""
    from telegram_dl.models import DownloadConfig

    return DownloadConfig(
        output_dir=tmp_path / "videos",
        max_retries=3,
        skip_existing=True,
    )


@pytest.fixture
def sample_video_metadata():
    """Fixture providing sample video metadata."""
    from telegram_dl.models import VideoMetadata

    return VideoMetadata(
        id=123,
        name="test_video.mp4",
        size=1024000,
        duration=120,
        width=1920,
        height=1080,
    )


@pytest.fixture
def mock_telegram_client():
    """Fixture providing a mock Telegram client."""
    client = MagicMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.get_entity = AsyncMock()
    client.iter_messages = MagicMock()
    client.iter_dialogs = MagicMock()
    return client
