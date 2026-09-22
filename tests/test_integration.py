import numpy as np
import pytest
from PIL import Image

from core import pvd, dwt
from core.payload import bytes_to_bits, build_packet, packet_to_bits
from services.stego_service import StegoService
from storage.history_store import HistoryStore


def test_dwt_clipping_detected(tmp_path):
    path = tmp_path / 'white.png'
    Image.fromarray(np.full((128, 128), 255, dtype=np.uint8)).save(path)
    service = StegoService(HistoryStore(tmp_path / 'history.json'))
    result = service.embed(path, 'A', 'DWT')
    assert not result['success']
    assert result['extract_status'] == 'extraction_failed'
    assert result['ber'] is None  # Damaged LENGTH: packet alignment not established.
    with pytest.raises(ValueError):
        service.save(result, tmp_path / 'bad.png')


@pytest.mark.parametrize('method', ['PVD', 'DWT'])
def test_corrupt_length_and_utf8(tmp_path, method):
    engine = {'PVD': pvd, 'DWT': dwt}[method]
    image = np.full((128, 128), 128, dtype=np.uint8)
    service = StegoService(HistoryStore(tmp_path / 'history.json'))
    for packet, expected in [(b'\xff\xff\xff\xff', 'LengthError'),
                             (b'\x00\x00\x00\x01\xff', 'UTF8Error')]:
        output = engine.embed(image, bytes_to_bits(packet))
        path = tmp_path / f'{method}_{expected}.png'
        Image.fromarray(output).save(path)
        result = service.extract(path, method)
        assert not result['success'] and result['error_type'] == expected
        assert 'message' not in result


def test_packet_cannot_authenticate_empty_cover(tmp_path):
    # The locked packet has no magic/checksum: a zero header is a valid empty message.
    path = tmp_path / 'plain.png'
    Image.fromarray(np.full((128, 128), 128, dtype=np.uint8)).save(path)
    service = StegoService(HistoryStore(tmp_path / 'history.json'))
    result = service.extract(path, 'PVD')
    assert result['success'] and result['message'] == ''


def test_output_error(tmp_path):
    path = tmp_path / 'cover.png'
    Image.fromarray(np.full((128, 128), 128, dtype=np.uint8)).save(path)
    service = StegoService(HistoryStore(tmp_path / 'history.json'))
    result = service.embed(path, 'Hello', 'PVD')
    with pytest.raises(OSError):
        service.save(result, tmp_path / 'nonexistent' / 'image.png')


@pytest.mark.parametrize('engine', [pvd, dwt])
def test_near_capacity_packet(engine):
    image = np.full((128, 128), 128, dtype=np.uint8)
    capacity = engine.calculate_capacity(image)
    message = 'A' * ((capacity - 32) // 8)
    bits = packet_to_bits(build_packet(message))
    assert np.array_equal(engine.extract(engine.embed(image, bits)), bits)
