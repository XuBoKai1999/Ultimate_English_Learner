import json
import re
import unicodedata
from datetime import date, timedelta
from itertools import accumulate, product
from pathlib import Path

from .settings import INTERVALS

SCHEDULE_DAYS = (0, *accumulate(INTERVALS))
CONTRACTIONS = {
    "ain't": ("am not", "is not", "are not"),
    "can't": ("cannot",), "won't": ("will not",), "shan't": ("shall not",),
    "let's": ("let us",), "i'm": ("i am",),
}
SUBJECTS = {"i", "you", "we", "they", "he", "she", "it", "that", "there", "who", "what"}


def article_date(article_id):
    try:
        return date.fromisoformat(article_id[:10])
    except ValueError:
        match = re.match(r"(\d{4})(\d{2})(\d{2})", article_id)
        if not match:
            raise ValueError(f"article folder has no date: {article_id}")
        return date(*map(int, match.groups()))


def due_date(card):
    stage = min(card["review_stage"], len(SCHEDULE_DAYS) - 1)
    return article_date(card["article_id"]) + timedelta(days=SCHEDULE_DAYS[stage])


def load_cards(text_root):
    cards = []
    for path in Path(text_root).glob("*/*/*/*/cards/card_*.json"):
        card = json.loads(path.read_text(encoding="utf-8"))
        card["_path"] = path
        card["_due"] = due_date(card)
        cards.append(card)
    return cards


def daily_cards(text_root, today=None):
    today = today or date.today()
    cards = load_cards(text_root)
    for card in cards:
        reviewed_today = card.get("last_review") == today.isoformat()
        card["_session_stage"] = card["review_stage"] - 1 if reviewed_today else card["review_stage"]
        card["_reviewed_today"] = reviewed_today
    new = sorted(
        (card for card in cards if card["_session_stage"] == 0 and (card["_reviewed_today"] or card["_due"] <= today)),
        key=lambda card: (card["_due"], card["article_id"], card["id"]),
    )
    history = sorted(
        (card for card in cards if 0 < card["_session_stage"] < len(SCHEDULE_DAYS) and (card["_reviewed_today"] or card["_due"] <= today)),
        key=lambda card: (card["_due"], card["article_id"], card["id"]),
    )
    return new, history


def history_groups(cards):
    return [
        (stage, INTERVALS[stage - 1], SCHEDULE_DAYS[stage],
         [card for card in cards if card.get("_session_stage", card["review_stage"]) == stage])
        for stage in range(1, len(SCHEDULE_DAYS))
        if any(card["review_stage"] == stage for card in cards)
    ]


def complete_scheduled(card, today=None):
    today = today or date.today()
    if card.get("last_review") == today.isoformat():
        return
    path = card["_path"]
    card["review_stage"] = min(card["review_stage"] + 1, len(SCHEDULE_DAYS))
    card["review_count"] += 1
    card["last_review"] = today.isoformat()
    card["next_review"] = (
        due_date(card).isoformat() if card["review_stage"] < len(SCHEDULE_DAYS) else None
    )
    stored = {key: value for key, value in card.items() if not key.startswith("_")}
    path.write_text(json.dumps(stored, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _expand(token):
    if token in CONTRACTIONS:
        return CONTRACTIONS[token]
    if token.endswith("n't"):
        return (token[:-3] + " not",)
    match = re.fullmatch(r"([a-z]+)'(re|ve|ll|m|d|s)", token)
    if not match or match.group(1) not in SUBJECTS:
        return (token,)
    word, ending = match.groups()
    choices = {"re": ("are",), "ve": ("have",), "ll": ("will",), "m": ("am",),
               "d": ("would", "had"), "s": ("is", "has")}[ending]
    return tuple(f"{word} {choice}" for choice in choices)


def normalized_variants(text):
    text = unicodedata.normalize("NFKC", text).casefold().replace("’", "'")
    tokens = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text)
    return {tuple(" ".join(parts).split()) for parts in product(*(_expand(token) for token in tokens))}


def dictation_matches(answer, expected):
    return bool(normalized_variants(answer) & normalized_variants(expected))
