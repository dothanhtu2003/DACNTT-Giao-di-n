"""PVD: Blue/intensity, horizontal non-overlapping raster pairs."""

import numpy as np

from core.engine_utils import CapacityError, validate_image
from core.payload import checked_bits, read_length, validate_length, InsufficientDataError

LOWER = np.array([0, 8, 16, 32, 64, 128])
BITS = np.array([3, 3, 4, 5, 6, 7])


def _pairs(image):
    image = validate_image(image)
    channel = image if image.ndim == 2 else image[:, :, 2]
    width = channel.shape[1] // 2 * 2
    return channel, channel[:, :width].reshape(-1, 2).astype(np.int16)


def _ranges(pairs):
    return np.searchsorted(LOWER, np.abs(pairs[:, 0] - pairs[:, 1]), side='right') - 1


def calculate_capacity(image):
    _, pairs = _pairs(image)
    return int(BITS[_ranges(pairs)].sum())


def embed(image, bits):
    bits = checked_bits(bits)
    capacity = calculate_capacity(image)
    if len(bits) > capacity:
        raise CapacityError(f'Packet {len(bits)} bit vượt capacity PVD {capacity} bit.')
    output = image.copy()
    channel, pairs = _pairs(output)
    ranges = _ranges(pairs)
    offset = 0
    for i, (p1, p2) in enumerate(pairs):
        if offset >= len(bits):
            break
        count = int(BITS[ranges[i]])
        chunk = bits[offset:offset + count]
        value = 0
        for bit in chunk:
            value = value * 2 + int(bit)
        value <<= count - len(chunk)
        difference = int(LOWER[ranges[i]]) + value
        sign = 1 if p1 >= p2 else -1
        # The nearest integer pair for a fixed signed difference minimizes distortion.
        first = int(np.floor((int(p1) + int(p2) + sign * difference) / 2 + 0.5))
        second = first - sign * difference
        shift = max(0, -min(first, second)) - max(0, max(first, second) - 255)
        pairs[i] = (first + shift, second + shift)
        offset += count
    width = channel.shape[1] // 2 * 2
    channel[:, :width] = pairs.reshape(channel.shape[0], width)
    return output


def extract_n_bits(image, count):
    _, pairs = _pairs(image)
    ranges = _ranges(pairs)
    sizes = BITS[ranges]
    if not isinstance(count, (int, np.integer)) or count < 0 or count > int(sizes.sum()):
        raise InsufficientDataError('Không đủ bit PVD được yêu cầu.')
    values = np.abs(pairs[:, 0] - pairs[:, 1]) - LOWER[ranges]
    result = np.empty(count, dtype=np.uint8)
    offset = 0
    for value, size in zip(values, sizes):
        for shift in range(int(size) - 1, -1, -1):
            if offset == count:
                return result
            result[offset] = (int(value) >> shift) & 1
            offset += 1
    return result


def extract(image):
    length = read_length(extract_n_bits(image, 32))
    validate_length(length, calculate_capacity(image))
    return extract_n_bits(image, 32 + 8 * length)
