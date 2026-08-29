import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from pathlib import Path

from .settings import LIBRARY_DIR, load_zoom, save_zoom
from .tts import build_article_audio, build_speech, cleanup_audio_cache
from .views.daily_learning import daily, history_cycles, parse_category_sources, review_modes, review_order, review_session
from .views.new_article import new_article
from .views.old_articles import align_word_spans, article, centered_scroll_fraction, estimate_english_reading, list_articles_by_date, list_directory, load_recent_articles, markdown_layout, nearest_span_index, old_articles, recent_articles, remember_recent_article

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

    def _replace_page(self, builder):
        self._current_page = builder
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

    _daily = daily
    _history_cycles = history_cycles
    _review_modes = review_modes
    _review_order = review_order
    _review_session = review_session

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

    _new_article = new_article

    _article = article
    _old_articles = old_articles
    _recent_articles = recent_articles

def run():
    EnglishReader().mainloop()
