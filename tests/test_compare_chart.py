import copy
import math

import pytest

from gui.compare_chart import normalized_scores


def test_relative_scores_preserve_raw_metrics():
    results = {
        'PVD': dict(capacity_bits=400, psnr=30, ssim=0.8, ber=0.1),
        'DWT': dict(capacity_bits=100, psnr=40, ssim=1, ber=0),
    }
    original = copy.deepcopy(results)
    scores = normalized_scores(results)
    assert scores['PVD'] == dict(Capacity=100, PSNR=75, SSIM=80, Recovery=90)
    assert scores['DWT'] == dict(Capacity=25, PSNR=100, SSIM=100, Recovery=100)
    assert results == original


@pytest.mark.parametrize('value', [None, float('nan'), -1, 'bad', float('-inf')])
def test_invalid_values_are_na(value):
    scores = normalized_scores({'PVD': dict(capacity_bits=value, psnr=value, ssim=value, ber=value)})
    assert all(v is None for group in scores.values() for v in group.values())


@pytest.mark.parametrize('first,second,expected', [
    (0, 0, (None, None)), (0, 10, (0, 100)),
    (math.inf, 40, (100, 0)), (math.inf, math.inf, (100, 100)),
    (None, 40, (None, 100)),
])
def test_psnr_zero_infinity_and_partial(first, second, expected):
    scores = normalized_scores({'PVD': {'psnr': first}, 'DWT': {'psnr': second}})
    assert (scores['PVD']['PSNR'], scores['DWT']['PSNR']) == expected


def test_zero_denominators_and_out_of_range_metrics():
    scores = normalized_scores({'PVD': dict(capacity_bits=0, ssim=0, ber=2),
                                'DWT': dict(capacity_bits=0, ssim=0, ber=math.inf)})
    assert all(v is None for group in scores.values() for v in group.values())
