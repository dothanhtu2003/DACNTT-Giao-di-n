"""Application orchestration. Secret text exists only in memory, never history."""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from core import pvd, dwt
from core.image_utils import load_image, image_info, save_stego
from core.payload import build_packet, packet_to_bits, decode_message, read_length
from metrics.metrics import payload_metrics, psnr, ssim, ber
from storage.history_store import HistoryStore

ENGINES = {'PVD': pvd, 'DWT': dwt}


def engine_for(method):
    if method not in ENGINES:
        raise ValueError('Phương pháp phải là PVD hoặc DWT.')
    return ENGINES[method]


def base_result(path, method):
    return dict.fromkeys(['output_image', 'capacity_bits', 'packet_bits', 'payload_bytes',
                          'usage_percent', 'bpp', 'psnr', 'ssim', 'ber', 'error']) | {
        'success': False, 'method': method, 'input_path': str(path),
        'status': 'failed', 'extract_status': 'not_checked', 'error_type': None,
    }


class StegoService:
    def __init__(self, history=None):
        self.history = history if history is not None else HistoryStore()

    def _record(self, result, operation):
        record = {key: result.get(key) for key in (
            'method', 'output_path', 'width', 'height', 'payload_bytes', 'packet_bits',
            'capacity_bits', 'usage_percent', 'bpp', 'psnr', 'ssim', 'ber', 'status')}
        record.update(timestamp=datetime.now(timezone.utc).isoformat(), operation=operation,
                      input_filename=Path(result['input_path']).name)
        try:
            result['history_id'] = self.history.add_record(record)
        except OSError:
            result['history_warning'] = 'Không ghi được lịch sử; kiểm tra quyền truy cập thư mục data.'

    def inspect(self, image_path, message, method):
        engine = engine_for(method)
        image = load_image(image_path)
        info = image_info(image)
        metrics = payload_metrics(len(message.encode('utf-8')), engine.calculate_capacity(image),
                                  info['width'], info['height'])
        return info | metrics

    def embed(self, image_path, message, method, *, operation='embed'):
        result = base_result(image_path, method)
        try:
            engine = engine_for(method)
            image = load_image(image_path)
            result.update(image_info(image))
            expected = packet_to_bits(build_packet(message))
            result.update(payload_metrics(len(message.encode('utf-8')), engine.calculate_capacity(image),
                                          result['width'], result['height']))
            output = engine.embed(image, expected)
            result.update(output_image=output, psnr=psnr(image, output))
            result['ssim'] = ssim(image, output) if min(image.shape[:2]) >= 3 else None
            # No success claim when clipping/rounding prevents exact recovery.
            try:
                actual = engine.extract(output)
                if len(actual) == len(expected) and np.array_equal(actual[:32], expected[:32]):
                    result['ber'] = ber(expected, actual)
                if not np.array_equal(actual, expected):
                    raise ValueError('Packet trích xuất không khớp dữ liệu gốc.')
                decode_message(actual)
                result.update(success=True, status='success', extract_status='integrity_verified')
            except (ValueError, OverflowError) as exc:
                result.update(status='extraction_failed', extract_status='extraction_failed',
                              error='Không khôi phục chính xác packet sau nhúng; hãy chọn ảnh khác. ' + str(exc),
                              error_type=type(exc).__name__)
        except (OSError, ValueError, TypeError, OverflowError) as exc:
            result.update(error=str(exc), error_type=type(exc).__name__)
        self._record(result, operation)
        return result

    def extract(self, image_path, method):
        result = base_result(image_path, method)
        try:
            engine = engine_for(method)
            image = load_image(image_path)
            result.update(image_info(image))
            result['capacity_bits'] = engine.calculate_capacity(image)
            bits = engine.extract(image)
            result.update(payload_metrics(read_length(bits), result['capacity_bits'],
                                          result['width'], result['height']))
            result['message'] = decode_message(bits)
            result.update(success=True, status='success', extract_status='valid_length_utf8')
        except (OSError, ValueError, TypeError, OverflowError) as exc:
            result.update(error=str(exc), error_type=type(exc).__name__, status='extraction_failed',
                          extract_status='extraction_failed')
        self._record(result, 'extract')
        return result

    def compare(self, image_path, message):
        results = {method: self.embed(image_path, message, method, operation='compare') for method in ENGINES}
        successes = sum(result['success'] for result in results.values())
        return {'status': {0: 'failed', 1: 'partial', 2: 'success'}[successes], 'results': results}

    def save(self, result, path):
        if not result['success'] or result['output_image'] is None:
            raise ValueError('Chưa có ảnh Stego được kiểm tra thành công để lưu.')
        output_path = save_stego(result['output_image'], path)
        result['output_path'] = output_path
        self._record(result, 'save')
        return output_path
