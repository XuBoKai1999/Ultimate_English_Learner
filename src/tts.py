import asyncio
import json
from pathlib import Path

import edge_tts

from .settings import TTS_VOICE


async def _synthesize(text, audio_path, timing_path, voice=TTS_VOICE):
    if not text.strip():
        raise ValueError("TTS text is empty")
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = audio_path.with_suffix(audio_path.suffix + ".tmp")
    timings = []
    try:
        with temporary.open("wb") as audio:
            async for chunk in edge_tts.Communicate(text, voice, boundary="WordBoundary").stream():
                if chunk["type"] == "audio":
                    audio.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    timings.append({
                        "start": chunk["offset"] / 10_000_000,
                        "duration": chunk["duration"] / 10_000_000,
                        "text": chunk["text"],
                    })
        if not temporary.stat().st_size:
            raise RuntimeError("TTS returned no audio")
        temporary.replace(audio_path)
        timing_path.write_text(
            json.dumps(timings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    finally:
        temporary.unlink(missing_ok=True)


async def _build(article_dir, audio_dir, progress=None):
    article_dir = Path(article_dir)
    audio_dir = Path(audio_dir)
    jobs = [
        (article_dir / "article.md", audio_dir / "article.mp3", audio_dir / "article.timing.json", None)
    ]
    for card_file in sorted((article_dir / "cards").glob("card_*.json")):
        card = json.loads(card_file.read_text(encoding="utf-8"))
        card_audio = audio_dir / "cards" / card["id"]
        jobs.extend((
            (None, card_audio / "text.mp3", card_audio / "text.timing.json", card["text"]),
            (None, card_audio / "example.mp3", card_audio / "example.timing.json", card["example_en"]),
        ))
    total = len(jobs)
    if progress:
        progress(0, total, "Starting")
    for completed, (source, audio, timing, text) in enumerate(jobs, 1):
        if not (audio.is_file() and timing.is_file()):
            await _synthesize(
                text if text is not None else source.read_text(encoding="utf-8"), audio, timing
            )
        if progress:
            progress(completed, total, audio.stem)


def build_article_audio(article_dir, audio_dir, progress=None):
    asyncio.run(_build(article_dir, audio_dir, progress))
