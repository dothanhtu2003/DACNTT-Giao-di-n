"""PNG/BMP input and lossless PNG-only stego output."""

from pathlib import Path

import numpy as np
from PIL import Image

from core.engine_utils import validate_image


def load_image(path):
    path = Path(path)
    if path.suffix.lower() not in {'.png', '.bmp'}:
        raise ValueError('Luồng ứng dụng chỉ nhận PNG/BMP; JPEG chỉ dùng trong thực nghiệm.')
    with Image.open(path) as source:
        if source.format not in {'PNG', 'BMP'}:
            raise ValueError('Nội dung file không phải PNG/BMP.')
        if source.mode not in {'L', 'RGB', 'RGBA'}:
            if source.mode in {'1', 'P'}:
                source = source.convert('RGBA' if 'transparency' in source.info else 'RGB')
            else:
                raise ValueError('Chỉ hỗ trợ ảnh 8-bit grayscale/RGB/RGBA.')
        return validate_image(np.array(source))


def save_stego(image, path):
    path = Path(path)
    if path.suffix.lower() != '.png':
        raise ValueError('Ảnh Stego chỉ được lưu PNG lossless.')
    Image.fromarray(validate_image(image)).save(path, format='PNG')
    return str(path.resolve())


def image_info(image):
    image = validate_image(image)
    channels = 1 if image.ndim == 2 else image.shape[2]
    return {'width': image.shape[1], 'height': image.shape[0], 'channels': channels,
            'mode': {1: 'L', 3: 'RGB', 4: 'RGBA'}[channels]}


def create_thumbnail(image, size=(360, 260)):
    thumbnail = Image.fromarray(validate_image(image))
    thumbnail.thumbnail(size, Image.Resampling.LANCZOS)
    return thumbnail
