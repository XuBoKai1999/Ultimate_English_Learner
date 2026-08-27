"""Validation for AI imports and stored cards."""

from datetime import date

TYPES = {"word", "phrase", "chunk"}
LEVELS = {"general", "domain", "specialized"}
STATUSES = {"learning", "known"}


def _object(value, name):
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _fields(value, required, name):
    missing = required - value.keys()
    extra = value.keys() - required
    if missing or extra:
        raise ValueError(f"{name} fields: missing={sorted(missing)}, extra={sorted(extra)}")


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")


def _choice(value, choices, field):
    if value not in choices:
        raise ValueError(f"{field} must be one of {sorted(choices)}")


def _item(item, fields, name):
    item = _object(item, name)
    _fields(item, fields, name)
    for field in fields:
        _text(item[field], f"{name}.{field}")
    _choice(item["type"], TYPES, f"{name}.type")
    _choice(item["level"], LEVELS, f"{name}.level")


def validate_analysis(data, categories):
    data = _object(data, "analysis")
    _fields(data, {"title", "category", "items"}, "analysis")
    _text(data["title"], "analysis.title")
    _choice(data["category"], set(categories), "analysis.category")
    if not isinstance(data["items"], list):
        raise ValueError("analysis.items must be an array")
    seen = set()
    for index, item in enumerate(data["items"]):
        _item(item, {"text", "type", "level"}, f"analysis.items[{index}]")
        if item["text"] in seen:
            raise ValueError(f"duplicate analysis item: {item['text']}")
        seen.add(item["text"])


CARD_CONTENT_FIELDS = {
    "text", "type", "level", "meaning_zh", "example_en", "example_zh"
}


def validate_cards(data):
    data = _object(data, "cards batch")
    _fields(data, {"cards"}, "cards batch")
    if not isinstance(data["cards"], list):
        raise ValueError("cards must be an array")
    for index, card in enumerate(data["cards"]):
        _item(card, CARD_CONTENT_FIELDS, f"cards[{index}]")


def validate_cards_match_analysis(cards, analysis):
    validate_cards(cards)
    expected = [(item["text"], item["type"], item["level"]) for item in analysis["items"]]
    actual = [(card["text"], card["type"], card["level"]) for card in cards["cards"]]
    if actual != expected:
        raise ValueError("cards must match analysis items exactly and in order")


def validate_card(card, categories):
    card = _object(card, "card")
    fields = CARD_CONTENT_FIELDS | {
        "id", "article_id", "category", "status", "review_stage",
        "review_count", "last_review", "next_review",
    }
    _fields(card, fields, "card")
    _item({key: card[key] for key in CARD_CONTENT_FIELDS}, CARD_CONTENT_FIELDS, "card")
    for field in ("id", "article_id"):
        _text(card[field], f"card.{field}")
    _choice(card["category"], set(categories), "card.category")
    _choice(card["status"], STATUSES, "card.status")
    for field in ("review_stage", "review_count"):
        if not isinstance(card[field], int) or isinstance(card[field], bool) or card[field] < 0:
            raise ValueError(f"card.{field} must be a non-negative integer")
    for field in ("last_review", "next_review"):
        if card[field] is not None:
            try:
                date.fromisoformat(card[field])
            except (TypeError, ValueError) as error:
                raise ValueError(f"card.{field} must be null or an ISO date") from error
