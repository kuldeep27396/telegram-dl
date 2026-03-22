"""Custom exceptions for telegram-dl package."""

from typing import Optional


class TelegramDLError(Exception):
    """Base exception for telegram-dl package."""

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class AuthenticationError(TelegramDLError):
    """Raised when authentication fails."""

    def __init__(
        self, message: str = "Authentication failed", details: Optional[dict] = None
    ) -> None:
        super().__init__(message, details)


class ChannelNotFoundError(TelegramDLError):
    """Raised when channel is not found."""

    def __init__(
        self,
        channel_id: int,
        message: str = "Channel not found",
        details: Optional[dict] = None,
    ) -> None:
        details = details or {}
        details["channel_id"] = channel_id
        super().__init__(message, details)


class VideoNotFoundError(TelegramDLError):
    """Raised when video is not found."""

    def __init__(
        self,
        video_id: int,
        message: str = "Video not found",
        details: Optional[dict] = None,
    ) -> None:
        details = details or {}
        details["video_id"] = video_id
        super().__init__(message, details)


class DownloadError(TelegramDLError):
    """Raised when download fails."""

    def __init__(
        self,
        video_id: int,
        message: str = "Download failed",
        details: Optional[dict] = None,
    ) -> None:
        details = details or {}
        details["video_id"] = video_id
        super().__init__(message, details)


class ConfigurationError(TelegramDLError):
    """Raised when configuration is invalid."""

    def __init__(
        self, message: str = "Invalid configuration", details: Optional[dict] = None
    ) -> None:
        super().__init__(message, details)


class ConnectionError(TelegramDLError):
    """Raised when connection to Telegram fails."""

    def __init__(
        self, message: str = "Connection failed", details: Optional[dict] = None
    ) -> None:
        super().__init__(message, details)
