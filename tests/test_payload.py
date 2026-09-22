import pytest

from core.payload import (
    build_packet, packet_to_bits, decode_message, read_length, validate_length,
    bits_to_bytes, bytes_to_bits, LengthError, InsufficientDataError, UTF8Error,
)


@pytest.mark.parametrize('message', ['ASCII', 'Tiếng Việt có dấu', '🔐🙂', '', 'a' * 10000])
def test_roundtrip(message):
    packet = build_packet(message)
    bits = packet_to_bits(packet)
    assert len(bits) == 32 + 8 * len(message.encode('utf-8'))
    assert decode_message(bits) == message
    assert read_length(bits) == len(message.encode('utf-8'))
    assert bits_to_bytes(bits) == packet


@pytest.mark.parametrize('length', [-1, 2**32, 1.5])
def test_invalid_length(length):
    with pytest.raises(LengthError):
        validate_length(length)


def test_truncated():
    with pytest.raises(InsufficientDataError):
        read_length([0] * 31)
    with pytest.raises(LengthError):
        decode_message(bytes_to_bits(b'\x00\x00\x00\x02a'))
    with pytest.raises(InsufficientDataError):
        bits_to_bytes([1])


def test_invalid_utf8():
    with pytest.raises(UTF8Error):
        decode_message(bytes_to_bits(b'\x00\x00\x00\x01\xff'))
