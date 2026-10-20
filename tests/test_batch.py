import json
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from experiments import batch_runner as batch
from experiments.experiment_config import default_config
from services.stego_service import StegoService
from storage.history_store import HistoryStore


def config():
    c = default_config()
    c.update(payload_levels=[{'kind': 'bytes', 'value': v} for v in (0, 8)], seeds=[7, 8, 7],
             attacks=[{'name': 'brightness', 'parameters': {'delta': v}} for v in (0, 1)] +
                     [{'name': 'gaussian_noise', 'parameters': {'sigma': v}} for v in (0, 1)])
    return c


def covers(tmp_path):
    paths = []
    for i in range(2):
        p = tmp_path / f'{i}.png'
        Image.fromarray(np.full((80, 80), 128 + i, dtype=np.uint8)).save(p)
        paths.append(p)
    return paths


def test_matrix_reproducible_private_unique_and_history(tmp_path):
    paths = covers(tmp_path)
    hashes = [p.read_bytes() for p in paths]
    c = batch.batch_config(config())
    assert c['seeds'] == [7, 8]
    assert batch.planned_counts(2, c) == {'images': 2, 'embeddings': 8, 'cases': 56}
    service = StegoService(HistoryStore(tmp_path / 'history.json'))
    a = service.run_batch(paths, tmp_path / 'results', c)
    b = batch.run_batch(paths, tmp_path / 'results', c)
    assert a['output_dir'] != b['output_dir']
    assert a['rows'] == b['rows'] and a['summary'] == b['summary']
    assert len(a['rows']) == 56
    assert all(r['seed'] is None for r in a['rows'] if r['attack'] != 'gaussian_noise')
    assert [p.read_bytes() for p in paths] == hashes
    assert len(service.history.get_all()) == 1
    assert any(r['ber_after_attack'] is None for r in a['rows'])
    for p in Path(a['output_dir']).glob('*'):
        if p.is_file():
            text = p.read_text(encoding='utf-8-sig')
            assert 'ABCDEFGH' not in text and 'expected_packet' not in text and 'raw_payload' not in text
    manifest = json.loads((Path(a['output_dir']) / 'config.json').read_text(encoding='utf-8'))
    assert all(i['sha256'] for i in manifest['images'])


def test_baseline_exclusions_and_common(tmp_path):
    paths = covers(tmp_path)
    tiny = tmp_path / 'tiny.bmp'
    Image.fromarray(np.zeros((2, 2), dtype=np.uint8)).save(tiny)
    bad = tmp_path / 'bad.png'
    bad.write_text('broken')
    result = batch.run_batch(paths + [tiny, bad], tmp_path / 'out', config())
    assert len(result['rows']) == 56
    assert {b['baseline_status'] for b in result['baselines']} == {'valid', 'capacity', 'embed_io_error'}
    assert all(r['ber_after_attack'] is None or 0 <= r['ber_after_attack'] <= 1 for r in result['rows'])
    for r in result['summary']:
        assert r['expected_images'] == 4 and r['baseline_valid'] == 2
        assert r['baseline_capacity'] == 1 and r['baseline_embed_io_error'] == 1
        assert r['eligible_images'] == 2


def test_baseline_mismatch_never_attacked(tmp_path, monkeypatch):
    paths = covers(tmp_path)
    from services import stego_service
    original = stego_service.engine_for
    def engine(method):
        e = original(method)
        return SimpleNamespace(calculate_capacity=e.calculate_capacity, embed=e.embed,
                               extract=lambda image: np.zeros(31, dtype=np.uint8)) if method == 'DWT' else e
    monkeypatch.setattr(stego_service, 'engine_for', engine)
    result = batch.run_batch(paths, tmp_path / 'out', config())
    assert all(r['method'] == 'PVD' for r in result['rows'])
    assert all(b['baseline_status'] == 'mismatch' and b['stego_path'] for b in result['baselines'] if b['method'] == 'DWT')
    assert all(r['completed_cases'] == 0 and r['image_ber_mean'] is None for r in result['summary'] if r['scope'] == 'common')


def test_independent_image_weighted_fixture():
    c = batch.batch_config(config())
    baselines = [{'image_id': i, 'method': m, 'payload_bytes': 0, 'baseline_status': 'valid' if (i, m) != (2, 'DWT') else 'mismatch'}
                 for i in (0, 1, 2) for m in ('PVD', 'DWT')]
    rows = []
    for i, results in [(0, [(True, 0), (False, .5), (False, None)]), (1, [(True, None)]), (2, [(False, .25)])]:
        for success, ber in results:
            rows.append(dict(image_id=i, method='PVD', payload_bytes=0, attack='none', attack_parameter='{}',
                             extract_success=success, ber_after_attack=ber))
    r = batch.aggregate(rows, baselines, [0, 1, 2], c)[0]
    assert r['pooled_success_rate'] == pytest.approx(2 / 5)
    assert r['image_success_mean'] == pytest.approx(4 / 9)
    assert r['image_success_std'] == pytest.approx((7 / 27) ** .5)
    assert r['image_ber_mean'] == .25
    assert (r['ber_valid_cases'], r['ber_na_cases'], r['ber_contributing_images'], r['ber_no_valid_images']) == (3, 2, 2, 1)
    common = batch.aggregate(rows, baselines, [0, 1, 2], c, common=True)[0]
    assert common['eligible_images'] == 2 and common['completed_cases'] == 4
    assert common['baseline_valid'] == 3
    assert common['image_success_mean'] == pytest.approx(2 / 3)


def test_cancel_and_no_cumulative_attacks(tmp_path, monkeypatch):
    paths = covers(tmp_path)
    event = Event()
    original = batch.apply_attack
    seen = []
    def attack(image, name, parameters, seed):
        seen.append(image.copy())
        result = original(image, name, parameters, seed=seed)
        image[:] = 0  # Runner must protect baseline even from a mutating attack.
        return result
    monkeypatch.setattr(batch, 'apply_attack', attack)
    def progress(p):
        if p['completed'] == 4:
            event.set()
    result = batch.run_batch(paths, tmp_path / 'out', config(), event, progress)
    assert result['status'] == 'cancelled' and len(result['rows']) == 4
    assert all(np.array_equal(seen[0], image) for image in seen)
    assert sum(r['completed_cases'] for r in result['summary'] if r['scope'] == 'all') == 4
    assert sum(r['success_cases'] for r in result['summary'] if r['scope'] == 'all') <= 4
    assert any(r['baseline_unprocessed'] for r in result['summary'])


def test_scan_and_validation(tmp_path):
    covers(tmp_path)
    (tmp_path / 'sub').mkdir()
    (tmp_path / 'bad.png').write_text('broken')
    (tmp_path / 'note.txt').write_text('unsupported')
    entries = batch.scan_directory(tmp_path)
    assert len(entries) == 4 and sum(e['status'] == 'ready' for e in entries) == 2
    for patch in ({'seeds': [-1]}, {'seeds': [True]}, {'payload_levels': [{'kind': 'bytes', 'value': -1}]},
                  {'attacks': [{'name': 'blur', 'parameters': {'kernel_size': 53}}]}):
        with pytest.raises(ValueError):
            batch.batch_config(config() | patch)


def test_save_error_is_baseline_error_and_other_method_continues(tmp_path, monkeypatch):
    original = batch.save_stego
    def save(image, path):
        if 'PVD' in str(path):
            raise OSError('Cannot save PNG')
        return original(image, path)
    monkeypatch.setattr(batch, 'save_stego', save)
    result = batch.run_batch(covers(tmp_path), tmp_path / 'out', config())
    assert all(b['baseline_status'] == 'embed_io_error' and not b['stego_path']
               for b in result['baselines'] if b['method'] == 'PVD')
    assert len(result['rows']) == 28 and all(r['method'] == 'DWT' for r in result['rows'])
