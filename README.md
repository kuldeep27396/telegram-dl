# telegram-dl

A Python CLI tool to download videos from Telegram channels.

## Installation

```bash
pip install telegram-dl
```

## Quick Start

### 1. Get Telegram API Credentials

1. Go to [my.telegram.org](https://my.telegram.org)
2. Log in with your phone number
3. Click **"API development tools"**
4. Create a new app
5. Copy your **API ID** and **API Hash**

### 2. Download Videos

```bash
# List your channels first
telegram-dl --api-id 12345 --api-hash abc123def456 --phone +1234567890 --list-channels

# Download all videos from a channel
telegram-dl --api-id 12345 --api-hash abc123def456 --phone +1234567890 --channel -1001234567890
```

### 3. Use Custom Output Directory

```bash
telegram-dl --api-id 12345 --api-hash abc123def456 --phone +1234567890 --channel -1001234567890 --output ./my_videos
```

## Programmatic Usage

```python
from telegram_dl import TelegramDownloader

async def main():
    async with TelegramDownloader(
        api_id=12345,
        api_hash="abc123def456",
        phone="+1234567890"
    ) as dl:
        # List channels
        async for dialog in dl.client.iter_dialogs():
            if dialog.is_channel:
                print(f"{dialog.id} | {dialog.title}")
        
        # Download all videos
        await dl.download_all_videos(channel_id, "./videos")

asyncio.run(main())
```

## Features

- Download all videos from Telegram channels
- Automatic session management (login once, use many times)
- Progress tracking
- Named file preservation from Telegram
- Skip already downloaded files
- CLI and programmatic API

## Requirements

- Python 3.10+
- Telegram API credentials (get from [my.telegram.org](https://my.telegram.org))

## License

MIT License
