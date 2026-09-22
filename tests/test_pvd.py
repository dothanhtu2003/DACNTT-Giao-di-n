import numpy as np
import pytest

from core import pvd
from core.engine_utils import CapacityError
from core.payload import build_packet, packet_to_bits, decode_message


@pytest.mark.parametrize('channels', [None, 3, 4])
@pytest.mark.parametrize('width', [64, 65])
def test_roundtrip(channels, width):
    shape = (64, width) if channels is None else (64, width, channels)
    image = np.random.default_rng(17).integers(0, 256, shape, dtype=np.uint8)
    original = image.copy()
    bits = packet_to_bits(build_packet('Việt Nam 🔐'))
    output = pvd.embed(image, bits)
    assert decode_message(pvd.extract(output)) == 'Việt Nam 🔐'
    assert np.array_equal(image, original)
    assert output.shape == image.shape and output.dtype == np.uint8
    if channels:
        assert np.array_equal(output[:, :, :2], image[:, :, :2])
        if channels == 4:
            assert np.array_equal(output[:, :, 3], image[:, :, 3])
    if width % 2:
        assert np.array_equal(output[:, -1], image[:, -1])


def test_capacity_boundary():
    image = np.zeros((8, 8), dtype=np.uint8)
    capacity = pvd.calculate_capacity(image)
    assert capacity == 96
    bits = np.random.default_rng(1).integers(0, 2, capacity, dtype=np.uint8)
    output = pvd.embed(image, bits)
    assert np.array_equal(pvd.extract_n_bits(output, capacity), bits)
    assert pvd.calculate_capacity(output) == capacity
    with pytest.raises(CapacityError):
        pvd.embed(image, np.zeros(capacity + 1, dtype=np.uint8))


def test_all_pixel_pairs():
    # Exercise all 65,536 source pairs at both extremes of each interval.
    pairs = np.array([(a, b) for a in range(256) for b in range(256)], dtype=np.uint8)
    capacity = pvd.calculate_capacity(pairs)
    for bit in (0, 1):
        bits = np.full(capacity, bit, dtype=np.uint8)
        output = pvd.embed(pairs, bits)
        assert np.array_equal(pvd.extract_n_bits(output, capacity), bits)
        assert pvd.calculate_capacity(output) == capacity
