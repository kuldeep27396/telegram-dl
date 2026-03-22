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

## High Level Design (HLD)

### Architecture

```mermaid
flowchart TB
    subgraph User["👤 User Layer"]
        CLI["🖥️ CLI Interface<br/>(telegram-dl)"]
        API["📦 Python API<br/>(TelegramDownloader)"]
    end
    
    subgraph Core["⚙️ Core Layer"]
        TD["🔷 TelegramDownloader<br/>• connect() / disconnect()<br/>• get_channel_videos()<br/>• download_video()<br/>• download_all_videos()"]
    end
    
    subgraph Protocol["🔌 Protocol Layer"]
        TL["🔶 Telethon Library<br/>• MTProto<br/>• Session Management<br/>• OTP/2FA Auth"]
    end
    
    subgraph External["🌐 External Services"]
        TS["📡 Telegram Servers<br/>api.telegram.org"]
    end
    
    User --> Core
    Core --> Protocol
    Protocol --> External
    
    style User fill:#e1f5fe
    style Core fill:#fff3e0
    style Protocol fill:#f3e5f5
    style External fill:#e8f5e9
```

### Data Flow

```mermaid
sequenceDiagram
    participant U as 👤 User
    participant C as 🖥️ CLI/API
    participant TD as 🔷 TelegramDownloader
    participant TL as 🔶 Telethon
    participant TS as 📡 Telegram

    U->>C: Provide credentials
    C->>TD: Initialize
    TD->>TL: connect()
    TL->>TS: Establish connection
    TS-->>TL: OTP verification
    TL-->>TD: Authenticated
    TD-->>C: Ready
    
    U->>C: download_all_videos(channel)
    C->>TD: Fetch channel
    TD->>TL: iter_messages()
    TL->>TS: Get messages
    TS-->>TL: Return messages
    TL-->>TD: Video messages
    TD->>TL: download_media()
    loop For each video
        TL->>TS: Request file
        TS-->>TL: Stream file
        TL-->>TD: Save to disk
    end
    TD-->>C: Done!
```

### Class Diagram

```mermaid
classDiagram
    class TelegramDownloader {
        +int api_id
        +str api_hash
        +str phone
        +TelegramClient client
        
        +connect() TelegramClient
        +disconnect()
        +get_dialogs() List[Dict]
        +get_channel_videos(channel_id) List[Dict]
        +download_video(channel_id, video_id, output_dir, filename) str
        +download_all_videos(channel_id, output_dir, progress_callback) List[str]
    }
    
    class TelegramDLError {
        +Exception base
    }
    
    class AuthenticationError {
        +TelegramDLError base
    }
    
    class ChannelNotFoundError {
        +TelegramDLError base
    }
    
    class VideoNotFoundError {
        +TelegramDLError base
    }
    
    TelegramDownloader o-- TelegramDLError : raises
    TelegramDLError <|-- AuthenticationError
    TelegramDLError <|-- ChannelNotFoundError
    TelegramDLError <|-- VideoNotFoundError
    
    TelegramDownloader --> "uses" TelethonClient : TelegramClient
```

### Session Management Flow

```mermaid
flowchart LR
    A([🚀 First Run]) --> B{Has Session?}
    B -->|No| C["📱 OTP Verification"]
    C --> D["💾 Save Session"]
    D --> E[✅ Ready]
    
    B -->|Yes| F{Session Valid?}
    F -->|Yes| E
    F -->|No| C
    
    G([♻️ Next Run]) --> H{Session Exists?}
    H -->|Yes| E
    H -->|No| C
```

### Error Handling

```mermaid
flowchart TB
    E[❌ Error Occurs] --> A
    
    subgraph TelethonErrors
        A1["🔴 ConnectionError"]
        A2["🔴 SessionPasswordNeededError"]
        A3["🔴 ChannelInvalidError"]
    end
    
    subgraph CustomErrors
        B1["🟠 TelegramDLError (base)"]
        B2["🟠 AuthenticationError"]
        B3["🟠 ChannelNotFoundError"]
        B4["🟠 VideoNotFoundError"]
    end
    
    subgraph Handling
        C1["📋 User retries with valid creds"]
        C2["📋 Check channel ID"]
        C3["📋 Verify video exists"]
    end
    
    A1 --> B1
    A2 --> B2
    A3 --> B3
    
    B1 <|-- B2
    B1 <|-- B3
    B1 <|-- B4
    
    B2 --> C1
    B3 --> C2
    B4 --> C3
    
    style TelethonErrors fill:#ffebee
    style CustomErrors fill:#fff8e1
    style Handling fill:#e8f5e9
```

### Components

| Component | Responsibility |
|-----------|---------------|
| `cli.py` | Command-line interface, argument parsing |
| `client.py` | Core download logic, Telegram client management |
| `exceptions.py` | Custom exception classes |

### Key Features

```mermaid
mindmap
  root((🔧 Features))
    CLI Interface
      Simple commands
      Progress tracking
      Channel listing
    Core Logic
      Async download
      Auto retry
      Skip existing
    Session Management
      Persistent login
      OTP support
      2FA support
    File Handling
      Named preservation
      Custom output dir
      Progress callbacks
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
