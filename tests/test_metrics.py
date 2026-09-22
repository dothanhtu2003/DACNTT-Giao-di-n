import math

import numpy as np
import pytest

from metrics.metrics import payload_metrics, mse, psnr, ssim, ber


def test_payload_metrics():
    result = payload_metrics(8, 192, 8, 8)
    assert result['packet_bits'] == 96
    assert result['bpp'] == 1.5
    assert result['usage_percent'] == 50
    assert payload_metrics(0, 0, 1, 1)['usage_percent'] is None


@pytest.mark.parametrize('shape', [(8, 8), (8, 8, 3), (8, 8, 4), (3, 3)])
def test_image_metrics(shape):
    image = np.full(shape, 80, dtype=np.uint8)
    assert mse(image, image) == 0
    assert math.isinf(psnr(image, image))
    assert ssim(image, image) == pytest.approx(1)
    altered = image + 10
    assert mse(image, altered) == 100
    assert psnr(image, altered) == pytest.approx(10 * math.log10(650.25))
    assert ssim(image, altered) < 1


def test_ber():
    assert ber([0, 1, 1, 0], [0, 0, 1, 0]) == 0.25
    with pytest.raises(ValueError):
        ber([1], [])
    with pytest.raises(ValueError):
        ssim(np.zeros((2, 2), dtype=np.uint8), np.zeros((2, 2), dtype=np.uint8))
