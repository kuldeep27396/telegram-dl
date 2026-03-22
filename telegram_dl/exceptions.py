class TelegramDLError(Exception):
    """Base exception for telegram-dl errors"""

    pass


class AuthenticationError(TelegramDLError):
    """Raised when authentication fails"""

    pass


class ChannelNotFoundError(TelegramDLError):
    """Raised when channel is not found"""

    pass


class VideoNotFoundError(TelegramDLError):
    """Raised when video is not found"""

    pass
