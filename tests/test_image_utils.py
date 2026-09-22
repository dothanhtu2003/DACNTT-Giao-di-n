import numpy as np
import pytest
from PIL import Image

from core.image_utils import load_image, save_stego, image_info, create_thumbnail


@pytest.mark.parametrize('shape', [(12, 15), (12, 15, 3), (12, 15, 4)])
def test_png(shape, tmp_path):
    image = np.zeros(shape, dtype=np.uint8)
    path = tmp_path / 'stego.png'
    save_stego(image, path)
    assert np.array_equal(load_image(path), image)
    assert image_info(image)['width'] == 15
    assert create_thumbnail(image, (8, 8)).width <= 8


def test_input_rejections(tmp_path):
    image = np.zeros((8, 8), dtype=np.uint8)
    bmp = tmp_path / 'cover.bmp'
    Image.fromarray(image).save(bmp)
    assert np.array_equal(load_image(bmp), image)
    jpg = tmp_path / 'test.jpg'
    Image.fromarray(image).save(jpg)
    with pytest.raises(ValueError):
        load_image(jpg)
    with pytest.raises(ValueError):
        save_stego(image, jpg)
    disguised = tmp_path / 'fake.png'
    disguised.write_bytes(jpg.read_bytes())
    with pytest.raises(ValueError):
        load_image(disguised)
    with pytest.raises(FileNotFoundError):
        load_image(tmp_path / 'missing.png')
