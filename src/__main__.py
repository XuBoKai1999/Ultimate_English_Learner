import argparse
import json
from pathlib import Path

from .contracts import validate_analysis, validate_card, validate_cards
from .gui import run
from .settings import CATEGORIES


def main():
    parser = argparse.ArgumentParser(description="Ultimate English Learner")
    parser.add_argument("kind", nargs="?", choices=("analysis", "cards", "card"))
    parser.add_argument("file", nargs="?", type=Path)
    args = parser.parse_args()

    if args.kind is None:
        run()
        return
    if args.file is None:
        parser.error("file is required when validating JSON")
    data = json.loads(args.file.read_text(encoding="utf-8"))
    if args.kind == "cards":
        validate_cards(data)
    else:
        (validate_analysis if args.kind == "analysis" else validate_card)(data, CATEGORIES)
    print("valid")


if __name__ == "__main__":
    main()
