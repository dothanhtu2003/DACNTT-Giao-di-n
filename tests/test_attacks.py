import numpy as np
import pytest

from experiments.attacks import apply_attack
from experiments.experiment_config import ATTACK_LEVELS


@pytest.mark.parametrize('channels', [None, 3, 4])
@pytest.mark.parametrize('attack', ATTACK_LEVELS, ids=lambda item: item['name'] + str(item['parameters']))
def test_attack(attack, channels):
    shape = (64, 64) if channels is None else (64, 64, channels)
    image = np.random.default_rng(3).integers(20, 235, shape, dtype=np.uint8)
    original = image.copy()
    result = apply_attack(image, attack['name'], attack['parameters'], seed=42)
    assert np.array_equal(image, original)
    assert result.dtype == np.uint8 and result.ndim == image.ndim
    assert not np.shares_memory(result, image)
    assert np.array_equal(result, apply_attack(image, attack['name'], attack['parameters'], seed=42))
    if attack['name'] not in ('crop', 'resize'):
        assert result.shape == image.shape
        if channels == 4:
            assert np.array_equal(result[:, :, 3], image[:, :, 3])
    else:
        assert result.shape[:2] != image.shape[:2]
    if attack['name'] != 'none':
        assert result.shape != image.shape or not np.array_equal(result, image)


@pytest.mark.parametrize('name,parameters', [('jpeg', {'quality': 101}), ('blur', {'kernel_size': 2}),
                                           ('resize', {'scale': 0}), ('crop', {'fraction': 0}),
                                           ('gaussian_noise', {'sigma': -1}), ('salt_pepper', {'amount': 2}),
                                           ('contrast', {'alpha': -1})])
def test_invalid(name, parameters):
    with pytest.raises(ValueError):
        apply_attack(np.zeros((16, 16), dtype=np.uint8), name, parameters, seed=1)
