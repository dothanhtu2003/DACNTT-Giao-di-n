"""Reproducible image × method × payload × attack matrix, independent of GUI/history."""

import csv
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
from uuid import uuid4

from core.image_utils import load_image, save_stego
from core.payload import build_packet, packet_to_bits
from experiments.extraction import assess_extraction
from experiments.attacks import apply_attack
from experiments.experiment_config import default_config
from metrics.metrics import payload_metrics, psnr, ssim
from services.stego_service import engine_for

COLUMNS = ['run_id', 'image_name', 'width', 'height', 'method', 'capacity_bits',
           'payload_bytes', 'packet_bits', 'bpp', 'usage_percent', 'psnr_before_attack',
           'ssim_before_attack', 'attack', 'attack_parameter', 'ber_after_attack',
           'extract_success', 'error_type', 'notes', 'payload_level', 'seed',
           'attacked_width', 'attacked_height', 'stego_path', 'image_sha256']


def public_payload(byte_count):
    if not isinstance(byte_count, int) or byte_count < 0:
        raise ValueError('Payload bytes phải là số nguyên không âm.')
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    return (alphabet * ((byte_count + len(alphabet) - 1) // len(alphabet)))[:byte_count]


def payload_size(level, capacity):
    if level['kind'] == 'bytes':
        value = level['value']
        if not isinstance(value, int) or value < 0:
            raise ValueError('Payload level bytes không hợp lệ.')
        return value
    if level['kind'] == 'capacity_fraction':
        fraction = level['value']
        if not 0 < fraction <= 1:
            raise ValueError('Capacity fraction phải thuộc (0,1].')
        return max(0, (int(capacity * fraction) - 32) // 8)
    raise ValueError('Payload kind phải là bytes hoặc capacity_fraction.')



def run_experiments(image_paths, output_dir, config=None):
    config = default_config() if config is None else config
    if not any(attack['name'] == 'none' for attack in config['attacks']):
        raise ValueError('Ma trận thực nghiệm bắt buộc có baseline attack=none.')
    if not config['methods'] or not config['payload_levels']:
        raise ValueError('Cần ít nhất một method và payload level.')
    for method in config['methods']:
        engine_for(method)
    paths = sorted((Path(path).resolve() for path in image_paths), key=str)
    if not paths:
        raise ValueError('Không có ảnh nguồn PNG/BMP.')
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stego_dir = output_dir / 'stego'
    stego_dir.mkdir(exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid4().hex[:8]
    snapshot = dict(config)
    snapshot.update(run_id=run_id, environment={'python': platform.python_version(), 'platform': platform.platform(),
                    **{name: version(name) for name in ['numpy', 'Pillow', 'PyWavelets', 'scikit-image', 'opencv-python']}},
                    images=[])
    rows = []
    for image_index, path in enumerate(paths):
        image = load_image(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        height, width = image.shape[:2]
        snapshot['images'].append({'name': path.name, 'sha256': digest, 'width': width, 'height': height})
        for method in config['methods']:
            engine = engine_for(method)
            capacity = engine.calculate_capacity(image)
            for payload_index, level in enumerate(config['payload_levels']):
                byte_count = payload_size(level, capacity)
                expected = packet_to_bits(build_packet(public_payload(byte_count)))
                base = {'run_id': run_id, 'image_name': path.name, 'width': width, 'height': height,
                        'method': method, **payload_metrics(byte_count, capacity, width, height),
                        'payload_level': json.dumps(level, sort_keys=True), 'image_sha256': digest}
                output = None
                embed_error = None
                try:
                    output = engine.embed(image, expected)
                    relative_path = Path('stego') / f'{run_id}_{image_index}_{method}_{payload_index}.png'
                    save_stego(output, output_dir / relative_path)
                    output = load_image(output_dir / relative_path)
                    base.update(stego_path=relative_path.as_posix(), psnr_before_attack=psnr(image, output),
                                ssim_before_attack=ssim(image, output) if min(height, width) >= 3 else None)
                except (OSError, ValueError, OverflowError) as exc:
                    embed_error = exc
                for attack in config['attacks']:
                    parameter_json = json.dumps(attack['parameters'], sort_keys=True, separators=(',', ':'))
                    seed_key = f'{config["seed"]}|{digest}|{byte_count}|{attack["name"]}|{parameter_json}'
                    case_seed = int.from_bytes(hashlib.sha256(seed_key.encode()).digest()[:4], 'big')
                    row = base | {'attack': attack['name'], 'attack_parameter': parameter_json,
                                  'seed': case_seed, 'extract_success': False, 'ber_after_attack': None,
                                  'error_type': '', 'notes': ''}
                    if embed_error is not None:
                        row.update(error_type=type(embed_error).__name__, notes='Embed failed: ' + str(embed_error))
                    else:
                        try:
                            attacked = apply_attack(output, attack['name'], attack['parameters'], seed=case_seed)
                            row.update(attacked_width=attacked.shape[1], attacked_height=attacked.shape[0])
                            row.update(assess_extraction(engine, attacked, expected))
                        except (ValueError, TypeError, OverflowError) as exc:
                            row.update(error_type=type(exc).__name__, notes='Attack failed: ' + str(exc))
                    rows.append(row)
    csv_path = output_dir / 'robustness_results.csv'
    with csv_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    snapshot['row_count'] = len(rows)
    (output_dir / 'experiment_config_snapshot.json').write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    return rows
