import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LIBRARY_DIR = PROJECT_ROOT / "library"
DRAFTS_DIR = LIBRARY_DIR / "drafts"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
CATEGORIES_FILE = PROJECT_ROOT / "categories.md"
SETTINGS_FILE = PROJECT_ROOT / "settings.json"
TTS_VOICE = "en-US-JennyNeural"
INTERVALS = (2, 5, 10, 21, 45, 90, 180)
AUDIO_CACHE_DAYS = 30
ENGLISH_READING_WPM = 238

CATEGORIES = (
    "Physics & Mathematics",
    "Medicine & Life Science",
    "Psychology & Mind",
    "Philosophy & Ideas",
    "Religion, Myth & Esotericism",
    "History & Anthropology",
    "AI & Technology",
    "Society & World",
    "Economics & Finance",
    "Literature & Culture",
    "Uncategorized",
)


def _load(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, AttributeError):
        return {}


def load_zoom(path=SETTINGS_FILE):
    value = _load(path).get("zoom", 1.0)
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and 0.6 <= value <= 2.0 else 1.0


def save_zoom(value, path=SETTINGS_FILE):
    settings = _load(path)
    settings["zoom"] = value
    path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")


def load_reading_mode(path=SETTINGS_FILE):
    value = _load(path).get("reading_mode", "normal")
    return value if value in ("normal", "typewriter") else "normal"


def save_reading_mode(value, path=SETTINGS_FILE):
    if value not in ("normal", "typewriter"):
        raise ValueError("invalid reading mode")
    settings = _load(path)
    settings["reading_mode"] = value
    path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
