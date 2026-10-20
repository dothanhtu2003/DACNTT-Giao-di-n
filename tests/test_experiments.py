import json
import os
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image

from experiments.experiment_config import default_config
from experiments.robustness_runner import run_experiments, assess_extraction, payload_size
from experiments.summarize_results import summarize
from core import pvd
from core.payload import packet_to_bits, build_packet


def test_legacy_quantitative_fixture(tmp_path):
    """Reference captured from the committed legacy runner before batch changes."""
    from pathlib import Path
    cover = tmp_path / 'legacy.png'
    Image.fromarray(np.full((80, 80, 3), 128, dtype=np.uint8)).save(cover)
    rows = run_experiments([cover], tmp_path / 'result', default_config())
    quantitative = [{k: v for k, v in row.items() if k not in ('run_id', 'stego_path')} for row in rows]
    for row in quantitative:
        if row.get('psnr_before_attack') == float('inf'):
            row['psnr_before_attack'] = 'Infinity'
    reference = json.loads((Path(__file__).parent / 'fixtures' / 'legacy_quantitative.json').read_text(encoding='utf-8'))
    assert quantitative == reference


def test_runner_reproducible_and_private(tmp_path):
    cover = tmp_path / 'cover.png'
    Image.fromarray(np.full((80, 80, 3), 128, dtype=np.uint8)).save(cover)
    config = default_config()
    config['payload_levels'] = [{'kind': 'bytes', 'value': 8}]
    config['attacks'] = [config['attacks'][0], {'name': 'gaussian_noise', 'parameters': {'sigma': 1.0}}]
    first = run_experiments([cover], tmp_path / 'a', config)
    second = run_experiments([cover], tmp_path / 'b', config)
    assert len(first) == 4
    for a, b in zip(first, second):
        assert {k: v for k, v in a.items() if k not in ('run_id', 'stego_path')} == {
            k: v for k, v in b.items() if k not in ('run_id', 'stego_path')}
    assert all(row['extract_success'] and row['ber_after_attack'] == 0 for row in first if row['attack'] == 'none')
    output = tmp_path / 'a' / 'robustness_results.csv'
    assert 'ABCDEFGH' not in output.read_text()
    assert not {'message', 'raw_payload', 'extracted_message'} & set(first[0])
    snapshot = json.loads((tmp_path / 'a' / 'experiment_config_snapshot.json').read_text())
    assert snapshot['seed'] == config['seed'] and snapshot['images'][0]['sha256']
    summary = tmp_path / 'summary.md'
    summarize(output, summary)
    assert 'Baseline' in summary.read_text(encoding='utf-8')


def test_extraction_failure_not_fabricated_ber():
    image = np.zeros((80, 80), dtype=np.uint8)
    expected = packet_to_bits(build_packet('a'))
    result = assess_extraction(pvd, image, expected)
    assert not result['extract_success'] and result['ber_after_attack'] is None


def test_invalid_utf8_ber_is_measurable():
    from core.payload import bytes_to_bits
    image = np.full((80, 80), 128, dtype=np.uint8)
    output = pvd.embed(image, bytes_to_bits(b'\0\0\0\1\xff'))
    result = assess_extraction(pvd, output, packet_to_bits(build_packet('a')))
    assert not result['extract_success'] and result['error_type'] == 'UTF8Error'
    assert result['ber_after_attack'] is not None


def test_capacity_failure_rows(tmp_path):
    path = tmp_path / 'tiny.png'
    Image.fromarray(np.zeros((2, 2), dtype=np.uint8)).save(path)
    config = default_config()
    config['attacks'] = [config['attacks'][0]]
    rows = run_experiments([path], tmp_path / 'results', config)
    assert all(row['error_type'] == 'CapacityError' and row['ber_after_attack'] is None for row in rows)
    assert payload_size({'kind': 'capacity_fraction', 'value': 0.5}, 192) == 8
    config['attacks'] = []
    with pytest.raises(ValueError):
        run_experiments([path], tmp_path / 'results', config)


def test_cli_unicode_paths(tmp_path):
    folder = tmp_path / 'ảnh tiếng Việt'
    folder.mkdir()
    Image.fromarray(np.full((40, 40), 128, dtype=np.uint8)).save(folder / 'ảnh.png')
    output = tmp_path / 'kết quả'
    result = subprocess.run([sys.executable, '-m', 'experiments.benchmark_runner', '--images', str(folder),
                             '--output', str(output), '--payload-bytes', '0'], capture_output=True,
                            env=os.environ | {'PYTHONIOENCODING': 'cp1252'}, timeout=30)
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    assert (output / 'robustness_results.csv').exists()


def test_gui_service_matches_benchmark_actual_case_seed(tmp_path):
    from services.stego_service import StegoService
    from storage.history_store import HistoryStore
    from experiments.robustness_runner import public_payload
    path = tmp_path / 'same.png'
    Image.fromarray(np.random.default_rng(27).integers(24, 232, (128, 128, 4),
                                                      dtype=np.uint8)).save(path)
    config = default_config()
    config['payload_levels'] = [{'kind': 'bytes', 'value': 8}]
    rows = run_experiments([path], tmp_path / 'benchmark', config)
    service = StegoService(HistoryStore(tmp_path / 'history.json'))
    embedded = service.compare(path, public_payload(8))['results']
    assert all(r['success'] for r in embedded.values())
    for attack in config['attacks']:
        parameter = json.dumps(attack['parameters'], sort_keys=True, separators=(',', ':'))
        cases = [r for r in rows if r['attack'] == attack['name'] and r['attack_parameter'] == parameter]
        results = service.try_robustness(embedded, attack['name'], attack['parameters'], cases[0]['seed'])
        for row in cases:
            result = results[row['method']]
            assert result['ber'] == row['ber_after_attack']
            assert result['success'] == row['extract_success']
            assert result['error_type'] == row['error_type']
            assert (result['width'], result['height']) == (row['attacked_width'], row['attacked_height'])
