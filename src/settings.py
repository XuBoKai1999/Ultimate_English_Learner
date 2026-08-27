import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LIBRARY_DIR = PROJECT_ROOT / "library"
DRAFTS_DIR = LIBRARY_DIR / "drafts"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
CATEGORIES_FILE = PROJECT_ROOT / "categories.md"
SETTINGS_FILE = PROJECT_ROOT / "settings.json"
TTS_VOICE = "en-US-JennyNeural"

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


def load_zoom(path=SETTINGS_FILE):
    try:
        value = json.loads(path.read_text(encoding="utf-8")).get("zoom", 1.0)
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) and 0.6 <= value <= 2.0 else 1.0
    except (OSError, ValueError, AttributeError):
        return 1.0


def save_zoom(value, path=SETTINGS_FILE):
    path.write_text(json.dumps({"zoom": value}, indent=2) + "\n", encoding="utf-8")
