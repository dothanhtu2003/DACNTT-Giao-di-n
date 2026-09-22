"""Packet LENGTH (uint32 big-endian byte count) || UTF-8 payload."""

import numpy as np


class PayloadError(ValueError):
    """Packet không hợp lệ."""


class LengthError(PayloadError):
    """LENGTH vượt giới hạn dữ liệu khả dụng."""


class InsufficientDataError(PayloadError):
    """Không đủ dữ liệu để đọc packet."""


class UTF8Error(PayloadError):
    """Payload không phải UTF-8 hợp lệ."""


def message_to_bytes(message):
    if not isinstance(message, str):
        raise TypeError('Message phải là chuỗi văn bản.')
    return message.encode('utf-8')


def checked_bits(bits):
    array = np.asarray(bits)
    if array.ndim != 1 or not np.all((array == 0) | (array == 1)):
        raise PayloadError('Bits phải là dãy một chiều chỉ chứa 0 và 1.')
    return array.astype(np.uint8)


def bytes_to_bits(data):
    return np.unpackbits(np.frombuffer(bytes(data), dtype=np.uint8))


def bits_to_bytes(bits):
    bits = checked_bits(bits)
    if len(bits) % 8:
        raise InsufficientDataError('Số bit phải chia hết cho 8.')
    return np.packbits(bits).tobytes()


def validate_length(length, available_bits=None):
    if not isinstance(length, (int, np.integer)) or not 0 <= length <= 0xFFFFFFFF:
        raise LengthError('LENGTH phải là unsigned 32-bit.')
    if available_bits is not None and 32 + 8 * length > available_bits:
        raise LengthError('LENGTH sai hoặc không đủ dữ liệu cho payload.')
    return int(length)


def build_packet(message):
    payload = message_to_bytes(message)
    validate_length(len(payload))
    return len(payload).to_bytes(4, 'big') + payload


def packet_to_bits(packet):
    return bytes_to_bits(packet)


def read_length(bits):
    bits = checked_bits(bits)
    if len(bits) < 32:
        raise InsufficientDataError('Không đủ 32 bit LENGTH.')
    return int.from_bytes(bits_to_bytes(bits[:32]), 'big')


def extract_payload(bits):
    bits = checked_bits(bits)
    length = read_length(bits)
    validate_length(length, len(bits))
    return bits_to_bytes(bits[32:32 + 8 * length])


def decode_message(bits):
    try:
        return extract_payload(bits).decode('utf-8', errors='strict')
    except UnicodeDecodeError as exc:
        raise UTF8Error('Payload chứa UTF-8 lỗi.') from exc
