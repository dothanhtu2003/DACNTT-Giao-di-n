"""Read-only observations of current seed masks and PVD raster origin."""

import numpy as np
import pytest

from core import pvd
from experiments.attacks import apply_attack


@pytest.mark.parametrize('channels', [1, 3, 4])
def test_salt_pepper_same_seed_same_positions_independent_of_content(channels):
    shape = (64, 80) if channels == 1 else (64, 80, channels)
    first = np.full(shape, 72, dtype=np.uint8)
    second = np.full(shape, 169, dtype=np.uint8)
    a = apply_attack(first, 'salt_pepper', {'amount': .1}, seed=20260919)
    b = apply_attack(second, 'salt_pepper', {'amount': .1}, seed=20260919)
    color_a, color_b = (a, b) if channels == 1 else (a[:, :, :3], b[:, :, :3])
    pepper_a, salt_a = color_a == 0, color_a == 255
    pepper_b, salt_b = color_b == 0, color_b == 255
    assert np.array_equal(pepper_a, pepper_b) and np.array_equal(salt_a, salt_b)
    uniform = np.random.default_rng(20260919).random((64, 80))
    expected_pepper = uniform < .05
    expected_salt = (uniform >= .05) & (uniform < .1)
    if channels != 1:
        expected_pepper = np.repeat(expected_pepper[:, :, None], 3, axis=2)
        expected_salt = np.repeat(expected_salt[:, :, None], 3, axis=2)
    assert np.array_equal(pepper_a, expected_pepper) and np.array_equal(salt_a, expected_salt)
    different = apply_attack(first, 'salt_pepper', {'amount': .1}, seed=20260920)
    assert not np.array_equal(a, different)
    if channels == 4:
        assert np.array_equal(a[:, :, 3], first[:, :, 3])


@pytest.mark.parametrize('channels', [1, 3, 4])
def test_pvd_starts_at_top_left_horizontal_pair(channels):
    shape = (4, 7) if channels == 1 else (4, 7, channels)
    image = np.full(shape, 128, dtype=np.uint8)
    output = pvd.embed(image, np.array([1, 0, 1, 0, 1, 0], dtype=np.uint8))
    plane = output if channels == 1 else output[:, :, 2]
    assert abs(int(plane[0, 0]) - int(plane[0, 1])) == 5
    assert abs(int(plane[0, 2]) - int(plane[0, 3])) == 2
    assert np.all(plane[0, 4:] == 128) and np.all(plane[1:] == 128)
    assert np.all(image == 128)
    if channels > 1:
        assert np.array_equal(output[:, :, :2], image[:, :, :2])
        if channels == 4:
            assert np.array_equal(output[:, :, 3], image[:, :, 3])
