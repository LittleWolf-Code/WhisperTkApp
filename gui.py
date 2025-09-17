import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from transcriber import Transcriber
from analysis import GrammarAnalyzer, PronunciationAnalyzer
from config import AppConfig

class WhisperTkApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Whisper Real-Time Subtitle App")
        self.geometry("800x400")
        self.configure(bg="#222")
        self.config = AppConfig()
        self.transcriber = Transcriber(self.config)
        self.grammar = GrammarAnalyzer()
        self.pronunciation = PronunciationAnalyzer()
        self.subtitle_text = tk.Text(self, font=("Arial", 18), fg="white", bg="#222", height=2, wrap="word", borderwidth=0, highlightthickness=0)
        self.subtitle_text.pack(pady=20, fill="x")
        self.subtitle_text.tag_configure("bad_pron", foreground="red")
        self.correction_label = tk.Label(self, text="Correction ici...", font=("Arial", 14), fg="lightgreen", bg="#222")
        self.correction_label.pack(pady=10)
        self.listen_active = False
        self.toggle_button = tk.Button(self, text="Démarrer", command=self.toggle_listen)
        self.toggle_button.pack(pady=10)
        self.settings_button = tk.Button(self, text="Paramètres", command=self.open_settings)
        self.settings_button.place(relx=0.98, rely=0.02, anchor="ne")
        self.transcriber.start(self.update_subtitle)
    def toggle_listen(self):
        if not self.listen_active:
            self.listen_active = True
            self.toggle_button.config(text="Arrêter")
            self.transcriber.resume()
        else:
            self.listen_active = False
            self.toggle_button.config(text="Démarrer")
            self.transcriber.pause()
    def open_settings(self):
        self.config.open_settings(self)
    def update_subtitle(self, text):
        grammar_errors = self.grammar.check(text)
        corrected = self.grammar.correct(text)
        pronunciation_errors = self.pronunciation.check(text)
        self.subtitle_text.config(state="normal")
        self.subtitle_text.delete("1.0", tk.END)
        words = text.split()
        for word in words:
            start_idx = self.subtitle_text.index(tk.INSERT)
            self.subtitle_text.insert(tk.END, word + " ")
            end_idx = self.subtitle_text.index(tk.INSERT)
            percent = 100 if not (pronunciation_errors and word in pronunciation_errors) else 0
            self.subtitle_text.insert(tk.END, f"({percent}%) ")
            if pronunciation_errors and word in pronunciation_errors:
                self.subtitle_text.tag_add("bad_pron", start_idx, f"{end_idx}-1c")
        self.subtitle_text.config(state="disabled")
        self.correction_label.config(text=f"Correction: {corrected}")
