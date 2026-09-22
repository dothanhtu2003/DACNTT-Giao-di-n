import numpy as np
import pytest
from PIL import Image

from services.stego_service import StegoService
from storage.history_store import HistoryStore


@pytest.fixture
def service(tmp_path):
    return StegoService(HistoryStore(tmp_path / 'history.json'))


@pytest.fixture
def cover(tmp_path):
    path = tmp_path / 'cover.png'
    Image.fromarray(np.full((128, 128, 3), 128, dtype=np.uint8)).save(path)
    return path


@pytest.mark.parametrize('method', ['PVD', 'DWT'])
def test_roundtrip(service, cover, method, tmp_path):
    message = 'Bí mật 🔐'
    result = service.embed(cover, message, method)
    assert result['success'], result['error']
    assert result['ber'] == 0
    path = tmp_path / f'{method}.png'
    service.save(result, path)
    extracted = service.extract(path, method)
    assert extracted['success'] and extracted['message'] == message
    assert message not in service.history.path.read_text(encoding='utf-8')
    assert 'message' not in service.history.path.read_text(encoding='utf-8')


@pytest.mark.parametrize('message,status', [('Hi', 'success'), ('x' * 150, 'partial'), ('x' * 4000, 'failed')])
def test_compare(service, cover, message, status):
    assert service.compare(cover, message)['status'] == status


def test_errors(service, cover, tmp_path):
    assert not service.embed(cover, 'x', 'unknown')['success']
    assert not service.embed(tmp_path / 'missing.png', 'x', 'PVD')['success']
    with pytest.raises(ValueError):
        service.save(service.embed(cover, 'ok', 'PVD'), tmp_path / 'bad.jpg')
    tiny = tmp_path / 'tiny.png'
    Image.fromarray(np.zeros((2, 2), dtype=np.uint8)).save(tiny)
    assert not service.extract(tiny, 'PVD')['success']
    corrupt = tmp_path / 'bad.png'
    corrupt.write_text('not an image')
    assert not service.embed(corrupt, 'ok', 'PVD')['success']
