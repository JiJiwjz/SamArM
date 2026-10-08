"""Resume a day's digest after partial SMTP delivery without resending to recipients."""
import hashlib
import json
import os
from pathlib import Path


class DeliveryState:
    def __init__(self, path='data/daily_delivery.json'):
        self.path = Path(path)

    @staticmethod
    def recipient_key(recipient):
        return hashlib.sha256(recipient.strip().lower().encode()).hexdigest()

    def load(self, date):
        if not self.path.exists():
            return None
        # Corrupted state must fail visibly rather than silently resend mail.
        with self.path.open(encoding='utf-8') as stream:
            state = json.load(stream)
        return state if state.get('date') == date else None

    def save(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temporary, self.path)
