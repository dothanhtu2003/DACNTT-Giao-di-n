"""OpenCV attacks on uint8 grayscale/RGB/RGBA; never mutate the input.

RGB data is explicitly converted to/from BGR at OpenCV JPEG boundaries.
Photometric operations leave alpha unchanged. Geometry operations transform it.
"""

import cv2
import numpy as np

from core.engine_utils import validate_image


def _color(image):
    image = validate_image(image)
    return image[:, :, :3] if image.ndim == 3 and image.shape[2] == 4 else image


def _restore(original, color):
    if original.ndim == 3 and original.shape[2] == 4:
        return np.dstack((color, original[:, :, 3]))
    return color.copy()


def _uint8(values):
    return np.clip(np.rint(values), 0, 255).astype(np.uint8)


def jpeg_compression(image, quality=90):
    if not isinstance(quality, int) or not 1 <= quality <= 100:
        raise ValueError('JPEG quality phải là số nguyên 1–100.')
    color = _color(image)
    bgr = color if color.ndim == 2 else cv2.cvtColor(color, cv2.COLOR_RGB2BGR)
    ok, encoded = cv2.imencode('.jpg', bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError('OpenCV không encode được JPEG.')
    restored = cv2.imdecode(encoded, cv2.IMREAD_GRAYSCALE if color.ndim == 2 else cv2.IMREAD_COLOR)
    if restored is None:
        raise ValueError('OpenCV không decode được JPEG.')
    if color.ndim == 3:
        restored = cv2.cvtColor(restored, cv2.COLOR_BGR2RGB)
    return _restore(image, restored)


def gaussian_noise(image, sigma=1.0, *, rng=None):
    if not np.isfinite(sigma) or sigma < 0:
        raise ValueError('Sigma phải không âm và hữu hạn.')
    rng = np.random.default_rng() if rng is None else rng
    color = _color(image)
    return _restore(image, _uint8(color.astype(float) + rng.normal(0, sigma, color.shape)))


def salt_pepper_noise(image, amount=0.01, *, rng=None):
    if not 0 <= amount <= 1:
        raise ValueError('Noise amount phải thuộc [0,1].')
    rng = np.random.default_rng() if rng is None else rng
    color = _color(image).copy()
    mask = rng.random(color.shape[:2])
    color[mask < amount / 2] = 0
    color[(mask >= amount / 2) & (mask < amount)] = 255
    return _restore(image, color)


def gaussian_blur(image, kernel_size=3):
    if not isinstance(kernel_size, int) or kernel_size < 1 or kernel_size % 2 == 0:
        raise ValueError('Blur kernel phải là số nguyên lẻ dương.')
    return _restore(image, cv2.GaussianBlur(_color(image), (kernel_size, kernel_size), 0,
                                          borderType=cv2.BORDER_REFLECT_101))


def brightness(image, delta=10):
    if not np.isfinite(delta):
        raise ValueError('Brightness delta phải hữu hạn.')
    return _restore(image, _uint8(_color(image).astype(float) + delta))


def contrast(image, alpha=1.1):
    if not np.isfinite(alpha) or alpha < 0:
        raise ValueError('Contrast alpha phải hữu hạn và không âm.')
    return _restore(image, _uint8((_color(image).astype(float) - 127.5) * alpha + 127.5))


def resize(image, scale=0.75):
    image = validate_image(image)
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError('Resize scale phải dương và hữu hạn.')
    width, height = max(1, round(image.shape[1] * scale)), max(1, round(image.shape[0] * scale))
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)


def crop(image, fraction=0.9):
    image = validate_image(image)
    if not 0 < fraction <= 1:
        raise ValueError('Crop fraction phải thuộc (0,1].')
    height, width = max(1, round(image.shape[0] * fraction)), max(1, round(image.shape[1] * fraction))
    top, left = (image.shape[0] - height) // 2, (image.shape[1] - width) // 2
    return image[top:top + height, left:left + width].copy()


ATTACKS = {'jpeg': jpeg_compression, 'gaussian_noise': gaussian_noise,
           'salt_pepper': salt_pepper_noise, 'blur': gaussian_blur, 'brightness': brightness,
           'contrast': contrast, 'resize': resize, 'crop': crop}


def apply_attack(image, name, parameters, *, seed):
    validate_image(image)
    parameters = dict(parameters)
    if name == 'none':
        if parameters:
            raise ValueError('Baseline none không nhận parameter.')
        return image.copy()
    if name not in ATTACKS:
        raise ValueError('Attack không được hỗ trợ: ' + name)
    if name in ('gaussian_noise', 'salt_pepper'):
        parameters['rng'] = np.random.default_rng(seed)
    return ATTACKS[name](image, **parameters)
