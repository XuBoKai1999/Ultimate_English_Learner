import json
import os
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.articles import article_directory_name, change_article_category, delete_article, import_analysis, import_cards, save_draft, save_translation
from src.contracts import validate_analysis, validate_card, validate_cards
from src.gui import align_word_spans, centered_scroll_fraction, list_directory, load_recent_articles, markdown_layout, nearest_span_index, parse_category_sources, remember_recent_article
from src.player import AudioPlayer, format_audio_time
from src.review import complete_scheduled, daily_cards, dictation_matches, due_date, history_groups
from src.settings import load_reading_mode, load_zoom, save_reading_mode, save_zoom
from src.tts import build_article_audio, cleanup_audio_cache


CATEGORIES = ["AI & Technology", "Uncategorized"]


class ContractTests(unittest.TestCase):
    def test_time_only_review_and_dictation(self):
        card = {
            "article_id": "2026-08-01-Title", "review_stage": 2,
            "review_count": 1, "last_review": None, "next_review": "2026-08-08",
        }
        self.assertEqual(due_date(card), date(2026, 8, 8))
        self.assertTrue(dictation_matches("  HE'S here! ", "He is here."))
        self.assertFalse(dictation_matches("He was here.", "He is here."))

    def test_unlimited_daily_cards_and_history_cycles(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            article = root / "Category" / "2026" / "08" / "2026-08-01-Title" / "cards"
            article.mkdir(parents=True)
            for index in range(27):
                card = {
                    "id": f"card_{index:03d}", "article_id": "2026-08-01-Title",
                    "review_stage": 0 if index < 16 else 1, "review_count": 0,
                    "last_review": None, "next_review": "2026-08-01",
                }
                (article / f'card_{index:03d}.json').write_text(json.dumps(card), encoding="utf-8")
            new, history = daily_cards(root, date(2026, 8, 28))
            self.assertEqual((len(new), len(history)), (16, 11))
            self.assertEqual(history_groups(history)[0][1:3], (2, 2))
            complete_scheduled(new[0], date(2026, 8, 28))
            card_path = new[0]["_path"]
            saved = json.loads(card_path.read_text(encoding="utf-8"))
            self.assertEqual((saved["review_stage"], saved["next_review"]), (1, "2026-08-03"))
            new_again, _ = daily_cards(root, date(2026, 8, 28))
            self.assertEqual(len(new_again), 16)
            complete_scheduled(new_again[0], date(2026, 8, 28))
            saved_again = json.loads(card_path.read_text(encoding="utf-8"))
            self.assertEqual(saved_again["review_stage"], 1)

    def test_audio_cache_removes_only_old_audio(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "old.mp3"
            timing = root / "old.timing.json"
            keep = root / "article.md"
            for path in (old, timing, keep):
                path.write_text("x", encoding="utf-8")
            timestamp = (datetime(2026, 8, 28) - timedelta(days=31)).timestamp()
            os.utime(old, (timestamp, timestamp))
            self.assertEqual(cleanup_audio_cache(root, 30, datetime(2026, 8, 28)), 1)
            self.assertFalse(old.exists())
            self.assertFalse(timing.exists())
            self.assertTrue(keep.exists())

    def test_article_directory_name_is_readable_and_safe(self):
        with TemporaryDirectory() as directory:
            now = datetime(2026, 8, 28)
            self.assertEqual(
                article_directory_name('A: Useful / Title?', now, directory),
                "2026-08-28-A- Useful - Title",
            )
            Path(directory, "2026-08-28-Title").mkdir()
            self.assertEqual(article_directory_name("Title", now, directory), "2026-08-28-Title-2")

    def test_category_source_table_is_read_from_markdown(self):
        rows = parse_category_sources(
            "## Default Categories\n\n| Category | 範圍 | 建議來源 |\n"
            "| --- | --- | --- |\n| **Physics** | 物理 | Quanta |\n\n## General Sources\n"
        )
        self.assertEqual(rows, [("Physics", "物理", "Quanta")])

    def test_timing_words_align_with_repeated_article_text(self):
        timings = [{"text": word} for word in ("Hello", "world", "hello")]
        spans = align_word_spans("Hello, world. Hello again.", timings)
        self.assertEqual(spans, [(0, 5), (7, 12), (14, 19)])
        self.assertEqual(nearest_span_index(10, spans), 1)
        self.assertAlmostEqual(centered_scroll_fraction(50, 100, 0.2), 0.4)

    def test_seek_syncs_highlight_immediately(self):
        seen = []
        player = type("FakePlayer", (), {})()
        player.timings = [{"start": 0.1}, {"start": 1.0}]
        player._word_index = -1
        player.on_word = lambda index, item: seen.append(index)
        AudioPlayer._sync_word(player, 1.2)
        self.assertEqual(seen, [1])
        self.assertEqual(format_audio_time(135.9), "02:15")

    def test_markdown_layout_preserves_audio_offsets(self):
        source = "# Title\n\n- **Bold** item\n"
        rendered, tags = markdown_layout(source)
        self.assertEqual(len(rendered), len(source))
        self.assertEqual(rendered[source.index("-")], "•")
        self.assertIn(("heading1", 2, 7), tags)
        self.assertIn(("bold", source.index("Bold"), source.index("Bold") + 4), tags)

    def test_valid_contracts(self):
        item = {"text": "reason about", "type": "phrase", "level": "general"}
        validate_analysis(
            {"title": "Test", "category": "AI & Technology", "items": [item]},
            CATEGORIES,
        )
        content = {
            **item,
            "meaning_zh": "推理、思考",
            "example_en": "We need to reason about the result.",
            "example_zh": "我們需要思考這個結果。",
        }
        validate_cards({"cards": [content]})
        validate_card(
            {
                **content,
                "id": "card_001",
                "article_id": "test",
                "category": "AI & Technology",
                "status": "learning",
                "review_stage": 0,
                "review_count": 0,
                "last_review": None,
                "next_review": "2026-08-27",
            },
            CATEGORIES,
        )

    def test_rejects_invalid_ai_output(self):
        with self.assertRaises(ValueError):
            validate_analysis(
                {"title": "Test", "category": "Invented", "items": []},
                CATEGORIES,
            )
        with self.assertRaises(ValueError):
            validate_cards({"cards": [{"text": "incomplete"}]})

    def test_zoom_setting_round_trip_and_fallback(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            self.assertEqual(load_zoom(path), 1.0)
            save_zoom(1.4, path)
            self.assertEqual(load_zoom(path), 1.4)
            save_reading_mode("typewriter", path)
            self.assertEqual((load_zoom(path), load_reading_mode(path)), (1.4, "typewriter"))
            save_zoom(1.2, path)
            self.assertEqual(load_reading_mode(path), "typewriter")
            path.write_text('{"zoom": 99}', encoding="utf-8")
            self.assertEqual(load_zoom(path), 1.0)

    def test_directory_listing_is_live_and_sorted(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "B.txt").touch()
            (root / "A folder").mkdir()
            (root / ".gitkeep").touch()
            self.assertEqual(
                [item.name for item in list_directory(root)],
                ["A folder", "B.txt"],
            )

    def test_recent_articles_are_deduplicated_and_limited(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "text"
            recent = Path(directory) / "recent.json"
            articles = []
            for index in range(11):
                article = root / "Category" / "2026" / "08" / f"article-{index}"
                article.mkdir(parents=True)
                (article / "article.md").write_text("x", encoding="utf-8")
                articles.append(article)
                remember_recent_article(article, root, recent)
            remember_recent_article(articles[5], root, recent)
            loaded = load_recent_articles(root, recent)
            self.assertEqual((len(loaded), loaded[0]), (10, articles[5].resolve()))

    def test_article_category_move_and_delete_include_audio(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            text, audio = root / "text", root / "audio"
            article = text / "Old" / "2026" / "08" / "2026-08-28-Title"
            (article / "cards").mkdir(parents=True)
            (article / "article.md").write_text("x", encoding="utf-8")
            (article / "analysis.json").write_text(json.dumps({"category": "Old"}), encoding="utf-8")
            (article / "cards" / "card_001.json").write_text(json.dumps({"category": "Old"}), encoding="utf-8")
            mirrored = audio / article.relative_to(text)
            mirrored.mkdir(parents=True)
            (mirrored / "article.mp3").touch()
            moved = change_article_category(article, "New", text, audio)
            self.assertEqual(json.loads((moved / "cards" / "card_001.json").read_text())["category"], "New")
            self.assertTrue((audio / moved.relative_to(text) / "article.mp3").is_file())
            delete_article(moved, text, audio)
            self.assertFalse(moved.exists())
            self.assertFalse((audio / moved.relative_to(text)).exists())

    def test_ai_cleaned_article_save(self):
        cleaned = "# Title\n\nHello world."
        with TemporaryDirectory() as directory:
            root = Path(directory)
            draft = save_draft(cleaned, root / "drafts", datetime(2026, 8, 27, 12))
            self.assertEqual((draft / "article.md").read_text(encoding="utf-8"), cleaned + "\n")
            save_translation(draft, "# 標題\n\n內文。")
            self.assertTrue((draft / "translation_zh.md").is_file())
            analysis = {
                "title": "Title",
                "category": "AI & Technology",
                "items": [{"text": "reason about", "type": "phrase", "level": "general"}],
            }
            article = import_analysis(
                draft, analysis, CATEGORIES, root / "text", root / "audio",
                datetime(2026, 8, 28),
            )
            self.assertEqual(
                article.relative_to(root / "text").parts[:3],
                ("AI & Technology", "2026", "08"),
            )
            self.assertEqual(article.name, "2026-08-28-Title")
            self.assertTrue((root / "audio" / article.relative_to(root / "text")).is_dir())
            cards = {"cards": [{
                "text": "reason about",
                "type": "phrase",
                "level": "general",
                "meaning_zh": "思考",
                "example_en": "Reason about the result.",
                "example_zh": "思考這項結果。",
            }]}
            import_cards(article, cards, datetime(2026, 8, 28))
            self.assertTrue((article / "cards.json").is_file())
            card = json.loads(
                (article / "cards" / "card_001.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                (card["id"], card["article_id"], card["category"], card["next_review"]),
                ("card_001", article.name, "AI & Technology", "2026-08-28"),
            )
            with self.assertRaises(ValueError):
                import_cards(article, {"cards": []})
            with self.assertRaises(ValueError):
                save_draft("", root / "drafts")

    def test_tts_builds_mirrored_audio_and_timings(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            article = root / "text" / "Category" / "2026" / "08" / "article"
            (article / "cards").mkdir(parents=True)
            (article / "article.md").write_text("Hello article", encoding="utf-8")
            (article / "cards" / "card_001.json").write_text(json.dumps({
                "id": "card_001", "text": "hello", "example_en": "Hello there."
            }), encoding="utf-8")

            class FakeCommunicate:
                def __init__(self, text, voice, **kwargs):
                    self.text = text

                async def stream(self):
                    yield {"type": "audio", "data": self.text.encode()}
                    yield {"type": "WordBoundary", "offset": 0, "duration": 5_000_000, "text": self.text}

            audio = root / "audio" / "Category" / "2026" / "08" / "article"
            with patch("src.tts.edge_tts.Communicate", FakeCommunicate):
                progress = []
                build_article_audio(article, audio, lambda done, total, name: progress.append((done, total, name)))
            self.assertTrue((audio / "article.mp3").is_file())
            self.assertTrue((audio / "cards" / "card_001" / "text.mp3").is_file())
            timing = json.loads((audio / "article.timing.json").read_text(encoding="utf-8"))
            self.assertEqual(timing[0], {"start": 0.0, "duration": 0.5, "text": "Hello article"})
            self.assertEqual(progress[-1][:2], (3, 3))


if __name__ == "__main__":
    unittest.main()
