import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import sounddevice as sd
import tkinter as tk
import datetime

class AppConfig:
    def __init__(self):
        self.mic_devices = sd.query_devices()
        self.input_devices = [d for d in self.mic_devices if d['max_input_channels'] > 0]
        self.device_names = [d['name'] for d in self.input_devices]
        self.selected_device = self.device_names[0] if self.device_names else ""
        self.device_index = self.input_devices[0]['index'] if self.input_devices else None
        self.transcription_delay = 0.5
        self.log_filename = self.ask_log_filename()
        self.log_file = open(self.log_filename, "a", encoding="utf-8")
    def ask_log_filename(self):
        import tkinter.simpledialog
        default_name = datetime.datetime.now().strftime("transcript_%Y%m%d_%H%M%S.txt")
        name = tkinter.simpledialog.askstring("Nom du document", f"Nom du document de transcription :", initialvalue=default_name)
        return name if name else default_name
    def open_settings(self, parent):
        settings_win = tk.Toplevel(parent)
        settings_win.title("Paramètres")
        settings_win.geometry("400x250")
        tk.Label(settings_win, text="Choisir le micro :", font=("Arial", 12)).pack(pady=10)
        device_var = tk.StringVar(value=self.selected_device)
        device_menu = tk.OptionMenu(settings_win, device_var, *self.device_names)
        device_menu.pack(pady=10)
        tk.Label(settings_win, text="Délai transcription (secondes) :", font=("Arial", 12)).pack(pady=10)
        delay_var = tk.DoubleVar(value=self.transcription_delay)
        delay_entry = tk.Entry(settings_win, textvariable=delay_var)
        delay_entry.pack(pady=5)
        def apply_settings():
            self.selected_device = device_var.get()
            for d in self.input_devices:
                if d['name'] == self.selected_device:
                    self.device_index = d['index']
                    break
            try:
                val = float(delay_var.get())
                if val > 0:
                    self.transcription_delay = val
            except Exception:
                pass
            settings_win.destroy()
        tk.Button(settings_win, text="Valider", command=apply_settings).pack(pady=20)
