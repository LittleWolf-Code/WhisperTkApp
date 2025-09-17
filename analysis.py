import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import language_tool_python
from phonemizer import phonemize

class GrammarAnalyzer:
    def __init__(self):
        self.lt_tool = language_tool_python.LanguageTool('en-US')
    def check(self, text):
        matches = self.lt_tool.check(text)
        return [(m.offset, m.errorLength, m.message) for m in matches]
    def correct(self, text):
        return self.lt_tool.correct(text)

class PronunciationAnalyzer:
    def check(self, text):
        words = text.split()
        errors = []
        for w in words:
            try:
                ph = phonemize(w, language='en-us', backend='espeak')
                if not ph.strip():
                    errors.append(w)
            except Exception:
                errors.append(w)
        return errors
