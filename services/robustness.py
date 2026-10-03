"""Interactive robustness configuration; image work stays in experiments."""

import math

import numpy as np

from experiments.experiment_config import ATTACK_LEVELS, SEED

NOISE = {'gaussian_noise', 'salt_pepper'}
ATTACK_LABELS = {
    'none': 'Không tác động', 'jpeg': 'Nén JPEG', 'gaussian_noise': 'Nhiễu Gaussian',
    'salt_pepper': 'Nhiễu muối tiêu', 'blur': 'Làm mờ Gaussian',
    'brightness': 'Thay đổi độ sáng', 'contrast': 'Thay đổi độ tương phản',
    'resize': 'Thay đổi kích thước', 'crop': 'Cắt ảnh giữa',
}
PARAMETER_HELP = {
    'quality': 'Chất lượng JPEG: số nguyên 1–100',
    'sigma': 'Sigma: độ lệch chuẩn mức pixel, ≥ 0',
    'amount': 'Tỷ lệ pixel nhiễu: 0–1',
    'kernel_size': 'Cạnh kernel: số nguyên lẻ 1–51 (giới hạn GUI)',
    'delta': 'Delta: cộng mức sáng pixel, số hữu hạn',
    'alpha': 'Alpha: hệ số tương phản, ≥ 0',
    'scale': 'Scale: tỷ lệ mỗi chiều, > 0 đến 4 (giới hạn GUI)',
    'fraction': 'Fraction: phần giữ lại mỗi chiều, > 0 đến 1',
}
DEFAULT_PARAMETERS = {}
for _level in ATTACK_LEVELS:
    DEFAULT_PARAMETERS.setdefault(_level['name'], dict(_level['parameters']))


def validate_configuration(name, parameters, seed=SEED):
    """Validate before submitting workers; NumPy accepts arbitrary nonnegative ints."""
    if name not in DEFAULT_PARAMETERS or set(parameters) != set(DEFAULT_PARAMETERS[name]):
        raise ValueError('Tác động hoặc tên tham số không hợp lệ.')
    normalized = {}
    for key, value in parameters.items():
        try:
            if key in ('quality', 'kernel_size'):
                if isinstance(value, bool) or (not isinstance(value, (int, str))):
                    raise ValueError('Cần số nguyên.')
                value = int(value)
            else:
                value = float(value)
                if not math.isfinite(value):
                    raise ValueError('Cần số hữu hạn.')
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError(PARAMETER_HELP[key]) from exc
        valid = {
            'quality': lambda v: 1 <= v <= 100,
            'kernel_size': lambda v: 1 <= v <= 51 and v % 2 == 1,
            'sigma': lambda v: v >= 0, 'amount': lambda v: 0 <= v <= 1,
            'delta': lambda v: True, 'alpha': lambda v: v >= 0,
            'scale': lambda v: 0 < v <= 4, 'fraction': lambda v: 0 < v <= 1,
        }[key](value)
        if not valid:
            raise ValueError(PARAMETER_HELP[key])
        normalized[key] = value
    if name in NOISE:
        try:
            if isinstance(seed, bool) or not isinstance(seed, (int, str)):
                raise ValueError('Cần số nguyên.')
            seed = int(seed)
            if seed < 0:
                raise ValueError('Seed âm.')
            np.random.SeedSequence(seed)
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError('Seed phải là số nguyên không âm được NumPy SeedSequence chấp nhận.') from exc
    else:
        seed = None
    return normalized, seed
