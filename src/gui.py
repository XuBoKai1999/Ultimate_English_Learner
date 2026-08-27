import json
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox, ttk
from pathlib import Path

from .articles import import_analysis, import_cards, save_draft
from .player import AudioPlayer
from .settings import CATEGORIES, CATEGORIES_FILE, DRAFTS_DIR, LIBRARY_DIR, PROMPTS_DIR, load_zoom, save_zoom
from .tts import build_article_audio

def list_directory(path):
    return sorted(
        (item for item in Path(path).iterdir() if not item.name.startswith(".")),
        key=lambda item: (not item.is_dir(), item.name.casefold()),
    )


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
        self._font_sizes = {
            name: tkfont.Font(root=self, name=name, exists=True).cget("size")
            for name in tkfont.names(root=self)
        }
        self._tree_row_height = 20
        self.audio_tasks = {}

        toolbar = ttk.Frame(self, padding=(12, 8, 12, 0))
        toolbar.pack(fill="x")
        self.home_button = ttk.Button(toolbar, text="Home", command=self._show_home)
        self.home_button.pack(side="left")
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
        self.home_button.pack(side="left")
        self._show(builder)

    def _show_home(self):
        self.home_button.pack_forget()

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
        ttk.Label(page, text="No cards are due today.").pack(anchor="w")
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

        player = AudioPlayer(article_panel)
        player.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        def load_audio(audio, timing, label=None, on_word=None):
            if player.load(audio, timing, label, on_word):
                player.toggle()
                return True
            return False

        def rebuild_audio():
            self._start_audio_task(article_dir)
            status.config(text="Audio task started in background.")

        article_text = tk.Text(article_panel, wrap="word", font=self.reader_content_font)
        article_text.insert("1.0", article)
        article_text.tag_configure("spoken", background="#ffe66d", foreground="#111111")
        article_text.config(state="disabled")
        article_text.grid(row=1, column=0, sticky="nsew", padx=(0, 6))

        article_actions = ttk.LabelFrame(article_panel, text="Functions", padding=8)
        article_actions.grid(row=1, column=1, sticky="nsew")

        article_spans = []
        article_timings = []

        def highlight_word(index, item):
            article_text.tag_remove("spoken", "1.0", "end")
            if 0 <= index < len(article_spans) and article_spans[index]:
                start, end = article_spans[index]
                line_start = article_text.index(f"{start} display linestart")
                line_end = article_text.index(f"{start} display lineend")
                article_text.tag_add("spoken", line_start, line_end)
                article_text.see(line_start)

        def prepare_article_audio(show_error=True):
            audio = audio_dir / "article.mp3"
            timing = audio_dir / "article.timing.json"
            if not audio.is_file() or not timing.is_file():
                if show_error:
                    player.load(audio, timing)
                else:
                    status.config(text="Article audio has not been built yet.")
                return False
            article_spans.clear()
            article_timings[:] = json.loads(timing.read_text(encoding="utf-8"))
            for span in align_word_spans(article, article_timings):
                if span is None:
                    article_spans.append(None)
                    continue
                start, end = span
                article_spans.append((f"1.0+{start}c", f"1.0+{end}c"))
            return player.queue(audio, timing, "Article", highlight_word)

        ttk.Button(
            article_actions, text="Build Missing Audio", command=rebuild_audio
        ).pack(fill="x", pady=3)
        ttk.Label(
            article_actions,
            text="Double-click the article to jump audio to that position.",
            wraplength=150,
        ).pack(fill="x", pady=(12, 0))

        def jump_from_text(event):
            if not article_timings and not prepare_article_audio():
                return "break"
            clicked = article_text.count("1.0", article_text.index(f"@{event.x},{event.y}"), "chars")[0]
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


def run():
    EnglishReader().mainloop()
