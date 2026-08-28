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


def save_translation(draft, translation):
    if not translation.strip():
        raise ValueError("Traditional Chinese translation is required")
    (Path(draft) / "translation_zh.md").write_text(
        translation.strip() + "\n", encoding="utf-8"
    )


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


def change_article_category(article_dir, category, text_dir, audio_dir):
    article_dir, text_dir, audio_dir = map(Path, (article_dir, text_dir, audio_dir))
    if not category or Path(category).name != category or category in (".", ".."):
        raise ValueError("Invalid category")
    relative = article_dir.resolve().relative_to(text_dir.resolve())
    target_relative = Path(category, *relative.parts[1:])
    target = text_dir / target_relative
    audio_source = audio_dir / relative
    audio_target = audio_dir / target_relative
    if target.exists() or audio_target.exists():
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    audio_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(article_dir), target)
    try:
        if audio_source.exists():
            shutil.move(str(audio_source), audio_target)
    except Exception:
        shutil.move(str(target), article_dir)
        raise
    analysis_path = target / "analysis.json"
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    analysis["category"] = category
    analysis_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for card_path in (target / "cards").glob("card_*.json"):
        card = json.loads(card_path.read_text(encoding="utf-8"))
        card["category"] = category
        card_path.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def delete_article(article_dir, text_dir, audio_dir):
    article_dir, text_dir, audio_dir = map(Path, (article_dir, text_dir, audio_dir))
    relative = article_dir.resolve().relative_to(text_dir.resolve())
    if not relative.parts or not (article_dir / "article.md").is_file():
        raise ValueError("Not an article directory")
    audio = audio_dir / relative
    if audio.exists():
        shutil.rmtree(audio)
    shutil.rmtree(article_dir)
