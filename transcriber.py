import threading
import time

class Transcriber:
    def __init__(self, config):
        self.config = config
        self.callback = None
        self.is_running = False
        self.is_paused = True
        self.thread = None
        
    def start(self, callback):
        """Démarre le transcripteur avec une fonction de callback"""
        self.callback = callback
        self.is_running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        
    def _run(self):
        """Boucle principale du transcripteur (simulation)"""
        counter = 0
        while self.is_running:
            if not self.is_paused and self.callback:
                # Simulation de transcription avec du texte de test
                counter += 1
                test_text = f"Ceci est un test de transcription numero {counter}"
                self.callback(test_text)
            time.sleep(self.config.transcription_delay)
            
    def pause(self):
        """Met en pause la transcription"""
        self.is_paused = True
        
    def resume(self):
        """Reprend la transcription"""
        self.is_paused = False
        
    def stop(self):
        """Arrête complètement le transcripteur"""
        self.is_running = False
        if self.thread:
            self.thread.join()