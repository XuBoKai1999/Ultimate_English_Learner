import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from ..articles import import_analysis, import_cards, save_draft, save_translation
from ..settings import CATEGORIES, DRAFTS_DIR, LIBRARY_DIR, PROMPTS_DIR


def new_article(self, parent, translation_target=None):
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
            "Stage 3: generate exactly one card for every analysis item.",
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

        ttk.Button(actions, text="Copy Stage 3 Request", command=copy).pack(side="left", padx=4)
        ttk.Button(actions, text="Import cards.json", command=save).pack(side="left", padx=4)

    def show_analysis(draft):
        text, actions, status, copy_prompt = editor(
            "Paste analysis.json from AI",
            "Stage 2: AI must choose an existing Category.",
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

        ttk.Button(actions, text="Copy Stage 2 Request", command=copy).pack(side="left", padx=4)
        ttk.Button(actions, text="Import analysis.json", command=save).pack(side="left", padx=4)

    def show_translation(draft):
        text, actions, status, copy_prompt = editor(
            "Paste the complete Traditional Chinese translation",
            "Stage 1: translate the full cleaned article without summarizing.",
            "translate_article.md",
        )

        def copy():
            copy_prompt()
            status.config(text="Article translation request copied to clipboard.")

        def save():
            try:
                save_translation(draft, text.get("1.0", "end-1c"))
            except (OSError, ValueError) as error:
                messagebox.showerror("Cannot save translation", str(error), parent=self)
                return
            if translation_target is not None:
                self._replace_page(lambda parent: self._article(parent, Path(draft)))
            else:
                show_analysis(draft)

        ttk.Button(actions, text="Copy Stage 1 Request", command=copy).pack(side="left", padx=4)
        ttk.Button(actions, text="Save Translation", command=save).pack(side="left", padx=4)

    if translation_target is not None:
        show_translation(Path(translation_target))
        return page

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
        show_translation(draft)

    def copy_cleaning_prompt():
        copy_prompt()
        status.config(text="Article cleaning prompt copied to clipboard.")

    ttk.Button(actions, text="Copy Cleaning Prompt", command=copy_cleaning_prompt).pack(side="left", padx=4)
    ttk.Button(actions, text="Save Article", command=save_article).pack(side="left", padx=4)
    return page

