"""Shared packet assessment; benchmark semantics are preserved."""

import numpy as np

from core.payload import decode_message
from metrics.metrics import ber


def assess_extraction(engine, image, expected):
    result = {'ber_after_attack': None, 'extract_success': False, 'error_type': '', 'notes': ''}
    try:
        actual = engine.extract(image)
        if len(actual) != len(expected) or not np.array_equal(actual[:32], expected[:32]):
            result.update(error_type='LengthMismatch', notes='LENGTH khác packet gốc; BER=NA vì chưa xác lập đồng bộ.')
            return result
        result['ber_after_attack'] = ber(expected, actual)
        decode_message(actual)
        result['extract_success'] = bool(np.array_equal(actual, expected))
        if not result['extract_success']:
            result.update(error_type='PayloadMismatch', notes='LENGTH khớp nhưng payload thay đổi.')
    except (ValueError, OverflowError) as exc:
        result.update(error_type=type(exc).__name__, notes='Trích xuất thất bại: ' + str(exc))
    return result

