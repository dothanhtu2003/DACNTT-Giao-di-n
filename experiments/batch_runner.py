"""Sequential, cancellable dataset experiments. Legacy CLI runner stays unchanged."""

from collections import defaultdict
from copy import deepcopy
import csv
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
from statistics import mean, stdev
import tempfile
from uuid import uuid4

from PIL import Image

from core.image_utils import load_image, save_stego, image_info
from core.payload import build_packet, packet_to_bits
from experiments.attacks import apply_attack
from experiments.extraction import assess_extraction
from experiments.experiment_config import default_config
from experiments.robustness_runner import public_payload
from services.robustness import NOISE, validate_configuration


def scan_directory(folder):
    """Inspect direct files one at a time, including unsupported entries."""
    entries = []
    for path in sorted(Path(folder).iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file():
            continue
        entry = {'path': str(path.resolve()), 'name': path.name, 'status': 'ready'}
        try:
            if path.suffix.lower() not in {'.png', '.bmp'}:
                raise ValueError('Không hỗ trợ; chỉ nhận PNG/BMP')
            with Image.open(path) as source:
                entry.update(width=source.width, height=source.height, mode=source.mode)
            image = load_image(path)
            entry['effective_mode'] = image_info(image)['mode']
            del image
        except (OSError, ValueError) as exc:
            entry.update(status='unreadable', error=str(exc))
        entries.append(entry)
    return entries


def batch_config(config=None):
    config = deepcopy(default_config() if config is None else config)
    if config.get('methods') != ['PVD', 'DWT']:
        raise ValueError('Bộ ảnh yêu cầu cả PVD và DWT, theo thứ tự này.')
    levels = config.get('payload_levels', [])
    if not levels or any(level.get('kind') != 'bytes' or type(level.get('value')) is not int
                         or not 0 <= level['value'] <= 0xFFFFFFFF for level in levels):
        raise ValueError('Payload cần danh sách số byte nguyên không âm, tối đa uint32.')
    config['payload_levels'] = [{'kind': 'bytes', 'value': v} for v in dict.fromkeys(l['value'] for l in levels)]
    seeds = config.get('seeds', list(range(config['seed'], config['seed'] + 5)))
    if not seeds or any(type(s) is not int or s < 0 for s in seeds):
        raise ValueError('Cần ít nhất một seed nguyên không âm.')
    config['seeds'] = list(dict.fromkeys(seeds))
    attacks = [{'name': 'none', 'parameters': {}}]
    for attack in config.get('attacks', []):
        params, _ = validate_configuration(attack['name'], attack['parameters'], config['seeds'][0])
        item = {'name': attack['name'], 'parameters': params}
        if item not in attacks:
            attacks.append(item)
    config['attacks'] = attacks
    config['seed_policy'] = 'listed seed directly for noise only; shared across methods/images/payloads'
    config['export_details'] = bool(config.get('export_details', True))
    return config


def attack_cases(config):
    return [(a, seed) for a in config['attacks']
            for seed in (config['seeds'] if a['name'] in NOISE else [None])]


def planned_counts(image_count, config):
    config = batch_config(config)
    embeddings = image_count * 2 * len(config['payload_levels'])
    return {'images': image_count, 'embeddings': embeddings,
            'cases': embeddings * len(attack_cases(config))}


def aggregate(rows, baselines, image_ids, config, common=False):
    """Image-weighted statistics; completed cases alone form denominators."""
    output = []
    statuses = {(b['image_id'], b['method'], b['payload_bytes']): b['baseline_status'] for b in baselines}
    for level in config['payload_levels']:
        payload = level['value']
        shared = {i for i in image_ids if all(statuses.get((i, m, payload)) == 'valid' for m in config['methods'])}
        for method in config['methods']:
            counts = {s: sum(statuses.get((i, method, payload)) == s for i in image_ids)
                      for s in ('valid', 'capacity', 'embed_io_error', 'mismatch')}
            for attack in config['attacks']:
                parameter = json.dumps(attack['parameters'], sort_keys=True, separators=(',', ':'))
                cases = [r for r in rows if r['method'] == method and r['payload_bytes'] == payload
                         and r['attack'] == attack['name'] and r['attack_parameter'] == parameter
                         and (not common or r['image_id'] in shared)]
                by_image = defaultdict(list)
                for row in cases:
                    by_image[row['image_id']].append(row)
                rates = [sum(r['extract_success'] for r in group) / len(group) for group in by_image.values()]
                bers = [[r['ber_after_attack'] for r in group if r['ber_after_attack'] is not None]
                        for group in by_image.values()]
                valid_ber = sum(map(len, bers))
                image_bers = [mean(values) for values in bers if values]
                successes = sum(r['extract_success'] for r in cases)
                output.append({'scope': 'common' if common else 'all', 'method': method,
                    'payload_bytes': payload, 'attack': attack['name'], 'attack_parameter': parameter,
                    'expected_images': len(image_ids), 'eligible_images': len(shared) if common else counts['valid'],
                    'baseline_valid': counts['valid'], 'baseline_capacity': counts['capacity'],
                    'baseline_embed_io_error': counts['embed_io_error'], 'baseline_mismatch': counts['mismatch'],
                    'baseline_unprocessed': len(image_ids) - sum(counts.values()),
                    'completed_cases': len(cases), 'success_cases': successes,
                    'pooled_success_rate': successes / len(cases) if cases else None,
                    'image_success_mean': mean(rates) if rates else None,
                    'image_success_std': stdev(rates) if len(rates) >= 2 else None,
                    'image_ber_mean': mean(image_bers) if image_bers else None,
                    'ber_valid_cases': valid_ber, 'ber_na_cases': len(cases) - valid_ber,
                    'ber_contributing_images': len(image_bers),
                    'ber_no_valid_images': len(bers) - len(image_bers)})
    return output


def _csv(path, rows, columns):
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({k: 'NA' if r.get(k) is None else r.get(k) for k in columns} for r in rows)


def run_batch(image_paths, output_root, config=None, cancel=None, progress=None):
    from services.stego_service import engine_for
    config = batch_config(config)
    paths = sorted(set(Path(p).resolve() for p in image_paths), key=str)
    if not paths:
        raise ValueError('Không có ảnh nguồn PNG/BMP.')
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid4().hex
    folder = Path(output_root).resolve() / run_id
    export_details = config['export_details']
    folder.mkdir(parents=True, exist_ok=False)
    if export_details:
        (folder / 'stego').mkdir()
    counts = planned_counts(len(paths), config)
    rows, baselines, images = [], [], []
    stopped = lambda: cancel is not None and cancel.is_set()
    def report(name):
        if progress:
            progress({'completed': len(rows), 'total': counts['cases'], 'image': name,
                      'baselines': len(baselines), 'embeddings': counts['embeddings']})
    # Hash the whole input manifest, without retaining image arrays.
    for path in paths:
        entry = {'path': str(path), 'name': path.name, 'sha256': None}
        try:
            with path.open('rb') as handle:
                digest = hashlib.sha256()
                for block in iter(lambda: handle.read(1024 * 1024), b''):
                    digest.update(block)
            entry['sha256'] = digest.hexdigest()
        except OSError as exc:
            entry['error'] = str(exc)
        images.append(entry)
    for index, path in enumerate(paths):
        if stopped():
            break
        report(path.name)
        image, load_error = None, None
        try:
            image = load_image(path)
            images[index].update(image_info(image))
        except (OSError, ValueError) as exc:
            load_error = exc
        for method in config['methods']:
            for level in config['payload_levels']:
                if stopped():
                    break
                byte_count = level['value']
                base = {'image_id': index, 'image_name': path.name, 'method': method,
                        'payload_bytes': byte_count, 'baseline_status': 'embed_io_error',
                        'stego_path': '', 'error': '', 'capacity_bits': None}
                output = expected = None
                temporary_stego = None
                try:
                    if load_error:
                        raise load_error
                    engine = engine_for(method)
                    capacity = engine.calculate_capacity(image)
                    base['capacity_bits'] = capacity
                    if 32 + 8 * byte_count > capacity:
                        base.update(baseline_status='capacity', error='Không đủ dung lượng')
                    else:
                        expected = packet_to_bits(build_packet(public_payload(byte_count)))
                        output = engine.embed(image, expected)
                        if export_details:
                            relative = f'stego/{index}_{method}_{byte_count}.png'
                            stego_file = folder / relative
                            base['stego_path'] = relative
                        else:
                            handle = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                            temporary_stego = Path(handle.name)
                            handle.close()
                            stego_file = temporary_stego
                        save_stego(output, stego_file)
                        output = load_image(stego_file)
                        assessment = assess_extraction(engine, output, expected)
                        base.update(baseline_status='valid' if assessment['extract_success'] else 'mismatch',
                                    error=assessment['notes'])
                except Exception as exc:
                    base['error'] = f'{type(exc).__name__}: {exc}'
                finally:
                    if temporary_stego is not None:
                        try:
                            temporary_stego.unlink(missing_ok=True)
                        except OSError:
                            pass
                baselines.append(base)
                if base['baseline_status'] == 'valid':
                    for attack, seed in attack_cases(config):
                        if stopped():
                            break
                        row = {k: base[k] for k in ('image_id', 'image_name', 'method', 'payload_bytes', 'stego_path')}
                        row.update(attack=attack['name'], attack_parameter=json.dumps(attack['parameters'], sort_keys=True, separators=(',', ':')),
                                   seed=seed, extract_success=False, ber_after_attack=None, error_type='', notes='')
                        try:
                            if attack['name'] == 'none':
                                row.update(assessment)
                            else:
                                attacked = apply_attack(output.copy(), attack['name'], attack['parameters'], seed=seed)
                                row.update(assess_extraction(engine, attacked, expected))
                                del attacked
                        except Exception as exc:
                            row.update(error_type=type(exc).__name__, notes=str(exc))
                        rows.append(row)
                        report(path.name)
                output = expected = None
                report(path.name)
        image = None
    summary = aggregate(rows, baselines, list(range(len(paths))), config)
    summary += aggregate(rows, baselines, list(range(len(paths))), config, common=True)
    status = 'cancelled' if stopped() else 'completed'
    snapshot = {'run_id': run_id, 'status': status, 'incomplete': status != 'completed', 'config': config,
                'images': images, 'planned': counts, 'completed_cases': len(rows),
                'processed_baselines': len(baselines), 'environment': {'python': platform.python_version(),
                'platform': platform.platform(), **{n: version(n) for n in ('numpy', 'Pillow', 'PyWavelets', 'scikit-image', 'opencv-python')}}}
    _csv(folder / 'summary.csv', summary, list(summary[0]))
    (folder / 'config.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    if export_details:
        _csv(folder / 'cases.csv', rows, ['image_id', 'image_name', 'method', 'payload_bytes', 'stego_path',
             'attack', 'attack_parameter', 'seed', 'extract_success', 'ber_after_attack', 'error_type', 'notes'])
        _csv(folder / 'baselines.csv', baselines, ['image_id', 'image_name', 'method', 'payload_bytes', 'baseline_status', 'capacity_bits', 'stego_path', 'error'])
    lines = ['# Kết quả Bộ ảnh', '', f'Trạng thái: {status}; chưa đầy đủ: {snapshot["incomplete"]}.',
             f'Đã hoàn tất {len(rows)}/{counts["cases"]} ca dự kiến.', '',
             'Tỷ lệ khôi phục toàn bộ packet là chỉ số chính. Mẫu số chỉ gồm ca đã hoàn tất; ca chưa chạy không là thất bại.',
             'Baseline: nhúng, lưu/đọc PNG, kiểm tra toàn bộ packet. Cấu hình baseline lỗi nằm riêng trong baselines.csv, không chạy tác động.',
             'image_success_mean: trung bình tỷ lệ đúng của từng ảnh; image_success_std: độ lệch chuẩn mẫu, dưới 2 ảnh là NA.',
             'image_ber_mean: trung bình BER hợp lệ trong từng ảnh, rồi trung bình giữa các ảnh có BER. LENGTH hoặc độ dài khác: BER NA.',
             'Mẫu số 0 là NA. Ảnh không có BER hợp lệ không nhận BER=0. Luôn đọc số ca/ảnh BER NA để nhận biết lệch chọn lọc.',
             'scope=common: chỉ ảnh baseline hợp lệ cả PVD/DWT tại cùng payload; các cột baseline vẫn đếm toàn bộ tập dự kiến.',
             'Không gộp payload hay mức tác động. Resize/crop không căn chỉnh. Không lưu ảnh sau tác động.', '',
             '| Tập | Method | Bytes | Attack | Parameter | Ca | Đúng | TB theo ảnh | SD | BER TB theo ảnh | BER NA |',
             '|---|---|---|---|---|---|---|---|---|---|---|']
    for r in summary:
        lines.append('| ' + ' | '.join('NA' if r[k] is None else str(r[k]) for k in
                     ('scope', 'method', 'payload_bytes', 'attack', 'attack_parameter', 'completed_cases',
                      'success_cases', 'image_success_mean', 'image_success_std', 'image_ber_mean', 'ber_na_cases')) + ' |')
    if export_details:
        (folder / 'summary.md').write_text('\n'.join(lines), encoding='utf-8')
    return {'run_id': run_id, 'status': status, 'output_dir': str(folder), 'counts': counts,
            'completed_cases': len(rows), 'summary': summary, 'baselines': baselines, 'rows': rows,
            'details_saved': export_details}
