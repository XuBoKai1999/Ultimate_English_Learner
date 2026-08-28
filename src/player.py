import json
import os
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import pygame


class AudioPlayer(ttk.LabelFrame):
    def __init__(self, parent):
        super().__init__(parent, text="Audio")
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        self.audio = None
        self.pending = None
        self.on_missing = None
        self.timings = []
        self.duration = 0.0
        self.position = 0.0
        self.playing = False
        self.dragging = False
        self.on_word = None
        self._word_index = -1

        controls = ttk.Frame(self)
        controls.pack(fill="x", padx=8, pady=6)
        self.play_button = ttk.Button(controls, text="Play", command=self.toggle)
        self.play_button.pack(side="left")
        ttk.Button(controls, text="Stop", command=self.stop).pack(side="left", padx=4)
        ttk.Button(controls, text="Replay", command=self.replay).pack(side="left")
        self.track_label = ttk.Label(controls, text="No audio selected")
        self.track_label.pack(side="left", padx=12)

        self.progress = tk.DoubleVar()
        scale = ttk.Scale(self, from_=0, to=1000, variable=self.progress)
        scale.pack(fill="x", padx=8)
        scale.bind("<ButtonPress-1>", lambda event: setattr(self, "dragging", True))
        scale.bind("<ButtonRelease-1>", self.seek)
        self.bind("<Destroy>", self._destroy)
        self.after(100, self._tick)

    def _destroy(self, event):
        if event.widget is self:
            pygame.mixer.music.stop()

    def load(self, audio, timing, label=None, on_word=None):
        audio = Path(audio)
        timing = Path(timing)
        if not audio.is_file() or not timing.is_file():
            messagebox.showerror("Audio unavailable", "Audio has not been built for this item.", parent=self)
            return False
        self.stop()
        self.audio = audio
        self.pending = None
        self.on_missing = None
        self.timings = json.loads(timing.read_text(encoding="utf-8"))
        self.on_word = on_word
        self._word_index = -1
        self.duration = pygame.mixer.Sound(str(audio)).get_length()
        pygame.mixer.music.load(str(audio))
        try:
            os.utime(audio)
            os.utime(timing)
        except OSError:
            pass
        self.track_label.config(text=label or audio.stem)
        return True

    def queue(self, audio, timing, label=None, on_word=None, on_missing=None):
        audio, timing = Path(audio), Path(timing)
        self.stop()
        self.audio = None
        self.pending = (audio, timing, label, on_word)
        self.on_missing = on_missing
        self.track_label.config(text=label or audio.stem)
        return True

    def _load_pending(self):
        if self.audio:
            return True
        if not self.pending:
            return False
        pending = self.pending
        if not pending[0].is_file() or not pending[1].is_file():
            if self.on_missing:
                self.on_missing()
            return False
        return self.load(*pending)

    def _current(self):
        elapsed = pygame.mixer.music.get_pos()
        return self.position + max(0, elapsed) / 1000 if self.playing else self.position

    def toggle(self):
        if not self._load_pending():
            return
        if self.playing:
            self.position = min(self.duration, self._current())
            pygame.mixer.music.stop()
            self.playing = False
            self.play_button.config(text="Play")
        else:
            pygame.mixer.music.play(start=self.position)
            self.playing = True
            self.play_button.config(text="Pause")

    def stop(self):
        pygame.mixer.music.stop()
        self.position = 0.0
        self.playing = False
        self.progress.set(0)
        self.play_button.config(text="Play")
        self._word_index = -1
        if self.on_word:
            self.on_word(-1, None)

    def replay(self):
        if self._load_pending():
            self.position = 0.0
            pygame.mixer.music.play(start=0.0)
            self.playing = True
            self.play_button.config(text="Pause")

    def seek(self, event=None):
        if not self.audio:
            return
        self.dragging = False
        self.seek_to(self.duration * self.progress.get() / 1000, self.playing)

    def seek_to(self, seconds, play=True):
        if not self._load_pending():
            return
        self.position = min(self.duration, max(0.0, seconds))
        pygame.mixer.music.stop()
        if play:
            pygame.mixer.music.play(start=self.position)
            self.playing = True
            self.play_button.config(text="Pause")
        else:
            self.playing = False
            self.play_button.config(text="Play")
        self.progress.set(self.position / self.duration * 1000 if self.duration else 0)

    def _tick(self):
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if self.audio and self.duration:
            current = min(self.duration, self._current())
            if not self.dragging:
                self.progress.set(current / self.duration * 1000)
            index = next(
                (index for index in range(len(self.timings) - 1, -1, -1)
                 if self.timings[index]["start"] <= current),
                -1,
            )
            if index != self._word_index:
                self._word_index = index
                if self.on_word:
                    self.on_word(index, self.timings[index] if index >= 0 else None)
            if self.playing and not pygame.mixer.music.get_busy():
                self.playing = False
                self.position = 0.0
                self.play_button.config(text="Play")
        self.after(100, self._tick)
