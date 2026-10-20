"""Presentation-only tests against deliberately unordered, independently supplied rows."""

from copy import deepcopy
import json
from pathlib import Path
import tkinter as tk
import time

import pytest
from PIL import ImageGrab

from gui.batch_panel import (ALL, ALL_SCOPE, COMMON_SCOPE, SUMMARY_COLUMNS,
                             completed_caption, detail_text, display_number)
from tests.test_gui import app, wait_job  # Shared actual Tk fixture; no runner changes.


def result_fixture():
    rows = []
    for scope in ('all', 'common'):
        for payload in (10, 2):
            for method in ('DWT', 'PVD'):
                for attack, key, levels in [('brightness', 'delta', [10, 2, -10]),
                                            ('gaussian_noise', 'sigma', [10, 2, .1]),
                                            ('jpeg', 'quality', [90, 10, 2])]:
                    for level in levels:
                        rows.append(dict(scope=scope, method=method, payload_bytes=payload,
                            attack=attack, attack_parameter=json.dumps({key: level}),
                            expected_images=5, eligible_images=(2 if payload == 2 else 1) if scope == 'common' else (4 if method == 'PVD' else 3),
                            baseline_valid=4 if method == 'PVD' else 3,
                            baseline_capacity=1, baseline_embed_io_error=0, baseline_mismatch=0 if method == 'PVD' else 1,
                            baseline_unprocessed=0, completed_cases=10, success_cases=5,
                            pooled_success_rate=.5, image_success_mean=.25, image_success_std=.46291,
                            image_ber_mean=None if attack == 'gaussian_noise' else .125,
                            ber_valid_cases=0 if attack == 'gaussian_noise' else 8,
                            ber_na_cases=10 if attack == 'gaussian_noise' else 2,
                            ber_contributing_images=0 if attack == 'gaussian_noise' else 2,
                            ber_no_valid_images=2 if attack == 'gaussian_noise' else 0))
    return dict(status='completed', counts={'images': 5, 'embeddings': 20, 'cases': 200}, completed_cases=190,
                baselines=[dict(image_id=i, method=m, payload_bytes=p, baseline_status='mismatch' if i == 4 and m == 'DWT' and p == 10 else 'valid')
                           for i in range(5) for m in ('PVD', 'DWT') for p in (2, 10)],
                output_dir='E:/Kết quả thử giao diện/' + 'thư mục dài ' * 15, summary=rows)


def panel_for(app):
    tab = app.compare_tab
    app.notebook.select(tab)
    app.geometry('1000x760')
    tab.mode.set('Bộ ảnh')
    tab.mode_changed()
    app.update()
    return tab.batch_panel


def capture(window, name):
    window.update()
    window.lift()
    time.sleep(.35)  # Let Windows finish its window transition before the screenshot.
    window.update()
    folder = Path(__file__).parent / 'artifacts'
    folder.mkdir(exist_ok=True)
    ImageGrab.grab(bbox=(window.winfo_rootx(), window.winfo_rooty(), window.winfo_rootx() + window.winfo_width(),
                         window.winfo_rooty() + window.winfo_height())).save(folder / name)


def test_columns_layout_collapse_and_zoom(app):
    panel = panel_for(app)
    panel.payloads.set('2,10')
    panel.seeds.set('7,8')
    before = (panel.payloads.get(), panel.seeds.get(), panel.capture_config())
    panel.present_result(result_fixture())
    app.update()
    assert not panel.config_expanded and not app.compare_tab.canvas.winfo_ismapped()
    assert list(panel.table['columns']) == [k for k, _ in SUMMARY_COLUMNS]
    assert len(SUMMARY_COLUMNS) == 8
    for key, title in SUMMARY_COLUMNS:
        assert panel.heading_font.measure(title) + 8 <= int(panel.table.column(key, 'width'))
    assert sum(int(panel.table.column(key, 'width')) for key, _ in SUMMARY_COLUMNS) <= panel.table.winfo_width()
    assert panel.table.xview() == (0.0, 1.0)
    small_height = panel.table.winfo_height()
    for widget in (panel.run_button, panel.cancel_button, panel.table, panel.detail_button, panel.open_button):
        assert widget.winfo_rooty() >= panel.winfo_rooty()
        assert widget.winfo_rooty() + widget.winfo_height() <= panel.winfo_rooty() + panel.winfo_height()
    capture(app, 'gui_batch_collapsed_1000x760.png')
    panel.toggle_config()
    app.update()
    assert panel.config_expanded
    assert (panel.payloads.get(), panel.seeds.get(), panel.capture_config()) == before
    assert panel.result is not None
    for widget in (panel.run_button, panel.cancel_button, panel.progress, panel.open_button):
        assert widget.winfo_rooty() + widget.winfo_height() <= panel.winfo_rooty() + panel.winfo_height()
    panel.toggle_config()
    app.geometry('1400x900')
    app.update()
    assert panel.table.winfo_height() > small_height
    assert panel.table.xview() == (0.0, 1.0)
    capture(app, 'gui_batch_results_1400x900.png')


def test_filters_numeric_order_and_data_unchanged(app):
    panel = panel_for(app)
    result = result_fixture()
    original = deepcopy(result)
    panel.present_result(result)
    app.update()
    assert panel.common.get() and panel.filter_scope.get() == COMMON_SCOPE
    assert tuple(panel.filters['payload']['values']) == (ALL, '2', '10')
    rows = [panel.row_data[i] for i in panel.table.get_children()]
    assert [r['payload_bytes'] for r in rows[:18]] == [2] * 18
    for a, b in zip(rows[::2], rows[1::2]):
        assert (a['method'], b['method']) == ('PVD', 'DWT')
        assert (a['payload_bytes'], a['attack'], a['attack_parameter']) == (b['payload_bytes'], b['attack'], b['attack_parameter'])
    gaussian = [json.loads(r['attack_parameter'])['sigma'] for r in rows if r['payload_bytes'] == 2 and r['attack'] == 'gaussian_noise' and r['method'] == 'PVD']
    brightness = [json.loads(r['attack_parameter'])['delta'] for r in rows if r['payload_bytes'] == 2 and r['attack'] == 'brightness' and r['method'] == 'PVD']
    assert gaussian == [.1, 2, 10] and brightness == [-10, 2, 10]
    panel.filter_method.set('DWT')
    panel.filter_payload.set('10')
    panel.filter_attack.set('Thay đổi độ sáng')
    assert len(panel.row_data) == 3
    assert all(r['method'] == 'DWT' and r['payload_bytes'] == 10 and r['attack'] == 'brightness'
               and r['scope'] == 'common' and r['eligible_images'] == 1 for r in panel.row_data.values())
    panel.filter_scope.set(ALL_SCOPE)
    assert all(r['scope'] == 'all' and r['eligible_images'] == 3 for r in panel.row_data.values())
    panel.filter_payload.set('999')  # Defensive empty state for a stale/unsupported selection.
    assert not panel.table.get_children() and 'không có dòng phù hợp' in panel.row_count.cget('text')
    assert result == original  # Includes original ordering; CSV/export data is untouched.
    assert 'Đang hiển thị: Toàn bộ ảnh có baseline hợp lệ của từng phương pháp' == panel.scope_label.cget('text')
    assert '5' not in panel.scope_label.cget('text')


def test_detail_long_parameter_na_and_units(app):
    panel = panel_for(app)
    result = result_fixture()
    target = next(r for r in result['summary'] if r['scope'] == 'common' and r['attack'] == 'gaussian_noise')
    target['attack_parameter'] = json.dumps({'sigma': 2, 'ghi_chu': 'Tham số rất dài cần xem đầy đủ ' * 10}, ensure_ascii=False)
    target['image_ber_mean'] = None
    panel.present_result(result)
    app.update()
    iid = next(i for i, r in panel.row_data.items() if r is target)
    panel.table.selection_set(iid)
    panel.table.see(iid)
    app.update()
    values = panel.table.item(iid, 'values')
    assert '…' in values[3]
    assert values[5] == '25.00%' and values[6] == 'NA'
    assert '46,291 điểm phần trăm' in detail_text(target, result)
    assert '0.46291%' not in detail_text(target, result)
    assert display_number(.125) == '0.125000'
    assert display_number(None, sd=True) == 'NA'
    window = panel.show_detail()
    try:
        assert window.detail_text.get('1.0', 'end-1c') == detail_text(target, result)
        assert target['attack_parameter'] in window.detail_text.get('1.0', 'end-1c')
        assert 'TOÀN TẬP DỰ KIẾN' in window.detail_text.get('1.0', 'end-1c')
        assert result['output_dir'] in window.detail_text.get('1.0', 'end-1c')
        assert window.detail_text['wrap'] == 'word'
        capture(window, 'gui_batch_detail_1000x760.png')
        assert window.detail_scroll.winfo_ismapped() and window.detail_scroll.winfo_width() > 0
        window.detail_text.yview_moveto(1)
        window.update()
        assert window.detail_text.yview()[1] == 1.0
    finally:
        window.destroy()
    capture(app, 'gui_batch_long_parameters_1000x760.png')
    missing = detail_text({'scope': 'common'}, {})
    assert 'Tổng số ảnh dự kiến: Thiếu dữ liệu' in missing


def test_completed_cancelled_failed_and_no_false_baseline_attribution(app):
    panel = panel_for(app)
    result = result_fixture()
    result['completed_cases'] = 190
    assert '10 ca không chạy do baseline' in completed_caption(result)
    panel.present_result(result)
    assert float(panel.progress['value']) == float(panel.progress['maximum'])
    result = deepcopy(result)
    result['completed_cases'] = 180
    assert 'Chênh lệch khác: 10 ca; chưa xác định nguyên nhân' in completed_caption(result)
    del result['baselines']
    assert 'thiếu dữ liệu' in completed_caption(result)
    result['status'] = 'cancelled'
    panel.present_result(result)
    assert float(panel.progress['value']) == 180 and float(panel.progress['maximum']) == 200
    assert 'Đã hủy — kết quả chưa đầy đủ' in panel.progress_text.cget('text')
    capture(app, 'gui_batch_cancelled_1000x760.png')
    result['status'] = 'failed'
    panel.present_result(result)
    assert 'Lỗi lần chạy' in panel.progress_text.cget('text') and 'chưa đầy đủ' in panel.progress_text.cget('text')
    assert float(panel.progress['value']) == 180
