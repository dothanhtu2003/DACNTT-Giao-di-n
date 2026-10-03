import json
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from core.payload import build_packet, packet_to_bits, bytes_to_bits
from experiments.attacks import apply_attack
from experiments.extraction import assess_extraction
from experiments.experiment_config import ATTACK_LEVELS, SEED
from services.robustness import DEFAULT_PARAMETERS, validate_configuration
from services.stego_service import StegoService
from storage.history_store import HistoryStore


@pytest.fixture
def comparison(tmp_path):
    path = tmp_path / 'cover.png'
    Image.fromarray(np.full((128, 128, 4), 128, dtype=np.uint8)).save(path)
    service = StegoService(HistoryStore(tmp_path / 'history.json'))
    return service, service.compare(path, 'secret 🔐')['results']


def test_none_and_private_history(comparison):
    service, embedded = comparison
    results = service.try_robustness(embedded, 'none', {}, 42)
    assert all(r['success'] and r['ber'] == 0 and r['seed'] is None for r in results.values())
    records = [r for r in service.history.get_all() if r['operation'] == 'robustness']
    assert len(records) == 2
    assert all(r['attack_parameters'] == '{}' for r in records)
    text = service.history.path.read_text(encoding='utf-8')
    assert 'secret' not in text
    assert not {'message', 'expected_packet', 'output_image', 'raw_payload'} & set(records[0])


def test_partial_and_isolated_errors(comparison, monkeypatch):
    service, embedded = comparison
    embedded['DWT']['success'] = False
    results = service.try_robustness(embedded, 'none', {})
    assert results['PVD']['success'] and results['DWT']['status'] == 'not_tested'
    assert len([r for r in service.history.get_all() if r['operation'] == 'robustness']) == 1
    embedded['DWT']['success'] = True
    from services import stego_service
    original = stego_service.engine_for
    def failing(method):
        if method == 'PVD':
            raise ValueError('independent failure')
        return original(method)
    monkeypatch.setattr(stego_service, 'engine_for', failing)
    results = service.try_robustness(embedded, 'none', {})
    assert results['PVD']['status'] == 'failed' and results['DWT']['success']


@pytest.mark.parametrize('actual', [bytes_to_bits(b'\0\0\0\2ab'), np.zeros(31, dtype=np.uint8)])
def test_length_mismatch(actual):
    result = assess_extraction(SimpleNamespace(extract=lambda image: actual), None,
                               packet_to_bits(build_packet('a')))
    assert result['ber_after_attack'] is None and not result['extract_success']


@pytest.mark.parametrize('payload,error', [(b'b', 'PayloadMismatch'), (b'\xff', 'UTF8Error')])
def test_packet_mismatch(payload, error):
    engine = SimpleNamespace(extract=lambda image: bytes_to_bits(b'\0\0\0\1' + payload))
    result = assess_extraction(engine, None, packet_to_bits(build_packet('a')))
    assert result['ber_after_attack'] > 0 and not result['extract_success']
    assert result['error_type'] == error


@pytest.mark.parametrize('name,params', [('gaussian_noise', {'sigma': 8}), ('salt_pepper', {'amount': .1})])
def test_seed_and_no_cumulative_mutation(comparison, name, params):
    service, embedded = comparison
    copies = {m: r['output_image'].copy() for m, r in embedded.items()}
    first = service.try_robustness(embedded, name, params, 2**100)
    second = service.try_robustness(embedded, name, params, 2**100)
    third = service.try_robustness(embedded, name, params, 2**100 + 1)
    for method in embedded:
        assert np.array_equal(copies[method], embedded[method]['output_image'])
        assert np.array_equal(first[method]['output_image'], second[method]['output_image'])
        assert not np.array_equal(first[method]['output_image'], third[method]['output_image'])
        assert np.array_equal(first[method]['output_image'], apply_attack(
            copies[method], name, params, seed=2**100))


@pytest.mark.parametrize('level', ATTACK_LEVELS)
def test_alpha_and_dimensions(comparison, level):
    service, embedded = comparison
    name, params = level['name'], level['parameters']
    results = service.try_robustness(embedded, name, params, SEED)
    for method, result in results.items():
        source = embedded[method]['output_image']
        attacked = result['output_image']
        assert np.array_equal(attacked, apply_attack(source, name, params, seed=SEED))
        assert (result['height'], result['width']) == attacked.shape[:2]
        if name not in ('resize', 'crop'):
            assert np.array_equal(attacked[:, :, 3], source[:, :, 3])


@pytest.mark.parametrize('name,key,value', [
    ('jpeg', 'quality', 0), ('jpeg', 'quality', 101), ('jpeg', 'quality', 1.2),
    ('blur', 'kernel_size', 0), ('blur', 'kernel_size', 2), ('blur', 'kernel_size', 53),
    ('resize', 'scale', 0), ('resize', 'scale', 4.1), ('crop', 'fraction', 0),
    ('crop', 'fraction', 1.1), ('contrast', 'alpha', -1), ('gaussian_noise', 'sigma', -1),
    ('salt_pepper', 'amount', -1), ('salt_pepper', 'amount', 1.1),
    *[(n, k, v) for n, k in [('brightness', 'delta'), ('resize', 'scale'),
                           ('crop', 'fraction'), ('contrast', 'alpha'),
                           ('gaussian_noise', 'sigma'), ('salt_pepper', 'amount')]
      for v in [float('nan'), float('inf'), float('-inf')]],
])
def test_invalid_configuration(name, key, value):
    with pytest.raises(ValueError):
        validate_configuration(name, {key: value}, SEED)


@pytest.mark.parametrize('seed', [-1, 1.5, '1.5', float('inf'), True, None])
def test_invalid_seed(seed):
    with pytest.raises(ValueError):
        validate_configuration('gaussian_noise', {'sigma': 1}, seed)


def test_defaults_and_boundaries():
    for name, parameters in DEFAULT_PARAMETERS.items():
        assert parameters == next(l['parameters'] for l in ATTACK_LEVELS if l['name'] == name)
        assert validate_configuration(name, parameters, SEED)[0] == parameters
    assert validate_configuration('blur', {'kernel_size': 1})[0]['kernel_size'] == 1
    assert validate_configuration('blur', {'kernel_size': 51})[0]['kernel_size'] == 51
    assert validate_configuration('resize', {'scale': 4})[0]['scale'] == 4
    assert validate_configuration('none', {}, -1)[1] is None
    with pytest.raises(ValueError):
        validate_configuration('none', {'sigma': 1})


def test_old_history_and_write_failure(comparison):
    service, embedded = comparison
    service.history.path.write_text(json.dumps([{'id': 'old', 'operation': 'embed', 'method': 'PVD'}]))
    assert service.history.get_all()[0]['attack'] is None
    class Broken:
        def add_record(self, record):
            raise OSError('read only')
    service.history = Broken()
    results = service.try_robustness(embedded, 'none', {})
    assert all(r['success'] and r['history_warning'] for r in results.values())
