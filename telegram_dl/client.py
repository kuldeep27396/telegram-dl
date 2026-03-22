import os
import asyncio
from pathlib import Path
from typing import Optional, List, Dict
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError


class TelegramDLError(Exception):
    pass


class TelegramDownloader:
    def __init__(
        self,
        api_id: int,
        api_hash: str,
        phone: str,
        session_name: str = "telegram_dl_session",
    ):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.session_name = session_name
        self.client: Optional[TelegramClient] = None

    async def connect(self):
        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        await self.client.start(phone=self.phone)
        return self

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()

    async def __aenter__(self):
        return await self.connect()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    def get_dialogs(self) -> List[Dict]:
        if not self.client:
            raise TelegramDLError(
                "Not connected. Use 'async with' or call connect() first."
            )

        dialogs = []
        for dialog in self.client.iter_dialogs():
            if dialog.is_channel or dialog.is_group:
                dialogs.append(
                    {
                        "id": dialog.id,
                        "title": dialog.title,
                        "type": "Channel" if dialog.is_channel else "Group",
                    }
                )
        return dialogs

    async def get_channel_videos(self, channel_id: int) -> List[Dict]:
        if not self.client:
            raise TelegramDLError("Not connected.")

        entity = await self.client.get_entity(channel_id)
        videos = []

        async for message in self.client.iter_messages(entity, reverse=True):
            if message.video:
                videos.append(
                    {
                        "id": message.id,
                        "name": message.file.name
                        if message.file and message.file.name
                        else f"video_{message.id}.mp4",
                        "date": message.date,
                        "message": message,
                    }
                )
        return videos

    async def download_video(
        self,
        channel_id: int,
        video_id: int,
        output_dir: str = ".",
        filename: Optional[str] = None,
    ) -> str:
        if not self.client:
            raise TelegramDLError("Not connected.")

        entity = await self.client.get_entity(channel_id)

        async for message in self.client.iter_messages(entity):
            if message.id == video_id and message.video:
                if filename is None:
                    filename = (
                        message.file.name
                        if message.file and message.file.name
                        else f"video_{video_id}.mp4"
                    )

                filepath = os.path.join(output_dir, filename)
                await message.download_media(filepath)
                return filepath

        raise TelegramDLError(f"Video {video_id} not found")

    async def download_all_videos(
        self,
        channel_id: int,
        output_dir: str = ".",
        progress_callback=None,
    ) -> List[str]:
        if not self.client:
            raise TelegramDLError("Not connected.")

        os.makedirs(output_dir, exist_ok=True)
        entity = await self.client.get_entity(channel_id)

        downloaded = []
        videos = await self.get_channel_videos(channel_id)

        for i, video in enumerate(videos):
            msg = video["message"]
            filename = video["name"]
            filepath = os.path.join(output_dir, filename)

            if os.path.exists(filepath):
                if progress_callback:
                    progress_callback(i + 1, len(videos), filename, "skipped")
                continue

            if progress_callback:
                progress_callback(i + 1, len(videos), filename, "downloading")

            await msg.download_media(filepath)
            downloaded.append(filepath)

            if progress_callback:
                progress_callback(i + 1, len(videos), filename, "done")

        return downloaded


def run_download(
    api_id: int,
    api_hash: str,
    phone: str,
    channel_id: int,
    output_dir: str = "./videos",
    session_name: str = "telegram_dl_session",
):
    async def _run():
        async with TelegramDownloader(api_id, api_hash, phone, session_name) as dl:

            def progress(current, total, filename, status):
                print(f"[{current}/{total}] {filename}: {status}")

            await dl.download_all_videos(
                channel_id, output_dir, progress_callback=progress
            )

    asyncio.run(_run())
