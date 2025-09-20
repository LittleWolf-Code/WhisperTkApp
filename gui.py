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
        self.geometry("800x600")  # Fenêtre plus grande
        self.configure(bg="#222")
        self.config = AppConfig()
        self.transcriber = Transcriber(self.config)
        self.grammar = GrammarAnalyzer()
        self.pronunciation = PronunciationAnalyzer()
        
        # Frame pour la zone de texte avec scrollbar
        text_frame = tk.Frame(self, bg="#222")
        text_frame.pack(pady=20, fill="both", expand=True)
        
        # Zone de texte avec scrollbar
        self.subtitle_text = tk.Text(text_frame, font=("Arial", 14), fg="white", bg="#222", 
                                   wrap="word", borderwidth=0, highlightthickness=0, height=15)
        scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=self.subtitle_text.yview)
        self.subtitle_text.configure(yscrollcommand=scrollbar.set)
        
        self.subtitle_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.subtitle_text.tag_configure("bad_pron", foreground="red")
        self.subtitle_text.tag_configure("timestamp", foreground="gray", font=("Arial", 10))
        
        self.correction_label = tk.Label(self, text="Correction ici...", font=("Arial", 14), fg="lightgreen", bg="#222")
        self.correction_label.pack(pady=10)
        
        # Frame pour les boutons
        button_frame = tk.Frame(self, bg="#222")
        button_frame.pack(pady=10)
        
        self.listen_active = False
        self.toggle_button = tk.Button(button_frame, text="Démarrer", command=self.toggle_listen)
        self.toggle_button.pack(side="left", padx=5)
        
        # Bouton pour effacer l'historique
        self.clear_button = tk.Button(button_frame, text="Effacer historique", command=self.clear_history)
        self.clear_button.pack(side="left", padx=5)
        
        self.settings_button = tk.Button(button_frame, text="Paramètres", command=self.open_settings)
        self.settings_button.pack(side="left", padx=5)
        
        self.transcriber.start(self.update_subtitle)
        
    def clear_history(self):
        """Efface l'historique du texte transcrit"""
        self.subtitle_text.config(state="normal")
        self.subtitle_text.delete("1.0", tk.END)
        self.subtitle_text.config(state="disabled")
        
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
        import datetime
        
        # Avec le nouveau système de segments, chaque texte est unique
        # Plus besoin de détecter les répétitions
        
        # Si pas de texte, ne rien afficher
        if not text.strip():
            return
            
        grammar_errors = self.grammar.check(text)
        corrected = self.grammar.correct(text)
        pronunciation_errors = self.pronunciation.check(text)
        
        # Ajouter le texte complet à l'affichage
        self.subtitle_text.config(state="normal")
        
        # Ajouter horodatage visible
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        self.subtitle_text.insert(tk.END, f"\n[{time_str}] ")
        self.subtitle_text.tag_add("timestamp", f"end-{len(time_str)+4}c", f"end-1c")
        
        # Ajouter le texte transcrit avec mise en forme
        words = text.split()
        for word in words:
            start_idx = self.subtitle_text.index(tk.INSERT)
            self.subtitle_text.insert(tk.END, word + " ")
            end_idx = self.subtitle_text.index(tk.INSERT)
            
            # Afficher les pourcentages seulement si activé
            if self.config.show_percentages:
                percent = 100 if not (pronunciation_errors and word in pronunciation_errors) else 0
                self.subtitle_text.insert(tk.END, f"({percent}%) ")
            
            # Appliquer les couleurs seulement si activé
            if self.config.show_colors and pronunciation_errors and word in pronunciation_errors:
                self.subtitle_text.tag_add("bad_pron", start_idx, f"{end_idx}-1c")
        
        # Auto-scroll vers le bas pour voir le nouveau contenu
        self.subtitle_text.see(tk.END)
        
        # Auto-scroll vers le bas pour voir le nouveau contenu
        self.subtitle_text.see(tk.END)        
        self.subtitle_text.config(state="disabled")
        
        # Correction affichée en dessous
        if corrected:
            self.correction_label.config(text=f"Correction: {corrected}")
