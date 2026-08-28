import json
import re
import threading
import random
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox, ttk
from pathlib import Path

from .articles import import_analysis, import_cards, save_draft
from .player import AudioPlayer
from .review import complete_scheduled, daily_cards, dictation_matches, history_groups
from .settings import CATEGORIES, CATEGORIES_FILE, DRAFTS_DIR, LIBRARY_DIR, PROMPTS_DIR, load_reading_mode, load_zoom, save_reading_mode, save_zoom
from .tts import build_article_audio, build_speech, cleanup_audio_cache

RECENT_ARTICLES_FILE = LIBRARY_DIR / "recent_articles.json"


def list_directory(path):
    return sorted(
        (item for item in Path(path).iterdir() if not item.name.startswith(".")),
        key=lambda item: (not item.is_dir(), item.name.casefold()),
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


def parse_category_sources(markdown):
    rows, in_section = [], False
    for line in markdown.splitlines():
        if line.strip() == "## Default Categories":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section or not line.startswith("|"):
            continue
        cells = [cell.strip().strip("*") for cell in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0] != "Category" and not set(cells[0]) <= {"-", " "}:
            rows.append(tuple(cells))
    return rows


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


class EnglishReader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ultimate English Learner")
        self.geometry("900x600")
        self.minsize(640, 420)
        self._zoom_level = load_zoom()
        default_font = tkfont.Font(root=self, name="TkDefaultFont", exists=True)
        default_size = default_font.cget("size")
        self.reader_content_font = tkfont.Font(
            root=self,
            name="ReaderContentFont",
            family=default_font.cget("family"),
            size=round(default_size * 1.4),
        )
        body_size = self.reader_content_font.cget("size")
        self.reader_bold_font = tkfont.Font(root=self, name="ReaderBoldFont", family=default_font.cget("family"), size=body_size, weight="bold")
        self.reader_italic_font = tkfont.Font(root=self, name="ReaderItalicFont", family=default_font.cget("family"), size=body_size, slant="italic")
        self.reader_code_font = tkfont.Font(root=self, name="ReaderCodeFont", family="Consolas", size=body_size)
        self.reader_heading_fonts = {
            level: tkfont.Font(root=self, name=f"ReaderHeading{level}Font", family=default_font.cget("family"), size=round(body_size * scale), weight="bold")
            for level, scale in ((1, 1.8), (2, 1.5), (3, 1.25))
        }
        self._font_sizes = {
            name: tkfont.Font(root=self, name=name, exists=True).cget("size")
            for name in tkfont.names(root=self)
        }
        self._tree_row_height = 20
        self.audio_tasks = {}
        self.lazy_audio_jobs = set()
        self._page_stack = []
        self._current_page = None
        threading.Thread(
            target=lambda: cleanup_audio_cache(LIBRARY_DIR / "audio"), daemon=True
        ).start()

        toolbar = ttk.Frame(self, padding=(12, 8, 12, 0))
        toolbar.pack(fill="x")
        self.home_button = ttk.Button(toolbar, text="Home", command=self._show_home)
        self.home_button.pack(side="left")
        self.back_button = ttk.Button(toolbar, text="← Back", command=self._go_back)
        self.back_button.pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="−", width=3, command=lambda: self._zoom(-1)).pack(side="right")
        self.zoom_label = ttk.Label(toolbar, text="100%", width=6, anchor="center")
        self.zoom_label.pack(side="right")
        ttk.Button(toolbar, text="+", width=3, command=lambda: self._zoom(1)).pack(side="right")

        self.content = ttk.Frame(self, padding=12)
        self.content.pack(fill="both", expand=True)
        self._show_home()

        for sequence in ("<Control-plus>", "<Control-equal>", "<Control-KP_Add>"):
            self.bind_all(sequence, lambda event: self._zoom(1))
        for sequence in ("<Control-minus>", "<Control-KP_Subtract>"):
            self.bind_all(sequence, lambda event: self._zoom(-1))
        self.bind_all("<Control-0>", lambda event: self._reset_zoom())
        self.bind_all("<Control-MouseWheel>", self._mouse_zoom)
        self._apply_zoom(save=False)

    def _show(self, builder):
        for child in self.content.winfo_children():
            child.destroy()
        builder(self.content).pack(fill="both", expand=True)

    def _show_page(self, builder):
        self._page_stack.append(self._current_page)
        self._current_page = builder
        self.home_button.pack(side="left")
        self.back_button.pack(side="left", padx=(8, 0))
        self._show(builder)

    def _go_back(self):
        if not self._page_stack:
            self._show_home()
            return
        builder = self._page_stack.pop()
        if builder is None:
            self._show_home()
            return
        self._current_page = builder
        self._show(builder)

    def _show_home(self):
        self._page_stack.clear()
        self._current_page = None
        self.home_button.pack_forget()
        self.back_button.pack_forget()

        def build(parent):
            page = ttk.Frame(parent, padding=20)
            page.columnconfigure(0, weight=1)
            for row, (text, command) in enumerate((
                ("Daily Learning", lambda: self._show_page(self._daily)),
                ("New Article", lambda: self._show_page(self._new_article)),
                ("Old Articles", lambda: self._show_page(self._old_articles)),
                ("Material Generation Tasks", lambda: self._show_page(self._audio_tasks)),
            )):
                page.rowconfigure(row, weight=1)
                ttk.Button(page, text=text, command=command).grid(
                    row=row, column=0, sticky="nsew", padx=24, pady=12
                )
            return page

        self._show(build)

    def _zoom(self, direction):
        self._zoom_level = round(min(2.0, max(0.6, self._zoom_level + direction * 0.1)), 1)
        self._apply_zoom()
        return "break"

    def _reset_zoom(self):
        self._zoom_level = 1.0
        self._apply_zoom()
        return "break"

    def _apply_zoom(self, save=True):
        for name, size in self._font_sizes.items():
            scaled = round(size * self._zoom_level)
            tkfont.Font(root=self, name=name, exists=True).configure(
                size=scaled or (-1 if size < 0 else 1)
            )
        ttk.Style(self).configure(
            "Treeview", rowheight=round(self._tree_row_height * self._zoom_level)
        )
        self.zoom_label.config(text=f"{self._zoom_level:.0%}")
        self.update_idletasks()
        if save:
            try:
                save_zoom(self._zoom_level)
            except OSError:
                pass

    def _mouse_zoom(self, event):
        return self._zoom(1 if event.delta > 0 else -1)

    def _daily(self, parent):
        page = ttk.Frame(parent, padding=16)
        new, history = daily_cards(LIBRARY_DIR / "text")
        actions = ttk.Frame(page)
        actions.pack(fill="x", pady=(0, 12))
        ttk.Button(
            actions, text=f"New Cards ({len(new)})",
            command=lambda: self._show_page(lambda parent: self._review_modes(parent, new, "New Cards")),
        ).pack(side="left", padx=4)
        ttk.Button(
            actions, text=f"History Review ({len(history)})",
            command=lambda: self._show_page(lambda parent: self._history_cycles(parent, history)),
        ).pack(side="left", padx=4)
        ttk.Label(page, text="Suggested reading sources by category").pack(anchor="w", pady=(24, 6))
        body = ttk.Frame(page)
        body.pack(fill="both", expand=True)
        text = tk.Text(body, wrap="word", font=self.reader_content_font, padx=10, pady=8)
        scroll = ttk.Scrollbar(body, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        try:
            rows = parse_category_sources(CATEGORIES_FILE.read_text(encoding="utf-8"))
        except OSError as error:
            rows = [("Cannot read categories.md", str(error), "—")]
        for category, scope, sources in rows:
            text.insert("end", f"{category}\n", "category")
            text.insert("end", f"範圍：{scope}\n建議來源：{sources}\n\n")
        text.tag_configure("category", font=self.reader_content_font, spacing1=6)
        text.config(state="disabled")
        return page

    def _history_cycles(self, parent, cards):
        page = ttk.Frame(parent, padding=24)
        ttk.Label(page, text="History Review — choose a review cycle").pack(anchor="w", pady=(0, 16))
        groups = history_groups(cards)
        if not groups:
            ttk.Label(page, text="No cards are due.").pack(pady=40)
            return page
        for _, interval, age, group in groups:
            ttk.Button(
                page,
                text=f"{interval}-day interval · appeared {age} days ago · {len(group)} cards",
                command=lambda group=group, interval=interval: self._show_page(
                    lambda parent: self._review_modes(parent, group, f"History Review · {interval}-day interval")
                ),
            ).pack(fill="x", pady=6)
        return page

    def _review_modes(self, parent, cards, title):
        page = ttk.Frame(parent, padding=24)
        ttk.Label(page, text=f"{title} — choose a mode").pack(anchor="w", pady=(0, 16))
        if not cards:
            ttk.Label(page, text="No cards available.").pack(pady=40)
            return page
        for label, mode in (("English → Chinese", "en-zh"), ("Chinese → English", "zh-en"), ("Dictation", "dictation")):
            ttk.Button(
                page, text=label,
                command=lambda label=label, mode=mode: self._show_page(
                    lambda parent: self._review_order(parent, cards, f"{title} · {label}", mode)
                ),
            ).pack(fill="x", pady=6)
        return page

    def _review_order(self, parent, cards, title, mode):
        page = ttk.Frame(parent, padding=24)
        ttk.Label(page, text=f"{title} — card order").pack(anchor="w", pady=(0, 16))
        ttk.Button(
            page, text="In order",
            command=lambda: self._show_page(lambda parent: self._review_session(parent, list(cards), title, mode)),
        ).pack(fill="x", pady=6)
        ttk.Button(
            page, text="Random",
            command=lambda: self._show_page(
                lambda parent: self._review_session(parent, random.sample(cards, len(cards)), title, mode)
            ),
        ).pack(fill="x", pady=6)
        return page

    def _review_session(self, parent, cards, title, mode):
        page = ttk.Frame(parent, padding=16)
        header = ttk.Frame(page)
        header.pack(fill="x")
        ttk.Label(header, text=title).pack(side="left")
        if not cards:
            ttk.Label(page, text="No cards available.").pack(pady=40)
            return page

        body = ttk.Frame(page)
        body.pack(fill="both", expand=True, pady=(8, 0))
        sidebar = ttk.Frame(body, padding=(0, 0, 12, 0))
        sidebar.pack(side="left", fill="y")
        card_list = tk.Listbox(sidebar, width=28, exportselection=False)
        card_list.pack(fill="both", expand=True)
        for index, card in enumerate(cards, 1):
            card_list.insert("end", f'{index}. {card["text"]} — {card["meaning_zh"]}')
        main = ttk.Frame(body)
        main.pack(side="left", fill="both", expand=True)

        def toggle_list():
            if sidebar.winfo_manager():
                sidebar.pack_forget()
                list_button.config(text="Show List")
            else:
                sidebar.pack(side="left", fill="y", before=main)
                list_button.config(text="Hide List")

        list_button = ttk.Button(header, text="Hide List", command=toggle_list)
        list_button.pack(side="right")
        player = AudioPlayer(main)
        audio_actions = ttk.Frame(main)
        audio_actions.pack(fill="x", pady=8)
        content = tk.Text(main, wrap="word", height=10, font=self.reader_content_font)
        content.pack(fill="both", expand=True)
        answer = ttk.Entry(main, font=self.reader_content_font)
        if mode == "dictation":
            answer.pack(fill="x", pady=8)
        status = ttk.Label(main, text="")
        status.pack(fill="x")
        actions = ttk.Frame(main)
        actions.pack(fill="x", pady=8)
        state = {"index": 0, "revealed": False, "checked": False}

        def card_audio(card, kind):
            article_dir = card["_path"].parents[1]
            audio_dir = LIBRARY_DIR / "audio" / article_dir.relative_to(LIBRARY_DIR / "text")
            base = audio_dir / "cards" / card["id"] / kind
            return base.with_suffix(".mp3"), base.with_suffix(".timing.json")

        def show():
            card = cards[state["index"]]
            content.config(state="normal")
            content.delete("1.0", "end")
            if mode == "dictation":
                shown = "Listen and type the complete example sentence."
                hidden = f'\n\n{card["example_en"]}'
            elif mode == "en-zh":
                shown = f'{card["text"]}\n\n{card["example_en"]}'
                hidden = f'\n\n{card["meaning_zh"]}\n{card["example_zh"]}'
            else:
                shown = f'{card["meaning_zh"]}\n\n{card["example_zh"]}'
                hidden = f'\n\n{card["text"]}\n{card["example_en"]}'
            content.insert("1.0", shown + (hidden if state["revealed"] else ""))
            content.config(state="disabled")
            answer.delete(0, "end")
            status.config(text=f'{state["index"] + 1} / {len(cards)} · Due {card["_due"]}')
            card_list.selection_clear(0, "end")
            card_list.selection_set(state["index"])
            card_list.see(state["index"])

        def play(kind):
            card = cards[state["index"]]
            text = card["text"] if kind == "text" else card["example_en"]
            audio, timing = card_audio(card, kind)
            self._play_or_build(player, text, audio, timing, card["text"], status)

        def reveal():
            state["revealed"] = not state["revealed"]
            show()

        def check():
            if state["checked"]:
                next_card()
                return
            card = cards[state["index"]]
            correct = dictation_matches(answer.get(), card["example_en"])
            if not complete(card):
                return
            state.update(revealed=True, checked=True)
            show()
            status.config(text="Correct. Press Enter to continue." if correct else f'Incorrect. Expected: {card["example_en"]} · Press Enter to continue.')

        def complete(card):
            try:
                complete_scheduled(card)
            except (OSError, ValueError) as error:
                messagebox.showerror("Cannot save review", str(error), parent=self)
                return False
            return True

        def advance():
            if complete(cards[state["index"]]):
                next_card()

        def previous_card():
            if state["index"] == 0:
                return
            player.stop()
            state.update(index=state["index"] - 1, revealed=False, checked=False)
            show()

        def select_card(event=None):
            selection = card_list.curselection()
            if not selection or selection[0] == state["index"]:
                return
            player.stop()
            state.update(index=selection[0], revealed=False, checked=False)
            show()

        def next_card():
            player.stop()
            state["index"] += 1
            if state["index"] >= len(cards):
                player.stop()
                for widget in (content, answer, actions):
                    widget.pack_forget()
                status.config(text="Session complete.")
                return
            state.update(revealed=False, checked=False)
            show()

        ttk.Button(audio_actions, text="Play Word", command=lambda: play("text")).pack(side="left", padx=4)
        ttk.Button(audio_actions, text="Play Example", command=lambda: play("example")).pack(side="left", padx=4)
        ttk.Button(actions, text="Previous", command=previous_card).pack(side="left", padx=4)
        if mode == "dictation":
            answer.bind("<Return>", lambda event: check())
            answer.focus_set()
            ttk.Button(actions, text="Next", command=advance).pack(side="left", padx=4)
        else:
            ttk.Button(actions, text="Show Answer", command=reveal).pack(side="left", padx=4)
            ttk.Button(actions, text="Next", command=advance).pack(side="left", padx=4)
        card_list.bind("<<ListboxSelect>>", select_card)
        show()
        return page

    def _play_or_build(self, player, text, audio, timing, label, status, on_word=None, on_ready=None):
        key = str(audio)
        def missing():
            if key in self.lazy_audio_jobs:
                return
            self.lazy_audio_jobs.add(key)
            status.config(text="Generating audio…")

            def worker():
                try:
                    build_speech(text, audio, timing)
                except Exception as error:
                    message = str(error)
                    self.after(0, lambda: failed(message))
                    return
                self.after(0, ready)

            threading.Thread(target=worker, daemon=True).start()

        def ready():
            self.lazy_audio_jobs.discard(key)
            status.config(text="Audio ready.")
            player.queue(audio, timing, label, on_word, missing)
            (on_ready or player.toggle)()

        def failed(message):
            self.lazy_audio_jobs.discard(key)
            status.config(text=f"TTS error: {message}")

        player.queue(audio, timing, label, on_word, missing)
        player.toggle()

    def _start_audio_task(self, article_dir):
        article_dir = Path(article_dir)
        key = str(article_dir)
        current = self.audio_tasks.get(key)
        if current and current["status"] in ("Queued", "Generating"):
            return
        task = {"article": article_dir, "completed": 0, "total": 1, "status": "Queued", "detail": ""}
        self.audio_tasks[key] = task
        audio_dir = LIBRARY_DIR / "audio" / article_dir.relative_to(LIBRARY_DIR / "text")

        def progress(completed, total, detail):
            task.update(completed=completed, total=total, status="Generating", detail=detail)

        def worker():
            try:
                task["status"] = "Generating"
                build_article_audio(article_dir, audio_dir, progress)
            except Exception as error:
                task.update(status="Failed", detail=str(error))
            else:
                task.update(status="Complete", detail="Audio ready")

        threading.Thread(target=worker, daemon=True).start()

    def _audio_tasks(self, parent):
        page = ttk.Frame(parent, padding=16)
        ttk.Label(page, text="Material Generation Tasks").pack(anchor="w", pady=(0, 12))
        tasks = ttk.Frame(page)
        tasks.pack(fill="both", expand=True)

        def refresh():
            try:
                exists = page.winfo_exists()
            except tk.TclError:
                return
            if not exists:
                return
            for child in tasks.winfo_children():
                child.destroy()
            if not self.audio_tasks:
                ttk.Label(tasks, text="No material generation tasks.").pack(anchor="w")
            for task in self.audio_tasks.values():
                row = ttk.LabelFrame(tasks, text=task["article"].name, padding=8)
                row.pack(fill="x", pady=5)
                ttk.Label(row, text=f'{task["status"]}: {task["detail"]}').pack(anchor="w")
                ttk.Progressbar(
                    row, maximum=max(1, task["total"]), value=task["completed"]
                ).pack(fill="x", pady=(5, 0))
                if task["status"] == "Failed":
                    ttk.Button(
                        row, text="Retry", command=lambda path=task["article"]: self._start_audio_task(path)
                    ).pack(anchor="e", pady=(5, 0))
            page.after(250, refresh)

        refresh()
        return page

    def _new_article(self, parent):
        page = ttk.Frame(parent, padding=16)

        def editor(title, help_text, prompt_name):
            for child in page.winfo_children():
                child.destroy()
            page.columnconfigure(0, weight=1)
            page.columnconfigure(1, weight=1)
            page.rowconfigure(1, weight=1)
            ttk.Label(page, text=f"Prompt: {prompt_name}").grid(row=0, column=0, sticky="w")
            ttk.Label(page, text=title).grid(row=0, column=1, sticky="w")
            prompt_path = PROMPTS_DIR / prompt_name
            prompt_text = tk.Text(page, wrap="word", undo=True)
            prompt_text.insert("1.0", prompt_path.read_text(encoding="utf-8"))
            prompt_text.grid(row=1, column=0, sticky="nsew", padx=(0, 6), pady=8)
            text = tk.Text(page, wrap="word", undo=True)
            text.grid(row=1, column=1, sticky="nsew", padx=(6, 0), pady=8)
            actions = ttk.Frame(page)
            actions.grid(row=2, column=0, columnspan=2, sticky="e")
            status = ttk.Label(page, text=help_text)
            status.grid(row=3, column=0, columnspan=2, sticky="w")

            def copy():
                self.clipboard_clear()
                self.clipboard_append(prompt_text.get("1.0", "end-1c").rstrip())

            def save_prompt():
                content = prompt_text.get("1.0", "end-1c").rstrip()
                if not content:
                    messagebox.showerror("Cannot save prompt", "Prompt cannot be empty.", parent=self)
                    return
                if not messagebox.askyesno(
                    "確認覆蓋", "你確定要覆蓋原始檔案嗎？", parent=self
                ):
                    return
                try:
                    prompt_path.write_text(
                        content + "\n", encoding="utf-8"
                    )
                except OSError as error:
                    messagebox.showerror("Cannot save prompt", str(error), parent=self)
                    return
                status.config(text=f"Saved: {prompt_path}")

            ttk.Button(actions, text="Save Prompt", command=save_prompt).pack(side="left", padx=4)
            return text, actions, status, copy

        def show_cards(article_dir):
            text, actions, status, copy_prompt = editor(
                "Paste cards.json from AI",
                "Stage 2: generate exactly one card for every analysis item.",
                "generate_cards.md",
            )

            def copy():
                copy_prompt()
                status.config(text="Card generation request copied to clipboard.")

            def save():
                try:
                    import_cards(article_dir, json.loads(text.get("1.0", "end-1c")))
                except (OSError, ValueError, json.JSONDecodeError) as error:
                    messagebox.showerror("Invalid cards.json", str(error), parent=self)
                    return
                self._start_audio_task(article_dir)
                for child in page.winfo_children():
                    child.destroy()
                ttk.Label(page, text="Article saved. Audio is being generated in the background.").pack(pady=40)
                ttk.Button(
                    page, text="View Generation Tasks",
                    command=lambda: self._show_page(self._audio_tasks),
                ).pack(pady=6)
                ttk.Button(
                    page, text="New Article",
                    command=lambda: self._show_page(self._new_article),
                ).pack(pady=6)

            ttk.Button(actions, text="Copy Stage 2 Request", command=copy).pack(side="left", padx=4)
            ttk.Button(actions, text="Import cards.json", command=save).pack(side="left", padx=4)

        def show_analysis(draft):
            text, actions, status, copy_prompt = editor(
                "Paste analysis.json from AI",
                "Stage 1: AI must choose an existing Category.",
                "analyze_article.md",
            )

            def copy():
                copy_prompt()
                status.config(text="Article analysis request copied to clipboard.")

            def save():
                try:
                    article_dir = import_analysis(
                        draft,
                        json.loads(text.get("1.0", "end-1c")),
                        CATEGORIES,
                        LIBRARY_DIR / "text",
                        LIBRARY_DIR / "audio",
                    )
                except (OSError, ValueError, json.JSONDecodeError) as error:
                    messagebox.showerror("Invalid analysis.json", str(error), parent=self)
                    return
                show_cards(article_dir)

            ttk.Button(actions, text="Copy Stage 1 Request", command=copy).pack(side="left", padx=4)
            ttk.Button(actions, text="Import analysis.json", command=save).pack(side="left", padx=4)

        text, actions, status, copy_prompt = editor(
            "Paste an AI-cleaned article",
            "Only cleaned article text is stored.",
            "clean_article.md",
        )

        def save_article():
            try:
                draft = save_draft(text.get("1.0", "end-1c"), DRAFTS_DIR)
            except (OSError, ValueError) as error:
                messagebox.showerror("Cannot save article", str(error), parent=self)
                return
            show_analysis(draft)

        def copy_cleaning_prompt():
            copy_prompt()
            status.config(text="Article cleaning prompt copied to clipboard.")

        ttk.Button(actions, text="Copy Cleaning Prompt", command=copy_cleaning_prompt).pack(side="left", padx=4)
        ttk.Button(actions, text="Save Article", command=save_article).pack(side="left", padx=4)
        return page

    def _article(self, parent, article_dir):
        try:
            remember_recent_article(article_dir)
        except (OSError, ValueError):
            pass
        page = ttk.Frame(parent, padding=16)
        header = ttk.Frame(page)
        header.pack(fill="x")
        ttk.Button(
            header, text="← Old Articles",
            command=lambda: self._show_page(self._old_articles),
        ).pack(side="left")
        ttk.Label(header, text=article_dir.name).pack(side="left", padx=12)
        status = ttk.Label(page, text="Ready.")
        status.pack(side="bottom", fill="x", pady=(8, 0))

        article = (article_dir / "article.md").read_text(encoding="utf-8")
        audio_dir = LIBRARY_DIR / "audio" / article_dir.relative_to(LIBRARY_DIR / "text")

        panes = ttk.Notebook(page)
        panes.pack(fill="both", expand=True, pady=(8, 0))
        article_panel = ttk.Frame(panes, padding=6)
        article_panel.columnconfigure(0, weight=4)
        article_panel.columnconfigure(1, weight=1)
        article_panel.rowconfigure(1, weight=1)
        panes.add(article_panel, text="Article")

        player = AudioPlayer(article_panel, show_time=True)
        player.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        def load_audio(audio, timing, label, text, on_word=None):
            self._play_or_build(player, text, audio, timing, label, status, on_word)

        article_text = tk.Text(article_panel, wrap="word", font=self.reader_content_font)
        rendered_article, markdown_tags = markdown_layout(article)
        article_text.insert("1.0", rendered_article)
        article_text.tag_configure("syntax", elide=True)
        article_text.tag_configure("bold", font=self.reader_bold_font)
        article_text.tag_configure("italic", font=self.reader_italic_font)
        article_text.tag_configure("code", font=self.reader_code_font, background="#eeeeee")
        article_text.tag_configure("code_block", font=self.reader_code_font, background="#eeeeee", lmargin1=16, lmargin2=16)
        article_text.tag_configure("quote", foreground="#555555", lmargin1=20, lmargin2=20)
        article_text.tag_configure("list", lmargin1=12, lmargin2=30)
        for level, font in self.reader_heading_fonts.items():
            article_text.tag_configure(f"heading{level}", font=font, spacing1=10, spacing3=6)
        for tag, start, end in markdown_tags:
            article_text.tag_add(tag, f"1.0+{start}c", f"1.0+{end}c")
        article_text.tag_configure("spoken", background="#ffe66d", foreground="#111111")
        article_text.config(state="disabled")
        article_text.grid(row=1, column=0, sticky="nsew", padx=(0, 6))

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

    def _old_articles(self, parent):
        page = ttk.Frame(parent, padding=16)
        header = ttk.Frame(page)
        header.pack(fill="x")
        ttk.Label(header, text="Library").pack(side="left")
        ttk.Button(
            header, text="Recent Articles",
            command=lambda: self._show_page(self._recent_articles),
        ).pack(side="right", padx=(8, 0))
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

        def refresh_selected():
            selection = tree.selection()
            populate(tree.focus() or (selection[0] if selection else ""))

        def open_article(event=None):
            item = tree.focus()
            if not item:
                return
            path = Path(tree.set(item, "path"))
            article_dir = path if path.is_dir() else path.parent
            if (article_dir / "article.md").is_file():
                self._show_page(lambda parent: self._article(parent, article_dir))

        ttk.Button(header, text="Refresh", command=refresh_selected).pack(side="right")
        tree.bind("<<TreeviewOpen>>", lambda event: refresh_selected())
        tree.bind("<ButtonRelease-1>", lambda event: self.after_idle(refresh_selected))
        tree.bind("<Double-1>", open_article)
        populate()
        return page

    def _recent_articles(self, parent):
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


def run():
    EnglishReader().mainloop()
