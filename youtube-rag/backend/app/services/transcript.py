"""YouTube transcript fetching service (youtube-transcript-api >= 1.0)."""

from youtube_transcript_api import YouTubeTranscriptApi
import logging

logger = logging.getLogger(__name__)

import httpx

# Reusable client instance
_ytt = YouTubeTranscriptApi()


class TranscriptService:
    """Fetches and returns YouTube video transcripts and metadata."""

    @staticmethod
    async def fetch_metadata(video_id: str) -> dict:
        """Fetch video metadata (title, etc.) via oEmbed."""
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.json()
        except Exception as exc:
            logger.warning("Failed to fetch metadata for %s: %s", video_id, exc)
        return {"title": f"Video {video_id}"}

    @staticmethod
    async def fetch(video_id: str) -> dict:
        """
        Download the transcript and metadata for a YouTube video.

        Returns:
            Dict containing 'transcript' and 'title'.
        """
        try:
            # Metadata first (async)
            meta = await TranscriptService.fetch_metadata(video_id)
            title = meta.get("title", f"Video {video_id}")

            # Transcript
            fetched = _ytt.fetch(video_id, languages=("en", "hi"))
            transcript = " ".join(snippet.text for snippet in fetched.snippets)

            logger.info(
                "Fetched transcript & title for %s (%d chars)",
                video_id,
                len(transcript),
            )
            return {"transcript": transcript, "title": title}

        except Exception as exc:
            logger.error("Error fetching data for %s: %s", video_id, exc)
            raise ValueError(
                f"Failed to fetch data for video '{video_id}': {exc}"
            ) from exc
