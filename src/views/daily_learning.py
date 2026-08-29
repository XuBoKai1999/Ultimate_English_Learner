import random
import tkinter as tk
from tkinter import messagebox, ttk

from ..player import AudioPlayer
from ..review import complete_scheduled, daily_cards, dictation_matches, history_groups
from ..settings import CATEGORIES_FILE, LIBRARY_DIR


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


def daily(self, parent):
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

def history_cycles(self, parent, cards):
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

def review_modes(self, parent, cards, title):
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

def review_order(self, parent, cards, title, mode):
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

def review_session(self, parent, cards, title, mode):
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

