import tkinter as tk
import threading
import sounddevice as sd
import whisper
import numpy as np
import language_tool_python
import datetime
import time
from difflib import SequenceMatcher
from phonemizer import phonemize

class WhisperTkApp(tk.Tk):
    def ask_log_filename(self):
        import tkinter.simpledialog
        default_name = datetime.datetime.now().strftime("transcript_%Y%m%d_%H%M%S.txt")
        name = tkinter.simpledialog.askstring("Nom du document", f"Nom du document de transcription :", initialvalue=default_name)
        return name if name else default_name
        
    def __init__(self):
        # Création du fichier de log
        self.log_filename = self.ask_log_filename()
        self.log_file = open(self.log_filename, "a", encoding="utf-8")
        super().__init__()
        self.title("Whisper Real-Time Subtitle App")
        self.geometry("800x600")
        self.configure(bg="#222")
        
        # Zone de texte
        self.subtitle_text = tk.Text(self, font=("Arial", 14), fg="white", bg="#222", 
                                   wrap="word", borderwidth=0, highlightthickness=0, height=15)
        self.subtitle_text.pack(pady=20, fill="both", expand=True)
        
        # Zone pour la correction
        self.correction_label = tk.Label(self, text="", font=("Arial", 12), fg="yellow", bg="#222", wraplength=700, justify="left")
        self.correction_label.pack(pady=10)
        
        # Bouton
        self.toggle_button = tk.Button(self, text="Démarrer", font=("Arial", 16), 
                                     bg="#007acc", fg="white", command=self.toggle_listening)
        self.toggle_button.pack(pady=10)
        
        # Bouton paramètres
        self.settings_button = tk.Button(self, text="Paramètres", font=("Arial", 12),
                                       bg="#555", fg="white", command=self.open_settings)
        self.settings_button.pack(pady=5)
        
        # Variables d'état
        self.listen_active = False
        self.running = False
        self.device_index = None
        
        # Buffer audio simple
        self.audio_buffer = np.array([], dtype=np.float32)
        self.buffer_lock = threading.Lock()
        
        # Paramètres par défaut
        self.show_percentages = True
        self.show_colors = True
        
        # Charger le modèle Whisper
        print("Chargement du modèle Whisper...")
        self.model = whisper.load_model("base")
        print("Modèle Whisper chargé")
        
        # Charger LanguageTool
        print("Chargement de LanguageTool...")
        self.lt_tool = language_tool_python.LanguageTool('en-US')
        print("LanguageTool chargé")

    def toggle_listening(self):
        if not self.listen_active:
            self.listen_active = True
            self.running = True
            self.toggle_button.config(text="Arrêter")
            
            # Démarrer l'audio stream
            self.stream = sd.InputStream(samplerate=16000, channels=1, dtype='float32', 
                                       callback=self.audio_callback, device=self.device_index)
            self.stream.start()
            
            # Démarrer le thread de transcription
            self.transcription_thread = threading.Thread(target=self.transcribe_loop, daemon=True)
            self.transcription_thread.start()
        else:
            self.listen_active = False
            self.running = False
            self.toggle_button.config(text="Démarrer")
            if hasattr(self, 'stream'):
                self.stream.stop()
                
    def open_settings(self):
        settings_win = tk.Toplevel(self)
        settings_win.title("Paramètres")
        settings_win.geometry("400x300")
        settings_win.configure(bg="#333")
        
        # Variables pour les paramètres
        percentage_var = tk.BooleanVar(value=self.show_percentages)
        color_var = tk.BooleanVar(value=self.show_colors)
        
        # Checkboxes
        tk.Label(settings_win, text="Paramètres d'affichage", font=("Arial", 14), fg="white", bg="#333").pack(pady=10)
        
        percentage_cb = tk.Checkbutton(settings_win, text="Afficher les pourcentages de prononciation", 
                                     variable=percentage_var, fg="white", bg="#333", selectcolor="#555")
        percentage_cb.pack(pady=5, anchor="w", padx=20)
        
        color_cb = tk.Checkbutton(settings_win, text="Colorer les erreurs de prononciation", 
                                variable=color_var, fg="white", bg="#333", selectcolor="#555")
        color_cb.pack(pady=5, anchor="w", padx=20)
        
        def save_settings():
            self.show_percentages = percentage_var.get()
            self.show_colors = color_var.get()
            settings_win.destroy()
        
        save_btn = tk.Button(settings_win, text="Sauvegarder", command=save_settings,
                           bg="#007acc", fg="white", font=("Arial", 12))
        save_btn.pack(pady=20)

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        
        with self.buffer_lock:
            # Convertir l'audio en mono et ajouter au buffer
            audio_data = indata[:, 0]
            self.audio_buffer = np.concatenate([self.audio_buffer, audio_data])

    def transcribe_loop(self):
        print("Thread de transcription démarré")
        
        while self.running:
            try:
                # Attendre un peu d'audio
                time.sleep(3)
                
                # Copier le buffer
                with self.buffer_lock:
                    if len(self.audio_buffer) > 16000:  # Au moins 1 seconde d'audio
                        audio_to_process = self.audio_buffer.copy()
                        self.audio_buffer = np.array([], dtype=np.float32)
                    else:
                        continue
                
                # Transcription
                result = self.model.transcribe(audio_to_process, language="en", fp16=False)
                text = result.get("text", "").strip()
                
                if text:
                    print(f"Transcrit: '{text}'")
                    
                    # Analyse grammaire
                    try:
                        matches = self.lt_tool.check(text)
                        grammar_errors = [(m.offset, m.errorLength, m.message) for m in matches]
                        corrected = self.lt_tool.correct(text)
                    except:
                        grammar_errors = []
                        corrected = text
                    
                    # Analyse prononciation
                    pronunciation_errors = []
                    if self.show_colors or self.show_percentages:
                        words = text.split()[:10]
                        for w in words:
                            try:
                                ph = phonemize(w, language='en-us', backend='espeak')
                                if not ph.strip():
                                    pronunciation_errors.append(w)
                            except:
                                pronunciation_errors.append(w)
                    
                    # Afficher dans l'interface
                    self.after(0, lambda: self.update_subtitle(text, grammar_errors, pronunciation_errors, corrected))
                    
            except Exception as e:
                print(f"Erreur transcription: {e}")
                time.sleep(1)
        
        print("Thread de transcription terminé")

    def update_subtitle(self, text, grammar_errors=None, pronunciation_errors=None, corrected=None):
        try:
            if not text.strip():
                return
            
            # Log vers fichier
            try:
                time_str = datetime.datetime.now().strftime("%H:%M:%S")
                self.log_file.write(f"[{time_str}] {text}\n")
                self.log_file.flush()
            except:
                pass
            
            # Afficher dans l'interface
            self.subtitle_text.config(state="normal")
            
            # Ajouter horodatage
            time_str = datetime.datetime.now().strftime("%H:%M:%S")
            self.subtitle_text.insert(tk.END, f"\n[{time_str}] ")
            
            # Ajouter le texte
            words = text.split()
            for i, word in enumerate(words):
                start_idx = self.subtitle_text.index(tk.INSERT)
                self.subtitle_text.insert(tk.END, word + " ")
                end_idx = self.subtitle_text.index(tk.INSERT)
                
                # Afficher pourcentages
                if self.show_percentages:
                    is_error = pronunciation_errors and word in pronunciation_errors
                    percent = 0 if is_error else 100
                    self.subtitle_text.insert(tk.END, f"({percent}%) ")
                
                # Appliquer couleurs
                if self.show_colors and pronunciation_errors and word in pronunciation_errors:
                    self.subtitle_text.tag_add("bad_pron", start_idx, f"{end_idx}-1c")
                    self.subtitle_text.tag_config("bad_pron", foreground="red")
            
            # Auto-scroll
            self.subtitle_text.see(tk.END)
            self.subtitle_text.config(state="disabled")
            
            # Afficher correction
            if corrected and corrected != text:
                self.correction_label.config(text=f"Correction: {corrected}")
            else:
                self.correction_label.config(text="")
                
        except Exception as e:
            print(f"Erreur update_subtitle: {e}")

if __name__ == "__main__":
    app = WhisperTkApp()
    app.mainloop()