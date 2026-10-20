from copy import deepcopy
import json
from pathlib import Path

import pytest
from PIL import Image
from matplotlib.colors import to_rgba

from gui.batch_chart import prepare_charts, chart_figure, save_png, attack_label, run_config, chart_display_groups
from gui.batch_panel import ALL_SCOPE
from tests.test_gui import app
from tests.test_batch_ui import panel_for, result_fixture, capture


def test_snapshot_values_zero_na_payloads_and_numeric_order():
    result = result_fixture()
    rows = [r for r in result['summary'] if r['scope'] == 'common' and r['attack'] == 'gaussian_noise']
    for r in rows:
        r['image_success_mean'] = None if json.loads(r['attack_parameter'])['sigma'] == .1 else 0
    original = deepcopy(rows)
    plots = prepare_charts(rows, result, {'Tác động': 'Nhiễu Gaussian'}, {'seeds': [7, 8]})
    assert [p['payload'] for p in plots] == [2, 10]
    assert [g['label'] for g in plots[0]['groups']] == ['Gaussian σ=0,1', 'Gaussian σ=2', 'Gaussian σ=10']
    assert plots[0]['groups'][0]['values'] == {'PVD': None, 'DWT': None}
    assert plots[0]['groups'][1]['values'] == {'PVD': 0, 'DWT': 0}
    assert '7, 8' in plots[0]['seed_note']
    assert rows == original
    rows[0]['image_success_mean'] = 1
    assert plots[0]['groups'][2]['values']['DWT'] == 0  # Snapshot survives subsequent changes.


def test_image_counts_filter_scope_and_percent_not_relative():
    result = result_fixture()
    rows = [r for r in result['summary'] if r['scope'] == 'all' and r['payload_bytes'] == 10 and r['attack'] == 'jpeg']
    rows[0]['image_success_mean'] = .8
    plots = prepare_charts(rows, result, {'Tập': ALL_SCOPE})
    assert len(plots) == 1
    assert plots[0]['scope'] == 'all' and 'khác nhau' in plots[0]['scope_note']
    assert {g['images']['PVD'] for g in plots[0]['groups']} == {4}
    assert {g['images']['DWT'] for g in plots[0]['groups']} == {3}
    assert plots[0]['groups'][2]['values']['DWT'] == 80
    assert plots[0]['groups'][2]['values']['PVD'] == 25
    assert not plots[0]['seed_note']  # Never guess seeds from completed_cases.
    single = prepare_charts([r for r in rows if r['method'] == 'DWT'], result, {})
    assert single[0]['methods'] == ['DWT']
    with pytest.raises(ValueError, match='all hoặc common'):
        prepare_charts(result['summary'], result, {})


@pytest.mark.parametrize('status,incomplete', [('cancelled', False), ('failed', False), ('completed', True)])
def test_incomplete_warning_and_png(status, incomplete, tmp_path):
    result = result_fixture() | {'status': status, 'incomplete': incomplete, 'run_id': 'run-test'}
    rows = [r for r in result['summary'] if r['scope'] == 'common' and r['attack'] == 'jpeg' and r['payload_bytes'] == 2]
    rows[0]['image_success_mean'] = None
    rows[1]['image_success_mean'] = 0
    plots = prepare_charts(rows, result, {'Tác động': 'Nén JPEG'})
    fig = chart_figure(plots[0])
    assert fig.axes[0].get_ylim() == (0, 100)
    handles = fig.axes[0].get_legend().legend_handles
    assert [h.get_facecolor() for h in handles] == [to_rgba('#176b78'), to_rgba('#db8732')]
    texts = [t.get_text() for t in fig.texts] + [t.get_text() for t in fig.axes[0].texts]
    assert any('KẾT QUẢ CHƯA ĐẦY ĐỦ' in t for t in texts)
    assert 'Không xác định' in texts and '0%' in texts
    output = tmp_path / 'chart.png'
    save_png(fig, output)
    with Image.open(output) as image:
        assert image.format == 'PNG' and image.width > 1000 and image.height > 700
    fig.clear()


def test_long_names_partition_all_zero_and_labels(tmp_path):
    result = result_fixture() | {'run_id': 'example-run', 'status': 'cancelled'}
    rows = [r for r in result['summary'] if r['scope'] == 'common']
    for r in rows:
        r['image_success_mean'] = 0
    rows[0]['attack_parameter'] = json.dumps({'delta': 10, 'ghi_chu': 'Tên tham số dài cần đọc toàn bộ ' * 4}, ensure_ascii=False)
    plots = prepare_charts(rows, result, {'Tác động': 'Tất cả'})
    assert len(plots) == 2
    assert sum(len(p['groups']) for p in plots) == 19  # Long parameter becomes a distinct group; no merging.
    assert attack_label('salt_pepper', '{"amount":0.01}') == 'Muối tiêu 1%'
    assert attack_label('contrast', '{"alpha":0.9}') == 'Tương phản ×0,9'
    assert attack_label('jpeg', '{"quality":90}') == 'JPEG Q90'
    assert attack_label('gaussian_noise', '{"sigma":1}') == 'Gaussian σ=1'
    long_plot = next(p for p in plots if any('ghi_chu' in g['label'] for g in p['groups']))
    fig = chart_figure(long_plot)
    labels = '\n'.join(t.get_text() for t in [*fig.axes[0].get_xticklabels(), *fig.texts])
    assert 'Tên tham số dài' in labels.replace('\n', ' ')
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    # All text is included within the padded figure; save uses tight bounds as well.
    for text in [*fig.texts, *fig.axes[0].get_xticklabels()]:
        box = text.get_window_extent(renderer)
        assert box.y0 >= -1 and box.y1 <= fig.bbox.height + 1
        assert box.x0 >= -1 and box.x1 <= fig.bbox.width + 1
    folder = Path(__file__).parent / 'artifacts'
    folder.mkdir(exist_ok=True)
    save_png(fig, folder / 'batch_chart_long_zero_incomplete.png')
    fig.clear()


def test_zero_groups_compact_only_in_chart_preserve_na_counts_and_snapshot(tmp_path):
    result = result_fixture()
    rows = [r for r in result['summary'] if r['scope'] == 'all' and r['payload_bytes'] == 2 and r['attack'] == 'jpeg']
    for row in rows:
        row['image_success_mean'] = 0
    plot = prepare_charts(rows, result, {})[0]
    plot['groups'][1]['values']['DWT'] = None
    plot['groups'][2]['values']['PVD'] = 50
    plot['groups'][0]['images']['PVD'] = 9
    original = deepcopy(plot)
    visible, zero = chart_display_groups(plot)
    assert len(visible) == 2 and len(zero) == 1
    assert visible[0]['values']['DWT'] is None
    fig = chart_figure(plot)
    assert len(fig.axes[0].get_xticks()) == 2
    texts = '\n'.join(t.get_text() for t in [*fig.texts, *fig.axes[0].texts])
    assert 'Tất cả đều 0%' in texts and zero[0]['label'] in texts
    assert 'PVD: 9 ảnh' in texts and 'DWT: 3 ảnh' in texts
    assert 'Không xác định' in texts and '0%' in texts
    assert plot == original
    fig.clear()
    single = deepcopy(plot) | {'methods': ['PVD']}
    assert len(chart_display_groups(single)[1]) == 2
    # A missing method is not evidence that both methods achieved zero.
    del plot['groups'][0]['values']['DWT']
    assert not chart_display_groups(plot)[1]
    for group in plot['groups']:
        group['values'] = {'PVD': 0, 'DWT': 0}
    fig = chart_figure(plot)
    assert not len(fig.axes[0].get_xticks()) and not fig.axes[0].patches
    assert any('Tất cả cấu hình đang chọn đều 0%' in t.get_text() for t in fig.axes[0].texts)
    save_png(fig, tmp_path / 'all-zero.png')
    with Image.open(tmp_path / 'all-zero.png') as image:
        assert image.format == 'PNG'
    fig.clear()


def test_optional_config_read_does_not_guess_or_write(tmp_path):
    path = tmp_path / 'config.json'
    data = {'run_id': 'r1', 'config': {'seeds': [11, 12]}}
    path.write_text(json.dumps(data), encoding='utf-8')
    before = path.read_bytes()
    assert run_config({'run_id': 'r1', 'output_dir': str(tmp_path)}) == data['config']
    assert run_config({'run_id': 'other', 'output_dir': str(tmp_path)}) == {}
    assert run_config({'completed_cases': 500}) == {}
    assert path.read_bytes() == before


def test_chart_button_window_snapshot_filters_export_no_runner(app, monkeypatch, tmp_path):
    panel = panel_for(app)
    assert str(panel.chart_button['state']) == 'disabled'
    result = result_fixture() | {'run_id': 'gui-run', 'config': {'seeds': [7, 8]}, 'status': 'cancelled'}
    panel.present_result(result)
    panel.filter_scope.set(ALL_SCOPE)
    panel.filter_payload.set('10')
    panel.filter_attack.set('Nén JPEG')
    panel.filter_method.set('DWT')
    original = deepcopy(result)
    monkeypatch.setattr(app.service, 'run_batch', lambda *args: pytest.fail('Chart called experiments'))
    monkeypatch.setattr(app.service.history, 'add_record', lambda *args: pytest.fail('Chart wrote history'))
    monkeypatch.setattr('experiments.batch_runner.run_batch', lambda *args: pytest.fail('Chart called runner'))
    assert str(panel.chart_button['state']) == 'normal'
    window = panel.show_chart()
    try:
        assert len(app.notebook.tabs()) == 4 and not app.busy
        assert len(window.plots) == 1 and window.plots[0]['methods'] == ['DWT']
        assert window.plots[0]['scope'] == 'all' and window.plots[0]['payload'] == 10
        assert window.plots[0]['filters']['Tác động'] == 'Nén JPEG'
        panel.filter_payload.set('2')
        assert window.plots[0]['payload'] == 10
        assert result == original
        assert not list(tmp_path.glob('*.png'))  # Opening does not automatically export.
        def choose_file(**kwargs):
            assert kwargs['initialfile'] == 'gui-run_all_payload_10_jpeg_1.png'
            return str(tmp_path / 'saved.png')
        monkeypatch.setattr('gui.batch_chart.filedialog.asksaveasfilename', choose_file)
        window.choose_save(0)
        assert (tmp_path / 'saved.png').exists()
        capture(window, 'gui_batch_chart_window_1000x760.png')
        save_png(window.figures[0], Path(__file__).parent / 'artifacts' / 'batch_chart_na_zero.png')
    finally:
        window.close()
    # Exercise the real scrollable window with several payloads/attacks and zero/NA groups.
    many = result_fixture() | {'run_id': 'many-groups', 'status': 'cancelled', 'config': {'seeds': [7, 8]}}
    for row in many['summary']:
        row['image_success_mean'] = None if row['attack'] == 'gaussian_noise' else 0
    panel.filter_method.set('Tất cả')
    panel.filter_payload.set('Tất cả')
    panel.filter_attack.set('Tất cả')
    panel.filter_scope.set('Baseline chung PVD/DWT')
    panel.present_result(many)
    window = panel.show_chart()
    try:
        assert len(window.plots) == 2
        assert {p['payload'] for p in window.plots} == {2, 10}
        capture(window, 'gui_batch_chart_many_zero_1000x760.png')
        window.scroll_canvas.yview_moveto(1)
        app.update()
        assert window.scroll_canvas.yview()[1] == 1.0
        save_png(window.figures[0], Path(__file__).parent / 'artifacts' / 'batch_chart_all_zero.png')
        save_png(window.figures[1], Path(__file__).parent / 'artifacts' / 'batch_chart_all_na.png')
    finally:
        window.close()
    panel.filter_payload.set('999')
    assert str(panel.chart_button['state']) == 'disabled' and panel.show_chart() is None
