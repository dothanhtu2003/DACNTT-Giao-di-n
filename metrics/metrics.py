"""One bpp definition: packet bits (including LENGTH) per image pixel.

For RGBA, perceptual metrics use RGB; unchanged alpha is excluded.
"""

import math

import numpy as np
from skimage.metrics import structural_similarity

from core.engine_utils import validate_image
from core.payload import checked_bits


def payload_metrics(payload_bytes, capacity_bits, width, height):
    if payload_bytes < 0 or capacity_bits < 0 or width <= 0 or height <= 0:
        raise ValueError('Thông số metrics không hợp lệ.')
    packet_bits = 32 + 8 * payload_bytes
    return {'capacity_bits': capacity_bits, 'payload_bytes': payload_bytes,
            'packet_bits': packet_bits,
            'usage_percent': packet_bits / capacity_bits * 100 if capacity_bits else None,
            'bpp': packet_bits / (width * height)}


def _pair(original, modified):
    original, modified = validate_image(original), validate_image(modified)
    if original.shape != modified.shape:
        raise ValueError('Hai ảnh phải cùng kích thước và số kênh.')
    if original.ndim == 3 and original.shape[2] == 4:
        original, modified = original[:, :, :3], modified[:, :, :3]
    return original, modified


def mse(original, modified):
    original, modified = _pair(original, modified)
    return float(np.mean((original.astype(float) - modified.astype(float)) ** 2))


def psnr(original, modified):
    error = mse(original, modified)
    return math.inf if error == 0 else 10 * math.log10(255 ** 2 / error)


def ssim(original, modified):
    original, modified = _pair(original, modified)
    minimum = min(original.shape[:2])
    if minimum < 3:
        raise ValueError('SSIM cần mỗi chiều ít nhất 3 pixel.')
    window = min(7, minimum if minimum % 2 else minimum - 1)
    return float(structural_similarity(original, modified, data_range=255,
                                      channel_axis=None if original.ndim == 2 else -1,
                                      win_size=window))


def ber(expected, extracted):
    expected, extracted = checked_bits(expected), checked_bits(extracted)
    if len(expected) != len(extracted) or not len(expected):
        raise ValueError('BER cần hai dãy bit cùng độ dài, khác rỗng và đã đồng bộ.')
    return float(np.count_nonzero(expected != extracted) / len(expected))
