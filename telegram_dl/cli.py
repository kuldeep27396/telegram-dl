import argparse
import sys
import os
from .client import TelegramDownloader, run_download


def main():
    parser = argparse.ArgumentParser(
        description="Download videos from Telegram channels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  telegram-dl --api-id 12345 --api-hash abc123 --phone +1234567890 --channel -100123456789
  telegram-dl --list-channels --api-id 12345 --api-hash abc123 --phone +1234567890
  telegram-dl --api-id 12345 --api-hash abc123 --phone +1234567890 --channel -100123456789 --output ./my_videos
        """,
    )

    parser.add_argument(
        "--api-id", type=int, required=True, help="Telegram API ID from my.telegram.org"
    )
    parser.add_argument(
        "--api-hash",
        type=str,
        required=True,
        help="Telegram API Hash from my.telegram.org",
    )
    parser.add_argument(
        "--phone",
        type=str,
        required=True,
        help="Phone number with country code (e.g., +1234567890)",
    )
    parser.add_argument(
        "--channel", type=int, help="Channel ID to download from (e.g., -100123456789)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./telegram_videos",
        help="Output directory (default: ./telegram_videos)",
    )
    parser.add_argument(
        "--session",
        type=str,
        default="telegram_dl_session",
        help="Session name (default: telegram_dl_session)",
    )
    parser.add_argument(
        "--list-channels", action="store_true", help="List all your channels and exit"
    )

    args = parser.parse_args()

    if args.list_channels:
        print("Fetching your channels...")

        async def list_channels():
            async with TelegramDownloader(
                args.api_id, args.api_hash, args.phone, args.session
            ) as dl:
                for dialog in dl.client.iter_dialogs():
                    if dialog.is_channel or dialog.is_group:
                        print(f"  {dialog.id} | {dialog.title}")

        import asyncio

        asyncio.run(list_channels())
        return

    if not args.channel:
        print("Error: --channel is required for downloading", file=sys.stderr)
        print("Use --list-channels to see available channels", file=sys.stderr)
        sys.exit(1)

    print(f"Downloading from channel {args.channel} to {args.output}/")
    run_download(
        args.api_id, args.api_hash, args.phone, args.channel, args.output, args.session
    )


if __name__ == "__main__":
    main()
