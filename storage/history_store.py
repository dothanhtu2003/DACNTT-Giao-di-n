"""Atomic local JSON storage with an explicit metadata allowlist."""

import json
import math
import os
from pathlib import Path
import tempfile
from uuid import uuid4

DEFAULT_PATH = Path(__file__).resolve().parents[1] / 'data' / 'history.json'
FIELDS = {
    'id', 'timestamp', 'operation', 'method', 'input_filename', 'output_path',
    'width', 'height', 'payload_bytes', 'packet_bits', 'capacity_bits',
    'usage_percent', 'bpp', 'psnr', 'ssim', 'ber', 'status',
    'attack', 'attack_parameters', 'seed', 'error', 'error_type',
}


def _clean(record):
    result = {}
    for key in FIELDS:
        value = record.get(key)
        if value is None or isinstance(value, (str, int, float, bool)):
            if isinstance(value, float) and not math.isfinite(value):
                value = 'Infinity' if value > 0 else None
            result[key] = value
    return result


class HistoryStore:
    def __init__(self, path=DEFAULT_PATH):
        self.path = Path(path)

    def _write(self, records):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                                             suffix='.tmp', delete=False) as handle:
                temp_path = Path(handle.name)
                json.dump(records, handle, ensure_ascii=False, indent=2, allow_nan=False)
            os.replace(temp_path, self.path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    def get_all(self):
        try:
            records = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
                raise ValueError('Invalid history structure')
            clean = [_clean(item) for item in records]
            if records != clean:
                self._write(clean)
            return clean
        except (FileNotFoundError, json.JSONDecodeError, UnicodeError, ValueError):
            self._write([])
            return []

    def add_record(self, record):
        records = self.get_all()
        record = _clean(record)
        record['id'] = uuid4().hex
        records.append(record)
        self._write(records)
        return record['id']

    def delete_record(self, record_id):
        self._write([item for item in self.get_all() if item.get('id') != record_id])

    def clear(self):
        self._write([])
