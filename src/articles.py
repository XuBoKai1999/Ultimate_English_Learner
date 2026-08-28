import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from .contracts import validate_analysis, validate_card, validate_cards_match_analysis


def article_directory_name(title, now, parent):
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", title).strip(" .-")
    title = re.sub(r"\s+", " ", title)[:120].rstrip(" .-") or "Untitled"
    base = f"{now:%Y-%m-%d}-{title}"
    name, suffix = base, 2
    while (Path(parent) / name).exists():
        name, suffix = f"{base}-{suffix}", suffix + 1
    return name

def save_draft(cleaned, drafts_dir, now=None):
    if not cleaned.strip():
        raise ValueError("Cleaned article is required")
    now = now or datetime.now()
    article_id = now.strftime("%Y%m%d-%H%M%S-%f")
    directory = Path(drafts_dir) / article_id
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "article.md").write_text(cleaned.strip() + "\n", encoding="utf-8")
    return directory


def import_analysis(draft, analysis, categories, text_dir, audio_dir, now=None):
    validate_analysis(analysis, categories)
    draft = Path(draft)
    now = now or datetime.now()
    parent = Path(text_dir, analysis["category"], now.strftime("%Y"), now.strftime("%m"))
    relative = Path(
        analysis["category"], now.strftime("%Y"), now.strftime("%m"),
        article_directory_name(analysis["title"], now, parent),
    )
    target = Path(text_dir) / relative
    if target.exists():
        raise FileExistsError(target)
    (draft / "analysis.json").write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(draft), target)
    (Path(audio_dir) / relative).mkdir(parents=True, exist_ok=True)
    return target


def import_cards(article_dir, cards, now=None):
    article_dir = Path(article_dir)
    analysis = json.loads((article_dir / "analysis.json").read_text(encoding="utf-8"))
    validate_cards_match_analysis(cards, analysis)
    cards_dir = article_dir / "cards"
    if cards_dir.exists():
        raise FileExistsError(cards_dir)
    (article_dir / "cards.json").write_text(
        json.dumps(cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    cards_dir.mkdir()
    category = article_dir.parents[2].name
    review_date = (now or datetime.now()).date().isoformat()
    for index, content in enumerate(cards["cards"], 1):
        card = {
            **content,
            "id": f"card_{index:03d}",
            "article_id": article_dir.name,
            "category": category,
            "status": "learning",
            "review_stage": 0,
            "review_count": 0,
            "last_review": None,
            "next_review": review_date,
        }
        validate_card(card, [category])
        (cards_dir / f"card_{index:03d}.json").write_text(
            json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
