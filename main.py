import tkinter as tk
import threading
import sounddevice as sd
import whisper
import numpy as np
import language_tool_python
import datetime
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
        self.geometry("800x400")
        self.configure(bg="#222")
        self.subtitle_text = tk.Text(self, font=("Arial", 18), fg="white", bg="#222", height=2, wrap="word", borderwidth=0, highlightthickness=0)
        self.subtitle_text.pack(pady=20, fill="x")
        self.subtitle_text.tag_configure("bad_pron", foreground="red")
        self.correction_label = tk.Label(self, text="Correction ici...", font=("Arial", 14), fg="lightgreen", bg="#222")
        self.correction_label.pack(pady=10)

        # Bouton Démarrer/Arrêter (juste sous les labels)
        self.listen_active = False
        self.toggle_button = tk.Button(self, text="Démarrer", command=self.toggle_listen)
        self.toggle_button.pack(pady=10)

        # Bouton paramètres
        self.settings_button = tk.Button(self, text="Paramètres", command=self.open_settings)
        self.settings_button.place(relx=0.98, rely=0.02, anchor="ne")

        # Liste des micros disponibles
        self.mic_devices = sd.query_devices()
        self.input_devices = [d for d in self.mic_devices if d['max_input_channels'] > 0]
        self.device_names = [d['name'] for d in self.input_devices]
        self.selected_device = tk.StringVar(value=self.device_names[0] if self.device_names else "")
        # (La sélection du micro est déplacée dans la fenêtre paramètres)

        self.device_index = self.input_devices[0]['index'] if self.input_devices else None

        # LanguageTool pour grammaire
        self.lt_tool = language_tool_python.LanguageTool('en-US')
        # Phonemizer pour prononciation
        self.phonemize = phonemize
        self.model = whisper.load_model("base")
        self.running = True
        self.audio_buffer = np.zeros(16000 * 5, dtype=np.float32)  # 5 secondes de buffer
        self.buffer_lock = threading.Lock()
        self.stream = sd.InputStream(samplerate=16000, channels=1, dtype='float32', callback=self.audio_callback, device=self.device_index)
        self.stream.start()
        threading.Thread(target=self.transcribe_loop, daemon=True).start()
        self.transcription_delay = 0.5  # Valeur par défaut, modifiable dans les paramètres

    def toggle_listen(self):
        if not self.listen_active:
            self.listen_active = True
            self.toggle_button.config(text="Arrêter")
            if not hasattr(self, 'stream') or not self.stream.active:
                self.stream = sd.InputStream(samplerate=16000, channels=1, dtype='float32', callback=self.audio_callback, device=self.device_index)
                self.stream.start()
            self.running = True
            if not hasattr(self, 'transcribe_thread') or not self.transcribe_thread.is_alive():
                self.transcribe_thread = threading.Thread(target=self.transcribe_loop, daemon=True)
                self.transcribe_thread.start()
        else:
            self.listen_active = False
            self.toggle_button.config(text="Démarrer")
            self.running = False
            if hasattr(self, 'stream') and self.stream.active:
                self.stream.stop()
    def open_settings(self):
        settings_win = tk.Toplevel(self)
        settings_win.title("Paramètres")
        settings_win.geometry("400x250")
        tk.Label(settings_win, text="Choisir le micro :", font=("Arial", 12)).pack(pady=10)
        device_var = tk.StringVar(value=self.selected_device.get())
        device_menu = tk.OptionMenu(settings_win, device_var, *self.device_names)
        device_menu.pack(pady=10)
        # Ajout du paramètre délai transcription
        tk.Label(settings_win, text="Délai transcription (secondes) :", font=("Arial", 12)).pack(pady=10)
        delay_var = tk.DoubleVar(value=self.transcription_delay)
        delay_entry = tk.Entry(settings_win, textvariable=delay_var)
        delay_entry.pack(pady=5)
        def apply_settings():
            self.selected_device.set(device_var.get())
            self.change_device(device_var.get())
            try:
                val = float(delay_var.get())
                if val > 0:
                    self.transcription_delay = val
            except Exception:
                pass
            settings_win.destroy()
        tk.Button(settings_win, text="Valider", command=apply_settings).pack(pady=20)

    def change_device(self, device_name):
        # Arrête l'ancien stream
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
        # Trouve l'index du nouveau micro
        for d in self.input_devices:
            if d['name'] == device_name:
                self.device_index = d['index']
                break
        # Redémarre le stream avec le nouveau micro
        self.stream = sd.InputStream(samplerate=16000, channels=1, dtype='float32', callback=self.audio_callback, device=self.device_index)
        self.stream.start()

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        with self.buffer_lock:
            self.audio_buffer = np.roll(self.audio_buffer, -frames)
            self.audio_buffer[-frames:] = indata[:, 0]

    def transcribe_loop(self):
        import time
        while self.running:
            with self.buffer_lock:
                audio = self.audio_buffer.copy()
            audio_float32 = audio.astype(np.float32)
            result = self.model.transcribe(audio_float32, language="en", fp16=False)
            text = result.get("text", "")
            # Analyse grammaire
            matches = self.lt_tool.check(text)
            grammar_errors = [(m.offset, m.errorLength, m.message) for m in matches]
            # Correction grammaire
            corrected = self.lt_tool.correct(text)
            # Analyse prononciation (simple: compare phonèmes attendus vs texte)
            # Pour la démo, on considère tout mot non anglais comme erreur de prononciation
            # (Améliorable avec reconnaissance phonétique)
            words = text.split()
            pronunciation_errors = []
            for w in words:
                try:
                    ph = self.phonemize(w, language='en-us', backend='espeak')
                    if not ph.strip():
                        pronunciation_errors.append(w)
                except Exception:
                    pronunciation_errors.append(w)
            self.after(0, lambda: self.update_subtitle(text, grammar_errors, pronunciation_errors, corrected))
            time.sleep(self.transcription_delay)

    def update_subtitle(self, text, grammar_errors=None, pronunciation_errors=None, corrected=None):
        # Ajout de la transcription au log avec horodatage
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_file.write(f"[{now}] {text}\n")
        self.log_file.flush()
        # Coloration des erreurs de grammaire (rouge) et prononciation (orange)
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
        # Correction affichée en dessous
        self.correction_label.config(text=f"Correction: {corrected}")

if __name__ == "__main__":
    app = WhisperTkApp()
    app.mainloop()
