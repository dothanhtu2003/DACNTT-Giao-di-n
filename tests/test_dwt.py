import numpy as np
import pytest
from PIL import Image

from core import dwt
from core.engine_utils import CapacityError
from core.payload import build_packet, packet_to_bits, decode_message


@pytest.mark.parametrize('channels', [None, 3, 4])
@pytest.mark.parametrize('shape', [(128, 128), (129, 131)])
def test_png_roundtrip(channels, shape, tmp_path):
    shape = shape if channels is None else (*shape, channels)
    image = np.random.default_rng(24).integers(24, 232, shape, dtype=np.uint8)
    original = image.copy()
    bits = packet_to_bits(build_packet('Tiếng Việt 🔐'))
    output = dwt.embed(image, bits)
    path = tmp_path / 'stego.png'
    Image.fromarray(output).save(path)
    loaded = np.array(Image.open(path))
    assert decode_message(dwt.extract(loaded)) == 'Tiếng Việt 🔐'
    assert np.array_equal(image, original)
    assert output.shape == image.shape and output.dtype == np.uint8
    if channels == 4:
        assert np.array_equal(output[:, :, 3], image[:, :, 3])


def test_capacity_boundary():
    image = np.full((80, 80), 128, dtype=np.uint8)
    capacity = dwt.calculate_capacity(image)
    assert capacity == 320
    bits = np.random.default_rng(3).integers(0, 2, capacity, dtype=np.uint8)
    assert np.array_equal(dwt.extract_n_bits(dwt.embed(image, bits), capacity), bits)
    with pytest.raises(CapacityError):
        dwt.embed(image, np.zeros(capacity + 1, dtype=np.uint8))


def test_qim_and_repetition():
    assert dwt.DELTA == 18 and dwt.REPEAT == 5
    coefficients = np.array([-19.1, -9.4, 0, 9.1, 18.7])
    for bit in (0, 1):
        quantized = dwt.quantize(coefficients, np.full(5, bit))
        assert np.all(dwt.coefficient_bits(quantized) == bit)
    assert dwt.majority_vote([1, 1, 1, 0, 0, 0, 0, 0, 1, 1]).tolist() == [1, 0]
    image = np.full((80, 80), 128, dtype=np.uint8)
    output = dwt.embed(image, [1, 0])
    decisions = dwt.coefficient_bits(dwt.decompose_for_visualization(output)['HH'].ravel()[:10])
    assert decisions.tolist() == [1] * 5 + [0] * 5


def test_subbands():
    image = np.full((80, 80), 128, dtype=np.uint8)
    bands = dwt.decompose_for_visualization(image)
    assert set(bands) == {'LL', 'LH', 'HL', 'HH'}
    assert all(band.shape == (40, 40) for band in bands.values())
