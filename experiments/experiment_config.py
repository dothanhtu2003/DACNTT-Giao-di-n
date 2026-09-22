"""Exploratory levels, not approved final Chapter 4 experiment parameters."""

from copy import deepcopy

SEED = 20260919
PAYLOAD_LEVELS = [{'kind': 'bytes', 'value': 8}, {'kind': 'bytes', 'value': 32}]
ATTACK_LEVELS = [
    {'name': 'none', 'parameters': {}},
    *[{'name': 'jpeg', 'parameters': {'quality': value}} for value in (90, 70)],
    *[{'name': 'gaussian_noise', 'parameters': {'sigma': value}} for value in (1.0, 3.0)],
    *[{'name': 'salt_pepper', 'parameters': {'amount': value}} for value in (0.001, 0.01)],
    *[{'name': 'blur', 'parameters': {'kernel_size': value}} for value in (3, 5)],
    *[{'name': 'brightness', 'parameters': {'delta': value}} for value in (-10, 10)],
    *[{'name': 'contrast', 'parameters': {'alpha': value}} for value in (0.9, 1.1)],
    *[{'name': 'resize', 'parameters': {'scale': value}} for value in (0.75, 1.25)],
    *[{'name': 'crop', 'parameters': {'fraction': value}} for value in (0.9, 0.75)],
]


def default_config():
    return deepcopy({'seed': SEED, 'methods': ['PVD', 'DWT'], 'payload_levels': PAYLOAD_LEVELS,
                     'attacks': ATTACK_LEVELS, 'parameter_status': 'exploratory_not_final_chapter4',
                     'payload_generator': 'deterministic ASCII sequence; exact UTF-8 byte count',
                     'resize_policy': 'retain resized dimensions; no registration or size restoration',
                     'crop_policy': 'center crop; fraction per dimension; no padding or registration',
                     'rgba_policy': 'photometric attacks preserve alpha; JPEG encodes RGB and reattaches original alpha',
                     'dwt': {'wavelet': 'haar', 'level': 1, 'band': 'HH', 'delta': 18,
                             'repeat': 5, 'extension_mode': 'symmetric', 'majority_threshold': 3},
                     'pvd': {'channel': 'Blue/intensity', 'raster': 'horizontal_nonoverlap',
                             'ranges': [[0, 7], [8, 15], [16, 31], [32, 63], [64, 127], [128, 255]]},
                     'packet': 'uint32 big-endian LENGTH in bytes || UTF-8',
                     'bpp': '(32 + 8 * payload_bytes) / (width * height)'})
