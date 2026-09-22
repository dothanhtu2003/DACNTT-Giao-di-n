import json

import pytest

from storage.history_store import HistoryStore


@pytest.mark.parametrize('content', ['', '{broken', '{}', '[3]'])
def test_recovery(content, tmp_path):
    path = tmp_path / 'history.json'
    path.write_text(content)
    store = HistoryStore(path)
    assert store.get_all() == []
    assert json.loads(path.read_text()) == []


def test_privacy_and_crud(tmp_path):
    path = tmp_path / 'history.json'
    store = HistoryStore(path)
    record_id = store.add_record({'method': 'PVD', 'status': 'success', 'psnr': float('inf'),
                                  'message': 'SECRET', 'extracted_message': 'SECRET',
                                  'raw_payload': [1, 2, 3]})
    assert len(store.get_all()) == 1
    assert 'SECRET' not in path.read_text() and 'raw_payload' not in path.read_text()
    assert store.get_all()[0]['psnr'] == 'Infinity'
    store.delete_record(record_id)
    assert store.get_all() == []
    store.add_record({'method': 'DWT'})
    store.clear()
    assert store.get_all() == []
