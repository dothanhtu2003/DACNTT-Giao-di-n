"""Haar level 1 / HH / QIM Delta 18 / repetition 5.

Capacity is a logical coefficient capacity, not a guarantee against distortion
caused by pixel clipping, color conversion, or symmetric odd-edge extension.
"""

import numpy as np
import pywt

from core.engine_utils import CapacityError, validate_image
from core.payload import checked_bits, read_length, validate_length, InsufficientDataError

DELTA = 18
REPEAT = 5
WAVELET = 'haar'
MODE = 'symmetric'


def luminance(image):
    image = validate_image(image)
    if image.ndim == 2:
        return image.astype(np.float64)
    rgb = image[:, :, :3].astype(np.float64)
    return rgb @ np.array([0.299, 0.587, 0.114])


def decompose_for_visualization(image):
    ll, (lh, hl, hh) = pywt.dwt2(luminance(image), WAVELET, mode=MODE)
    return {'LL': ll, 'LH': lh, 'HL': hl, 'HH': hh}


def calculate_capacity(image):
    image = validate_image(image)
    return ((image.shape[0] + 1) // 2 * ((image.shape[1] + 1) // 2)) // REPEAT


def quantize(coefficients, bits):
    return DELTA * np.rint((coefficients - bits * DELTA / 2) / DELTA) + bits * DELTA / 2


def coefficient_bits(coefficients):
    # Distances to the two nearest lattices; exact ties select zero.
    zero_distance = np.abs(coefficients - DELTA * np.rint(coefficients / DELTA))
    one_distance = np.abs(coefficients - (DELTA * np.rint((coefficients - DELTA / 2) / DELTA) + DELTA / 2))
    return (one_distance < zero_distance).astype(np.uint8)


def majority_vote(bits):
    bits = checked_bits(bits)
    if len(bits) % REPEAT:
        raise ValueError('Majority vote cần nhóm đủ 5 bit.')
    return (bits.reshape(-1, REPEAT).sum(axis=1) >= 3).astype(np.uint8)


def embed(image, bits):
    image = validate_image(image)
    bits = checked_bits(bits)
    capacity = calculate_capacity(image)
    if len(bits) > capacity:
        raise CapacityError(f'Packet {len(bits)} bit vượt capacity DWT {capacity} bit.')
    y = luminance(image)
    ll, (lh, hl, hh) = pywt.dwt2(y, WAVELET, mode=MODE)
    physical_bits = np.repeat(bits, REPEAT)
    flat = hh.ravel().copy()
    flat[:len(physical_bits)] = quantize(flat[:len(physical_bits)], physical_bits)
    restored_y = pywt.idwt2((ll, (lh, hl, flat.reshape(hh.shape))), WAVELET, mode=MODE)
    restored_y = restored_y[:image.shape[0], :image.shape[1]]
    if image.ndim == 2:
        return np.clip(np.rint(restored_y), 0, 255).astype(np.uint8)
    # Adding the Y difference to R,G,B is the inverse of YCbCr with Cb/Cr
    # unchanged, before the required rounding/clipping to displayable uint8.
    output = image.copy()
    output[:, :, :3] = np.clip(np.rint(image[:, :, :3].astype(float) + (restored_y - y)[:, :, None]), 0, 255).astype(np.uint8)
    return output


def extract_n_bits(image, count):
    if not isinstance(count, (int, np.integer)) or count < 0 or count > calculate_capacity(image):
        raise InsufficientDataError('Không đủ logical bit DWT được yêu cầu.')
    hh = decompose_for_visualization(image)['HH']
    return majority_vote(coefficient_bits(hh.ravel()[:count * REPEAT]))


def extract(image):
    length = read_length(extract_n_bits(image, 32))
    validate_length(length, calculate_capacity(image))
    return extract_n_bits(image, 32 + 8 * length)
