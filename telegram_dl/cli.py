"""CLI interface for telegram-dl package."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from .client import DownloaderBuilder, TelegramDownloader
from .exceptions import TelegramDLError
from .models import TelegramCredentials


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def main() -> int:
    """Main CLI entry point.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    parser = argparse.ArgumentParser(
        description="Download videos from Telegram channels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  telegram-dl --api-id 12345 --api-hash abc123 --phone +1234567890 --list-channels
  telegram-dl --api-id 12345 --api-hash abc123 --phone +1234567890 --channel -100123456789
  telegram-dl --api-id 12345 --api-hash abc123 --phone +1234567890 --channel -100123456789 --output ./videos
  telegram-dl --api-id 12345 --api-hash abc123 --phone +1234567890 --channel -100123456789 --with-progress
        """,
    )

    parser.add_argument("--api-id", type=int, required=True, help="Telegram API ID")
    parser.add_argument("--api-hash", type=str, required=True, help="Telegram API Hash")
    parser.add_argument(
        "--phone", type=str, required=True, help="Phone number (e.g., +1234567890)"
    )
    parser.add_argument("--channel", type=int, help="Channel ID to download from")
    parser.add_argument(
        "--output", type=str, default="./telegram_videos", help="Output directory"
    )
    parser.add_argument(
        "--session", type=str, default="telegram_dl_session", help="Session name"
    )
    parser.add_argument(
        "--list-channels", action="store_true", help="List available channels"
    )
    parser.add_argument(
        "--with-progress", action="store_true", help="Show progress bars"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )

    args = parser.parse_args()

    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    try:
        builder = (
            DownloaderBuilder()
            .with_credentials(
                api_id=args.api_id,
                api_hash=args.api_hash,
                phone=args.phone,
            )
            .with_output_dir(args.output)
        )

        if args.with_progress:
            builder = builder.with_progress_bar().with_logging()

        downloader = builder.build()

        async def run() -> int:
            async with downloader:
                if args.list_channels:
                    print("\nAvailable channels and groups:\n")
                    channels = await downloader.get_dialogs()
                    for ch in channels:
                        ch_type = "Channel" if ch.is_channel else "Group"
                        print(f"  [{ch_type}] {ch.id} | {ch.title}")
                        if ch.username:
                            print(f"           @{ch.username}")
                    print()
                    return 0

                elif args.channel:
                    print(
                        f"\nDownloading from channel {args.channel} to {args.output}/\n"
                    )
                    results = await downloader.download_all_videos(args.channel)

                    print("\n" + "=" * 50)
                    print("Download Summary:")
                    print("=" * 50)

                    successful = sum(1 for r in results if r.success)
                    failed = sum(1 for r in results if not r.success and r.error)
                    skipped = sum(1 for r in results if r.status.value == "SKIPPED")

                    print(f"Total: {len(results)}")
                    print(f"Completed: {successful}")
                    print(f"Failed: {failed}")
                    print(f"Skipped: {skipped}")
                    return 0

                else:
                    print(
                        "Error: --channel is required for downloading", file=sys.stderr
                    )
                    print(
                        "Use --list-channels to see available channels", file=sys.stderr
                    )
                    return 1

        return asyncio.run(run())

    except TelegramDLError as e:
        logger.error(f"Telegram error: {e.message}")
        if e.details:
            logger.debug(f"Details: {e.details}")
        return 1
    except KeyboardInterrupt:
        logger.info("Download interrupted by user")
        return 130
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
