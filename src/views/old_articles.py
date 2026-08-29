import json
import math
import re
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from ..articles import change_article_category, delete_article
from ..player import AudioPlayer
from ..settings import CATEGORIES, ENGLISH_READING_WPM, LIBRARY_DIR, load_reading_mode, save_reading_mode
from ..translation import lookup_inline

RECENT_ARTICLES_FILE = LIBRARY_DIR / "recent_articles.json"


def list_directory(path):
    return sorted(
        (item for item in Path(path).iterdir() if not item.name.startswith(".")),
        key=lambda item: (not item.is_dir(), item.name.casefold()),
    )


def list_articles_by_date(text_root):
    articles = []
    for article_file in Path(text_root).glob("*/*/*/*/article.md"):
        article = article_file.parent
        _, year, month, _ = article.relative_to(text_root).parts
        if not (year.isdigit() and month.isdigit()):
            continue
        articles.append((year, month, article))
    return sorted(
        articles,
        key=lambda item: (item[0], item[1], item[2].name.casefold()),
        reverse=True,
    )


def remember_recent_article(article_dir, text_root=LIBRARY_DIR / "text", path=RECENT_ARTICLES_FILE):
    relative = Path(article_dir).relative_to(text_root).as_posix()
    try:
        items = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        items = []
    items = [relative, *(item for item in items if item != relative)][:10]
    Path(path).write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_recent_articles(text_root=LIBRARY_DIR / "text", path=RECENT_ARTICLES_FILE):
    try:
        items = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    root = Path(text_root).resolve()
    articles = []
    for item in items[:10]:
        candidate = (root / item).resolve()
        if candidate.is_relative_to(root) and (candidate / "article.md").is_file():
            articles.append(candidate)
    return articles


def align_word_spans(text, timings):
    spans, cursor, folded = [], 0, text.casefold()
    for item in timings:
        word = item["text"]
        start = folded.find(word.casefold(), cursor)
        if start < 0:
            spans.append(None)
            continue
        cursor = start + len(word)
        spans.append((start, cursor))
    return spans


def nearest_span_index(offset, spans):
    choices = []
    for index, span in enumerate(spans):
        if span:
            start, end = span
            choices.append((0 if start <= offset <= end else min(abs(offset - start), abs(offset - end)), index))
    return min(choices)[1] if choices else None


def centered_scroll_fraction(line, total, visible):
    return max(0.0, min(1.0 - visible, line / max(total, 1) - visible / 2))


def estimate_english_reading(text, words_per_minute=ENGLISH_READING_WPM):
    words = len(re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)*", text))
    return words, max(1, (words + words_per_minute - 1) // words_per_minute) if words else 0


def markdown_layout(markdown):
    display = list(markdown)
    tags = []
    offset = 0
    in_code = False
    for line in markdown.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        if content.startswith("```"):
            tags.append(("syntax", offset, offset + len(content)))
            in_code = not in_code
        elif in_code:
            tags.append(("code_block", offset, offset + len(content)))
        else:
            heading = re.match(r"^(#{1,6})\s+", content)
            if heading:
                level = min(len(heading.group(1)), 3)
                tags.extend((("syntax", offset, offset + heading.end()),
                             (f"heading{level}", offset + heading.end(), offset + len(content))))
            bullet = re.match(r"^(\s*)[-+*]\s+", content)
            if bullet:
                marker = offset + len(bullet.group(1))
                display[marker] = "•"
                tags.append(("list", offset, offset + len(content)))
            elif re.match(r"^\s*\d+[.)]\s+", content):
                tags.append(("list", offset, offset + len(content)))
            quote = re.match(r"^\s*>\s?", content)
            if quote:
                tags.extend((("syntax", offset, offset + quote.end()),
                             ("quote", offset + quote.end(), offset + len(content))))
        offset += len(line)
    for pattern, tag, markers in (
        (r"\*\*(.+?)\*\*", "bold", 2),
        (r"(?<!\*)\*([^*\n]+?)\*(?!\*)", "italic", 1),
        (r"`([^`\n]+?)`", "code", 1),
    ):
        for match in re.finditer(pattern, markdown):
            tags.extend((("syntax", match.start(), match.start() + markers),
                         (tag, match.start() + markers, match.end() - markers),
                         ("syntax", match.end() - markers, match.end())))
    return "".join(display), tags


def article(self, parent, article_dir):
    try:
        remember_recent_article(article_dir)
    except (OSError, ValueError):
        pass
    page = ttk.Frame(parent, padding=(6, 2))
    status = ttk.Label(page, text="Ready.")
    status.pack(side="bottom", fill="x", pady=(2, 0))

    article = (article_dir / "article.md").read_text(encoding="utf-8")
    _, reading_minutes = estimate_english_reading(article)
    audio_dir = LIBRARY_DIR / "audio" / article_dir.relative_to(LIBRARY_DIR / "text")

    panes = ttk.Notebook(page)
    panes.pack(fill="both", expand=True)
    article_panel = ttk.Frame(panes, padding=3)
    article_panel.columnconfigure(0, weight=4, uniform="article-layout")
    article_panel.columnconfigure(1, weight=1, uniform="article-layout")
    article_panel.rowconfigure(1, weight=1)
    panes.add(
        article_panel,
        text=f"Article · ~{reading_minutes} min" if reading_minutes else "Article",
    )

    player = AudioPlayer(article_panel, show_time=True)
    player.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 3))

    def load_audio(audio, timing, label, text, on_word=None):
        self._play_or_build(player, text, audio, timing, label, status, on_word)

    def render_markdown(widget, source):
        rendered, tags = markdown_layout(source)
        widget.insert("1.0", rendered)
        widget.tag_configure("syntax", elide=True)
        widget.tag_configure("bold", font=self.reader_bold_font)
        widget.tag_configure("italic", font=self.reader_italic_font)
        widget.tag_configure("code", font=self.reader_code_font, background="#eeeeee")
        widget.tag_configure("code_block", font=self.reader_code_font, background="#eeeeee", lmargin1=16, lmargin2=16)
        widget.tag_configure("quote", foreground="#555555", lmargin1=20, lmargin2=20)
        widget.tag_configure("list", lmargin1=12, lmargin2=30)
        for level, font in self.reader_heading_fonts.items():
            widget.tag_configure(f"heading{level}", font=font, spacing1=10, spacing3=6)
        for tag, start, end in tags:
            widget.tag_add(tag, f"1.0+{start}c", f"1.0+{end}c")
        widget.config(state="disabled")

    translation_path = article_dir / "translation_zh.md"
    translation = translation_path.read_text(encoding="utf-8") if translation_path.is_file() else None
    reading_frame = ttk.Frame(article_panel)
    reading_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
    reading_frame.columnconfigure(0, weight=1, uniform="bilingual")
    reading_frame.rowconfigure(0, weight=1)
    english_frame = ttk.LabelFrame(reading_frame, text="English", padding=4)
    english_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 3) if translation else 0)
    english_frame.columnconfigure(0, weight=1)
    english_frame.rowconfigure(0, weight=1)
    article_text = tk.Text(
        english_frame, wrap="word", width=1, height=1, font=self.reader_content_font
    )
    render_markdown(article_text, article)
    article_text.tag_configure("spoken", background="#ffe66d", foreground="#111111")
    article_text.grid(row=0, column=0, sticky="nsew")
    article_scroll = ttk.Scrollbar(english_frame, orient="vertical", command=article_text.yview)
    article_scroll.grid(row=0, column=1, sticky="ns")

    translation_popup = {
        "window": None, "english": None, "chinese": None, "request": 0,
        "outside_binding": None,
    }
    translate_button = {"window": None}

    def close_translation_popup(event=None):
        binding = translation_popup["outside_binding"]
        if binding is not None:
            self.unbind("<Button-1>", binding)
        window = translation_popup["window"]
        if window is not None and window.winfo_exists():
            window.destroy()
        translation_popup.update(
            window=None, english=None, chinese=None, outside_binding=None
        )

    def close_translate_button(event=None):
        window = translate_button["window"]
        if window is not None and window.winfo_exists():
            window.destroy()
        translate_button["window"] = None

    page.bind(
        "<Destroy>",
        lambda event: (close_translation_popup(), close_translate_button())
        if event.widget is page else None,
    )

    def show_inline_translation(selected=None):
        if selected is None:
            try:
                selected = article_text.get("sel.first", "sel.last").strip()
            except tk.TclError:
                return
        if not selected:
            return
        close_translate_button()

        window = translation_popup["window"]
        if window is None or not window.winfo_exists():
            window = tk.Toplevel(self)
            window.title("Translation")
            window.transient(self)
            window.protocol("WM_DELETE_WINDOW", close_translation_popup)
            window.bind("<Escape>", close_translation_popup)
            body = ttk.Frame(window, padding=10)
            body.pack(fill="both", expand=True)
            ttk.Label(body, text="English").pack(anchor="w")
            english = tk.Text(
                body, wrap="word", width=44, height=1, font=self.reader_content_font
            )
            english.pack(fill="x", pady=(3, 8))
            english.bind(
                "<Return>",
                lambda event: show_inline_translation(
                    english.get("1.0", "end-1c").strip()
                ) or "break",
            )
            ttk.Label(body, text="Translation / Dictionary").pack(anchor="w")
            result_frame = ttk.Frame(body)
            result_frame.pack(fill="both", expand=True, pady=(3, 0))
            chinese = tk.Text(
                result_frame, wrap="word", width=44, height=10,
                font=self.reader_content_font,
            )
            chinese.pack(side="left", fill="both", expand=True)
            result_scroll = ttk.Scrollbar(result_frame, command=chinese.yview)
            result_scroll.pack(side="right", fill="y")
            chinese.config(yscrollcommand=result_scroll.set)
            chinese.tag_configure("heading", font=self.reader_bold_font, spacing1=8, spacing3=3)
            chinese.tag_configure("part", font=self.reader_bold_font, spacing1=8, spacing3=2)
            chinese.tag_configure("definition", lmargin1=12, lmargin2=34, spacing1=3)
            chinese.tag_configure(
                "example", font=self.reader_italic_font, foreground="#555555",
                lmargin1=34, lmargin2=34, spacing1=2,
            )
            chinese.tag_configure("synonyms", lmargin1=34, lmargin2=34, spacing1=3)
            translation_popup.update(window=window, english=english, chinese=chinese)
            translation_popup["outside_binding"] = self.bind(
                "<Button-1>", close_translation_popup, add="+"
            )
        else:
            window.deiconify()
            window.lift()

        def set_text(widget, text, disabled=True):
            widget.config(state="normal")
            widget.delete("1.0", "end")
            widget.insert("1.0", text)
            if disabled:
                widget.config(state="disabled")

        set_text(translation_popup["english"], selected, disabled=False)
        translation_popup["english"].mark_set("insert", "end-1c")
        translation_popup["english"].config(
            height=min(6, max(1, sum(
                max(1, math.ceil(len(line) / 44)) for line in selected.splitlines()
            )))
        )
        set_text(translation_popup["chinese"], "Looking up...")
        translation_popup["request"] += 1
        request = translation_popup["request"]

        def render_result(widget, result):
            widget.config(state="normal")
            widget.delete("1.0", "end")
            if result["suggestion"]:
                widget.insert("end", f'Did you mean: {result["suggestion"]}?\n', "heading")
            if result["translation"]:
                widget.insert("end", "繁體中文\n", "heading")
                widget.insert("end", f'{result["translation"]}\n')
            dictionary = result["dictionary"]
            if dictionary:
                heading = dictionary["word"]
                if dictionary["phonetic"]:
                    heading += f'  /{dictionary["phonetic"]}/'
                widget.insert("end", f'\n{heading}\n', "heading")
                for meaning in dictionary["meanings"]:
                    widget.insert("end", f'{meaning["part_of_speech"]}\n', "part")
                    for definition in meaning["definitions"]:
                        widget.insert("end", f'•  {definition["definition"]}\n', "definition")
                        if definition["example"]:
                            widget.insert(
                                "end", f'Example: {definition["example"]}\n', "example"
                            )
                    if meaning["synonyms"]:
                        widget.insert(
                            "end", f'Synonyms: {", ".join(meaning["synonyms"])}\n',
                            "synonyms",
                        )
            elif result["dictionary_status"] == "not_found":
                widget.insert("end", "\nNo dictionary entry found.\n", "example")
            elif result["dictionary_status"] == "timeout":
                widget.insert("end", "\nDictionary lookup timed out.\n", "example")
            elif result["dictionary_status"] == "unavailable":
                widget.insert("end", "\nDictionary service unavailable.\n", "example")
            elif result["word"]:
                widget.insert("end", "\nDictionary lookup continuing...\n", "example")
            if not widget.get("1.0", "end-1c").strip():
                widget.insert("end", "No lookup result available.")
            widget.config(state="disabled")

        def finish(result):
            window = translation_popup["window"]
            if request == translation_popup["request"] and window is not None and window.winfo_exists():
                render_result(translation_popup["chinese"], result)

        def worker():
            def publish(result):
                try:
                    self.after(0, finish, result)
                except (tk.TclError, RuntimeError):
                    pass

            lookup_inline(selected, publish)

        threading.Thread(target=worker, daemon=True).start()

    def show_translate_button(event):
        try:
            selected = article_text.get("sel.first", "sel.last").strip()
        except tk.TclError:
            close_translate_button()
            return
        if not selected:
            close_translate_button()
            return
        window = translate_button["window"]
        if window is None or not window.winfo_exists():
            window = tk.Toplevel(self)
            window.overrideredirect(True)
            window.transient(self)
            window.bind("<Escape>", close_translate_button)
            button = tk.Button(
                window, text="Translate", font="TkDefaultFont", width=10, height=1,
            )
            button.pack()
            translate_button.update(window=window, button=button)
        translate_button["button"].config(
            command=lambda text=selected: show_inline_translation(text)
        )
        window.geometry(f"+{event.x_root + 12}+{event.y_root + 10}")
        window.deiconify()
        window.lift()

    article_text.bind("<ButtonRelease-1>", show_translate_button, add="+")

    if translation:
        translation_visible = {"value": False}
        reading_frame.columnconfigure(1, weight=1, uniform="bilingual")
        chinese_frame = ttk.LabelFrame(reading_frame, text="繁體中文", padding=4)
        chinese_frame.grid(row=0, column=1, sticky="nsew", padx=(3, 0))
        chinese_frame.columnconfigure(0, weight=1)
        chinese_frame.rowconfigure(0, weight=1)
        translation_text = tk.Text(
            chinese_frame, wrap="word", width=1, height=1, font=self.reader_content_font
        )
        render_markdown(translation_text, translation)
        translation_text.grid(row=0, column=0, sticky="nsew")
        translation_scroll = ttk.Scrollbar(chinese_frame, orient="vertical", command=translation_text.yview)
        translation_scroll.grid(row=0, column=1, sticky="ns")
        syncing_scroll = {"active": False}

        def sync_scrollbar(scrollbar, other, first, last):
            scrollbar.set(first, last)
            if not translation_visible["value"] or syncing_scroll["active"]:
                return
            syncing_scroll["active"] = True
            other.yview_moveto(first)
            article_text.after_idle(
                lambda: syncing_scroll.update(active=False)
            )

        article_text.configure(
            yscrollcommand=lambda first, last: sync_scrollbar(
                article_scroll, translation_text, first, last
            )
        )
        translation_text.configure(
            yscrollcommand=lambda first, last: sync_scrollbar(
                translation_scroll, article_text, first, last
            )
        )
        chinese_frame.grid_remove()
        reading_frame.columnconfigure(1, weight=0)
    else:
        article_text.configure(yscrollcommand=article_scroll.set)

    article_actions = ttk.LabelFrame(article_panel, text="Functions", padding=8)
    article_actions.grid(row=1, column=1, sticky="nsew")

    article_spans = []
    article_timings = []
    reading_mode = tk.StringVar(value=load_reading_mode())
    scroll_state = {"line": None, "target": None, "job": None}

    def animate_scroll():
        target = scroll_state["target"]
        if target is None:
            scroll_state["job"] = None
            return
        current = article_text.yview()[0]
        if abs(target - current) < 0.001:
            article_text.yview_moveto(target)
            scroll_state["job"] = None
            return
        article_text.yview_moveto(current + (target - current) * 0.22)
        scroll_state["job"] = article_text.after(16, animate_scroll)

    def scroll_to_line(line_start):
        if reading_mode.get() == "normal":
            scroll_state["target"] = None
            article_text.see(line_start)
            return
        article_text.update_idletasks()
        before = article_text.count("1.0", line_start, "displaylines")
        all_lines = article_text.count("1.0", "end-1c", "displaylines")
        line = before[0] if before else 0
        total = (all_lines[0] if all_lines else 0) + 1
        first, last = article_text.yview()
        scroll_state["target"] = centered_scroll_fraction(line, total, last - first)
        if scroll_state["job"] is None:
            animate_scroll()

    def change_reading_mode():
        try:
            save_reading_mode(reading_mode.get())
        except OSError:
            pass
        if scroll_state["line"]:
            scroll_to_line(scroll_state["line"])

    def highlight_word(index, item):
        if not article_spans and player.timings:
            for span in align_word_spans(article, player.timings):
                article_spans.append(
                    None if span is None else (f"1.0+{span[0]}c", f"1.0+{span[1]}c")
                )
        if 0 <= index < len(article_spans) and article_spans[index]:
            start, end = article_spans[index]
            line_start = article_text.index(f"{start} display linestart")
            line_end = article_text.index(f"{start} display lineend")
            highlighted = tuple(map(str, article_text.tag_ranges("spoken")))
            if highlighted != (line_start, line_end):
                article_text.tag_remove("spoken", "1.0", "end")
                article_text.tag_add("spoken", line_start, line_end)
            scroll_state["line"] = line_start
            scroll_to_line(line_start)
        elif index < 0:
            article_text.tag_remove("spoken", "1.0", "end")
            scroll_state.update(line=None, target=None)

    def prepare_article_audio(show_error=True):
        audio = audio_dir / "article.mp3"
        timing = audio_dir / "article.timing.json"
        article_spans.clear()
        article_timings[:] = json.loads(timing.read_text(encoding="utf-8")) if timing.is_file() else []
        for span in align_word_spans(article, article_timings):
            if span is None:
                article_spans.append(None)
                continue
            start, end = span
            article_spans.append((f"1.0+{start}c", f"1.0+{end}c"))
        return player.queue(
            audio, timing, "Article", highlight_word,
            lambda: load_audio(audio, timing, "Article", article, highlight_word),
        )
    ttk.Label(
        article_actions,
        text="Double-click the article to jump audio to that position.",
        wraplength=150,
    ).pack(fill="x", pady=(12, 0))
    ttk.Label(article_actions, text="Reading mode").pack(anchor="w", pady=(16, 4))
    ttk.Radiobutton(
        article_actions, text="Normal", variable=reading_mode, value="normal",
        command=change_reading_mode,
    ).pack(anchor="w")
    ttk.Radiobutton(
        article_actions, text="Typewriter", variable=reading_mode, value="typewriter",
        command=change_reading_mode,
    ).pack(anchor="w")
    if translation:
        def toggle_translation():
            if translation_visible["value"]:
                chinese_frame.grid_remove()
                reading_frame.columnconfigure(1, weight=0)
                translation_button.config(text="Show Chinese")
            else:
                reading_frame.columnconfigure(1, weight=1)
                chinese_frame.grid()
                translation_text.yview_moveto(article_text.yview()[0])
                translation_button.config(text="Hide Chinese")
            translation_visible["value"] = not translation_visible["value"]

        translation_button = ttk.Button(
            article_actions, text="Show Chinese", command=toggle_translation
        )
        translation_button.pack(fill="x", pady=(12, 0))
    else:
        ttk.Button(
            article_actions,
            text="Add Chinese Translation",
            command=lambda: self._show_page(
                lambda parent: self._new_article(parent, article_dir)
            ),
        ).pack(fill="x", pady=(12, 0))

    ttk.Separator(article_actions).pack(fill="x", pady=16)
    ttk.Label(article_actions, text="Category").pack(anchor="w")
    category = tk.StringVar(value=article_dir.relative_to(LIBRARY_DIR / "text").parts[0])
    category_box = ttk.Combobox(
        article_actions, textvariable=category, values=CATEGORIES, state="readonly", width=1
    )
    category_box.pack(fill="x", pady=(4, 6))

    def article_busy():
        task = self.audio_tasks.get(str(article_dir))
        if task and task["status"] in ("Queued", "Generating"):
            messagebox.showinfo(
                "Article is busy",
                "Wait for its background audio task to finish before moving or deleting it.",
                parent=self,
            )
            return True
        return False

    def move_category():
        if article_busy():
            return
        if category.get() == article_dir.relative_to(LIBRARY_DIR / "text").parts[0]:
            return
        if not messagebox.askyesno(
            "Change category",
            f'Move this article to "{category.get()}"?',
            parent=self,
        ):
            return
        try:
            target = change_article_category(
                article_dir, category.get(), LIBRARY_DIR / "text", LIBRARY_DIR / "audio"
            )
            remember_recent_article(target)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            messagebox.showerror("Cannot change category", str(error), parent=self)
            return
        player.stop()
        self._replace_page(self._old_articles)

    def remove_article():
        if article_busy():
            return
        if not messagebox.askyesno(
            "Delete article",
            f'Permanently delete "{article_dir.name}" and its audio?\n\nThis cannot be undone.',
            icon="warning",
            parent=self,
        ):
            return
        player.stop()
        try:
            delete_article(article_dir, LIBRARY_DIR / "text", LIBRARY_DIR / "audio")
        except (OSError, ValueError) as error:
            messagebox.showerror("Cannot delete article", str(error), parent=self)
            return
        self._replace_page(self._old_articles)

    ttk.Button(article_actions, text="Change Category", command=move_category).pack(fill="x", pady=2)
    ttk.Button(article_actions, text="Delete Article", command=remove_article).pack(fill="x", pady=2)

    def jump_from_text(event):
        clicked = article_text.count("1.0", article_text.index(f"@{event.x},{event.y}"), "chars")[0]

        def jump():
            prepare_article_audio()
            index = nearest_span_index(clicked, align_word_spans(article, article_timings))
            if index is not None:
                player.seek_to(article_timings[index]["start"])

        if not (audio_dir / "article.timing.json").is_file():
            self._play_or_build(
                player, article, audio_dir / "article.mp3", audio_dir / "article.timing.json",
                "Article", status, highlight_word, jump,
            )
            return "break"
        prepare_article_audio()
        index = nearest_span_index(clicked, align_word_spans(article, article_timings))
        if index is not None:
            player.seek_to(article_timings[index]["start"])
        return "break"

    article_text.bind("<Double-1>", jump_from_text)

    card_panel = ttk.Frame(panes)
    card_panel.columnconfigure(0, weight=1, uniform="card-columns")
    card_panel.columnconfigure(1, weight=3, uniform="card-columns")
    card_panel.rowconfigure(0, weight=1)
    card_panel.rowconfigure(1, weight=3)
    cards = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((article_dir / "cards").glob("card_*.json"))
    ]
    card_actions = ttk.LabelFrame(card_panel, text="Card Audio", padding=6)
    card_actions.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 6))
    card_list = tk.Listbox(
        card_panel, exportselection=False, height=5, font=self.reader_content_font
    )
    for card in cards:
        card_list.insert("end", card["text"])
    card_list.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
    card_text = tk.Text(
        card_panel, wrap="word", height=12, font=self.reader_content_font
    )
    card_text.grid(row=0, column=1, rowspan=2, sticky="nsew")

    def selected_card():
        selection = card_list.curselection()
        if not selection:
            messagebox.showinfo("Select a card", "Select a card first.", parent=self)
            return None
        return cards[selection[0]]

    def show_card(event=None):
        card = selected_card()
        if not card:
            return
        card_text.config(state="normal")
        card_text.delete("1.0", "end")
        card_text.insert(
            "1.0",
            f"{card['text']}  [{card['type']} · {card['level']}]\n\n"
            f"{card['meaning_zh']}\n\n{card['example_en']}\n{card['example_zh']}",
        )
        card_text.config(state="disabled")

    def play_card(stem):
        card = selected_card()
        if card:
            card_audio = audio_dir / "cards" / card["id"]
            load_audio(
                card_audio / f"{stem}.mp3",
                card_audio / f"{stem}.timing.json",
                f'{card["text"]} — {"word / phrase" if stem == "text" else "example"}',
                card["text"] if stem == "text" else card["example_en"],
            )

    card_list.bind("<<ListboxSelect>>", show_card)
    ttk.Button(
        card_actions, text="Play Word / Phrase",
        command=lambda: play_card("text"),
    ).pack(fill="x", pady=2)
    ttk.Button(
        card_actions, text="Play Example",
        command=lambda: play_card("example"),
    ).pack(fill="x", pady=2)
    ttk.Button(card_actions, text="Stop Audio", command=player.stop).pack(fill="x", pady=2)
    if cards:
        card_list.selection_set(0)
        show_card()
    else:
        card_text.insert("1.0", "No cards have been imported.")
        card_text.config(state="disabled")
    panes.add(card_panel, text="Vocabulary Cards")

    def change_tab(event=None):
        player.stop()
        if panes.select() == str(article_panel):
            prepare_article_audio(show_error=False)

    panes.bind("<<NotebookTabChanged>>", change_tab)
    prepare_article_audio(show_error=False)
    return page

def old_articles(self, parent):
    page = ttk.Frame(parent, padding=16)
    header = ttk.Frame(page)
    header.pack(fill="x")
    ttk.Label(header, text="Library").pack(side="left")
    ttk.Button(
        header, text="Recent Articles",
        command=lambda: self._show_page(self._recent_articles),
    ).pack(side="right", padx=(8, 0))
    view_mode = {"value": "category"}
    status = ttk.Label(page, text="Select a folder to view its contents.")
    status.pack(side="bottom", fill="x", pady=(8, 0))
    tree = ttk.Treeview(page, columns=("type", "path"), displaycolumns=("type",))
    tree.heading("#0", text="Name", anchor="w")
    tree.heading("type", text="Type", anchor="w")
    tree.column("#0", width=520, stretch=True)
    tree.column("type", width=100, stretch=False)
    tree.pack(fill="both", expand=True, pady=(8, 0))
    text_root = LIBRARY_DIR / "text"

    def populate(item=""):
        path = text_root if not item else Path(tree.set(item, "path"))
        if not path.is_dir():
            return
        try:
            entries = list_directory(path)
        except OSError as error:
            status.config(text=str(error))
            return
        tree.delete(*tree.get_children(item))
        for entry in entries:
            child = tree.insert(
                item, "end", text=entry.name,
                values=("Folder" if entry.is_dir() else "File", str(entry)),
            )
            if entry.is_dir():
                tree.insert(child, "end", text="Loading…")
        status.config(text=f"{len(entries)} item(s) in {path}")

    def populate_date():
        tree.delete(*tree.get_children(""))
        nodes = {}
        articles = list_articles_by_date(text_root)
        for year, month, article in articles:
            year_node = nodes.get((year,))
            if not year_node:
                year_node = nodes[(year,)] = tree.insert(
                    "", "end", text=year, values=("Year", "")
                )
            month_node = nodes.get((year, month))
            if not month_node:
                month_node = nodes[(year, month)] = tree.insert(
                    year_node, "end", text=month, values=("Month", "")
                )
            tree.insert(
                month_node, "end", text=article.name,
                values=("Article", str(article)),
            )
        status.config(text=f"{len(articles)} article(s), grouped by year and month.")

    def toggle_view():
        if view_mode["value"] == "category":
            view_mode["value"] = "date"
            view_button.config(text="View by Category")
            populate_date()
        else:
            view_mode["value"] = "category"
            view_button.config(text="View by Date")
            tree.delete(*tree.get_children(""))
            populate()

    def refresh_selected():
        if view_mode["value"] == "date":
            populate_date()
            return
        selection = tree.selection()
        populate(tree.focus() or (selection[0] if selection else ""))

    def open_article(event=None):
        item = tree.focus()
        if not item:
            return
        stored_path = tree.set(item, "path")
        if not stored_path:
            return
        path = Path(stored_path)
        article_dir = path if path.is_dir() else path.parent
        if (article_dir / "article.md").is_file():
            self._show_page(lambda parent: self._article(parent, article_dir))

    view_button = ttk.Button(header, text="View by Date", command=toggle_view)
    view_button.pack(side="right", padx=(8, 0))
    ttk.Button(header, text="Refresh", command=refresh_selected).pack(side="right")

    def refresh_category_tree(event=None):
        if view_mode["value"] == "category":
            self.after_idle(refresh_selected)

    tree.bind("<<TreeviewOpen>>", refresh_category_tree)
    tree.bind("<ButtonRelease-1>", refresh_category_tree)
    tree.bind("<Double-1>", open_article)
    populate()
    return page

def recent_articles(self, parent):
    page = ttk.Frame(parent, padding=16)
    ttk.Label(page, text="Recently Read — latest 10").pack(anchor="w", pady=(0, 8))
    articles = load_recent_articles()
    if not articles:
        ttk.Label(page, text="No recently read articles.").pack(pady=40)
        return page
    tree = ttk.Treeview(page, columns=("category", "path"), displaycolumns=("category",))
    tree.heading("#0", text="Article", anchor="w")
    tree.heading("category", text="Category", anchor="w")
    tree.column("#0", width=560, stretch=True)
    tree.column("category", width=220, stretch=False)
    tree.pack(fill="both", expand=True)
    for article in articles:
        relative = article.relative_to(LIBRARY_DIR / "text")
        tree.insert("", "end", text=article.name, values=(relative.parts[0], str(article)))

    def open_selected(event=None):
        item = tree.focus()
        if item:
            article = Path(tree.set(item, "path"))
            self._show_page(lambda parent: self._article(parent, article))

    ttk.Button(page, text="Open", command=open_selected).pack(anchor="e", pady=(8, 0))
    tree.bind("<Double-1>", open_selected)
    return page
