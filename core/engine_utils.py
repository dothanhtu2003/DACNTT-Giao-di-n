"""Validation shared by the two independent engines."""

import numpy as np


class CapacityError(ValueError):
    """Ảnh không đủ dung lượng cho toàn bộ packet."""


def validate_image(image):
    image = np.asarray(image)
    if image.dtype != np.uint8 or image.ndim not in (2, 3):
        raise ValueError('Ảnh phải là ma trận uint8 grayscale/RGB/RGBA.')
    if image.ndim == 3 and image.shape[2] not in (3, 4):
        raise ValueError('Ảnh màu phải có 3 hoặc 4 kênh.')
    if not image.shape[0] or not image.shape[1]:
        raise ValueError('Ảnh rỗng.')
    return image
