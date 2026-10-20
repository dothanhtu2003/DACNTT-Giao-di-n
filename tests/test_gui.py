"""Tk smoke/integration tests: actual widgets, dialogs replaced by test paths."""

import time
import gc
import tkinter as tk

import numpy as np
import pytest
from PIL import Image
from tkinter import ttk

from gui.main_window import MainWindow
from services.stego_service import StegoService
from storage.history_store import HistoryStore


@pytest.fixture
def app(tmp_path):
    try:
        window = MainWindow(StegoService(HistoryStore(tmp_path / 'history.json')))
    except tk.TclError as exc:
        pytest.skip(f'Tk display unavailable: {exc}')
    window.update()
    yield window
    if window.winfo_exists():
        window.close()
    del window
    gc.collect()  # Dispose Tk cycles on the owner thread before another worker starts.


def wait_job(app):
    deadline = time.monotonic() + 15
    while app.busy and time.monotonic() < deadline:
        app.update()
        time.sleep(0.01)
    assert not app.busy, 'GUI service job timed out'
    app.update()


def assert_buttons_visible(tab):
    bottom = tab.winfo_rooty() + tab.winfo_height()
    pending = list(tab.winfo_children())
    while pending:
        widget = pending.pop()
        pending.extend(widget.winfo_children())
        if isinstance(widget, ttk.Button) and widget.winfo_manager():
            if hasattr(tab, 'canvas'):
                assert_scroll_accessible(tab, widget)
                continue
            assert widget.winfo_ismapped(), widget.cget('text')
            assert widget.winfo_rooty() + widget.winfo_height() <= bottom, widget.cget('text')
    if hasattr(tab, 'canvas'):
        tab.canvas.yview_moveto(0)
        tab.app.update()


def assert_scroll_accessible(tab, widget):
    tab.canvas.yview_moveto(0)
    tab.app.update()
    offset = widget.winfo_rooty() - tab.content.winfo_rooty()
    tab.canvas.yview_moveto(offset / tab.content.winfo_height())
    tab.app.update()
    assert widget.winfo_ismapped()
    assert widget.winfo_rooty() >= tab.canvas.winfo_rooty()
    assert widget.winfo_rooty() + widget.winfo_height() <= tab.canvas.winfo_rooty() + tab.canvas.winfo_height()


@pytest.mark.parametrize('method', ['PVD', 'DWT'])
def test_gui_workflow(app, tmp_path, monkeypatch, method):
    cover = tmp_path / 'cover.bmp'
    stego = tmp_path / 'stego.png'
    Image.fromarray(np.full((128, 128, 3), 128, dtype=np.uint8)).save(cover)
    monkeypatch.setattr('gui.common.filedialog.askopenfilename', lambda **kwargs: str(cover))
    monkeypatch.setattr('gui.common.filedialog.asksaveasfilename', lambda **kwargs: str(stego))
    assert [app.notebook.tab(tab, 'text') for tab in app.notebook.tabs()] == [
        'Nhúng dữ liệu', 'Trích xuất dữ liệu', 'So sánh PVD – DWT', 'Lịch sử']
    embed = app.embed_tab
    embed.choose()
    embed.method.set(method)
    embed.message.insert('1.0', 'Kiểm thử 🔐')
    app.update()
    embed.changed()
    embed.check_capacity()
    embed.embed()
    wait_job(app)
    assert embed.result['success']
    assert_buttons_visible(embed)
    embed.save_button.invoke()
    assert stego.exists()
    monkeypatch.setattr('gui.common.filedialog.askopenfilename', lambda **kwargs: str(stego))
    extract = app.extract_tab
    app.notebook.select(extract)
    extract.choose()
    extract.method.set(method)
    extract.extract()
    wait_job(app)
    assert extract.message.get('1.0', 'end-1c') == 'Kiểm thử 🔐'
    assert str(extract.message['state']) == 'disabled'
    assert_buttons_visible(extract)
    extract.copy()
    assert app.clipboard_get() == 'Kiểm thử 🔐'
    app.notebook.select(app.compare_tab)
    compare = app.compare_tab
    monkeypatch.setattr('gui.common.filedialog.askopenfilename', lambda **kwargs: str(cover))
    compare.choose()
    compare.message.insert('1.0', 'Hello')
    compare.compare()
    wait_job(app)
    assert all(result['success'] for result in compare.results.values())
    assert len(compare.table.get_children()) == 9
    assert compare.chart.winfo_ismapped()
    assert len(compare.chart.find_withtag('bar')) == 8
    assert [compare.chart.itemcget(item, 'text') for item in
            compare.chart.find_withtag('group')] == ['Capacity', 'PSNR', 'SSIM', 'Recovery']
    assert_buttons_visible(compare)
    app.notebook.select(app.history_tab)
    app.update()
    assert len(app.history_tab.table.get_children()) >= 5
    first = app.history_tab.table.get_children()[0]
    app.history_tab.table.selection_set(first)
    app.history_tab.detail()
    app.history_tab.delete()
    monkeypatch.setattr('gui.history_tab.messagebox.askyesno', lambda *args, **kwargs: True)
    app.history_tab.clear_all()
    assert not app.history_tab.table.get_children()
    embed.show_dwt()
    app.update()
    assert any(isinstance(widget, tk.Toplevel) for widget in embed.winfo_children())


def test_corrupt_history_and_invalid_input(app, tmp_path, monkeypatch):
    app.service.history.path.write_text('broken')
    app.refresh_history()
    assert not app.history_tab.table.get_children()
    errors = []
    monkeypatch.setattr('gui.common.messagebox.showerror', lambda title, text, **kwargs: errors.append(text))
    jpg = tmp_path / 'cover.jpg'
    Image.fromarray(np.zeros((8, 8), dtype=np.uint8)).save(jpg)
    monkeypatch.setattr('gui.common.filedialog.askopenfilename', lambda **kwargs: str(jpg))
    app.embed_tab.choose()
    assert errors and app.embed_tab.path is None


@pytest.mark.parametrize('message,status', [('Hello', 'success'), ('x' * 150, 'partial')])
def test_compare_chart_layout_and_reset(app, tmp_path, monkeypatch, message, status):
    cover = tmp_path / 'chart.png'
    Image.fromarray(np.full((128, 128, 3), 128, dtype=np.uint8)).save(cover)
    monkeypatch.setattr('gui.common.filedialog.askopenfilename', lambda **kwargs: str(cover))
    tab = app.compare_tab
    app.notebook.select(tab)
    tab.choose()
    tab.message.insert('1.0', message)
    app.update()
    tab.compare()
    wait_job(app)
    assert sum(r['success'] for r in tab.results.values()) == (2 if status == 'success' else 1)
    assert tab.chart.find_withtag('bar')
    for values in tab.chart.scores.values():
        assert all(value is None or 0 <= value <= 100 for value in values.values())
    if status == 'partial':
        assert tab.chart.scores['DWT']['Recovery'] is None
        assert 'N/A' in [tab.chart.itemcget(item, 'text')
                         for item in tab.chart.find_withtag('value')]
    for geometry in ('1180x760', '1000x760', '1400x900'):
        app.geometry(geometry)
        app.update()
        assert_buttons_visible(tab)
        for button in tab.save_buttons.values():
            assert button.winfo_height() >= button.winfo_reqheight()
        for widget in (tab.table, tab.chart, tab.status_label, *tab.previews.values()):
            assert_scroll_accessible(tab, widget)
        tab.canvas.yview_moveto(0)
        app.update()
        assert tab.chart.winfo_rooty() >= tab.table.winfo_rooty() + tab.table.winfo_height()
        assert len(tab.chart.find_withtag('group')) == 4
        assert tab.status_label.winfo_height() >= tab.status_label.winfo_reqheight()
        for item in tab.chart.find_withtag('bar'):
            x1, y1, x2, y2 = tab.chart.coords(item)
            assert 0 <= x1 <= x2 <= tab.chart.winfo_width()
            assert 0 <= y1 <= y2 <= tab.chart.winfo_height()
    tab.message.insert('end', '!')
    app.update()
    assert tab.chart.scores is None and not tab.chart.find_all()
    tab.compare()
    wait_job(app)
    assert tab.chart.find_all()
    tab.compare()
    assert tab.chart.scores is None and not tab.chart.find_all()
    wait_job(app)
    assert tab.chart.find_all()
    tab.choose()
    app.update()
    assert tab.chart.scores is None and not tab.chart.find_all()


def test_compare_chart_infinite_psnr_and_missing_ber(app):
    from services.stego_service import base_result
    tab = app.compare_tab
    app.notebook.select(tab)
    results = {method: base_result('unused', method) for method in ('PVD', 'DWT')}
    results['PVD'].update(capacity_bits=100, psnr=float('inf'), ssim=1, ber=None)
    results['DWT'].update(capacity_bits=50, psnr=40, ssim=0.5, ber=0.25)
    tab.show_result({'status': 'failed', 'results': results})
    app.update()
    assert tab.chart.scores['PVD']['PSNR'] == 100
    assert tab.chart.scores['DWT']['PSNR'] == 0
    assert tab.chart.scores['PVD']['Recovery'] is None
    assert tab.chart.scores['DWT']['Recovery'] == 75
    assert len(tab.chart.find_withtag('bar')) == 7
    assert tab.table.item(tab.table.get_children()[5], 'values')[1] == 'inf'


def prepare_comparison(app, tmp_path, monkeypatch, message='Hello'):
    path = tmp_path / 'robust.png'
    Image.fromarray(np.full((128, 128, 4), 128, dtype=np.uint8)).save(path)
    monkeypatch.setattr('gui.common.filedialog.askopenfilename', lambda **kwargs: str(path))
    tab = app.compare_tab
    app.notebook.select(tab)
    tab.choose()
    tab.message.insert('1.0', message)
    app.update()
    tab.compare()
    assert str(tab.try_button['state']) == 'disabled'
    wait_job(app)
    return tab


@pytest.mark.parametrize('message', ['Hello', 'x' * 150])
def test_robustness_workflow_and_configuration(app, tmp_path, monkeypatch, message):
    from services.robustness import ATTACK_LABELS, DEFAULT_PARAMETERS
    tab = prepare_comparison(app, tmp_path, monkeypatch, message)
    assert str(tab.try_button['state']) == 'normal'
    tab.try_robustness()
    assert str(tab.try_button['state']) == 'disabled'
    wait_job(app)
    assert tab.robustness_results['PVD']['ber'] == 0
    assert tab.robustness_results['DWT']['status'] == ('success' if message == 'Hello' else 'not_tested')
    original = tab.results
    for name, label in ATTACK_LABELS.items():
        tab.attack.set(label)
        app.update()
        assert tab.results is original and not tab.robustness_results
        assert bool(tab.parameter_frame.winfo_manager()) == bool(DEFAULT_PARAMETERS[name])
        assert bool(tab.seed_frame.winfo_manager()) == (name in ('gaussian_noise', 'salt_pepper'))
        tab.try_robustness()
        wait_job(app)
        assert tab.robustness_results['PVD']['output_image'] is not None
        assert all(message not in cell.cget('text') for cell in tab.robustness_cells['PVD'].values())
    tab.parameter.set('.8')
    assert tab.results is original and not tab.robustness_results
    tab.seed.set('42')
    assert tab.results is original
    for geometry in ('1000x760', '1180x760'):
        app.geometry(geometry)
        app.update()
        assert_buttons_visible(tab)
        for widget in (*tab.attacked_previews.values(), tab.parameter_frame):
            assert_scroll_accessible(tab, widget)
    tab.message.insert('end', '!')
    app.update()
    assert not tab.results and str(tab.try_button['state']) == 'disabled'


def test_gui_invalid_parameters_before_worker(app, tmp_path, monkeypatch):
    tab = prepare_comparison(app, tmp_path, monkeypatch)
    errors = []
    monkeypatch.setattr(tab, 'show_error', errors.append)
    monkeypatch.setattr(app, 'run_job', lambda *args: pytest.fail('invalid input started worker'))
    for name, value in [('Làm mờ Gaussian', '53'), ('Thay đổi kích thước', '4.1'),
                        ('Nhiễu Gaussian', 'nan'), ('Thay đổi độ sáng', 'inf')]:
        tab.attack.set(name)
        tab.parameter.set(value)
        tab.try_robustness()
    tab.attack.set('Nhiễu muối tiêu')
    tab.seed.set('-1')
    tab.try_robustness()
    assert len(errors) == 5


@pytest.mark.parametrize('change', ['attack', 'parameter', 'seed', 'message', 'image', 'compare'])
def test_stale_robustness_token_and_captured_history(app, tmp_path, monkeypatch, change):
    tab = prepare_comparison(app, tmp_path, monkeypatch)
    tab.attack.set('Nhiễu Gaussian')
    pending = []
    # Hold delivery, allowing the UI to change away and back before completion.
    monkeypatch.setattr(app, 'run_job', lambda work, done: pending.append((work, done)))
    tab.try_robustness()
    token = tab.version
    if change == 'attack':
        tab.attack.set('Không tác động')
        tab.attack.set('Nhiễu Gaussian')
    elif change == 'parameter':
        tab.parameter.set('8')
        tab.parameter.set('1.0')
    elif change == 'seed':
        seed = tab.seed.get()
        tab.seed.set('42')
        tab.seed.set(seed)
    elif change == 'message':
        tab.message.insert('end', '!')
        app.update()
        tab.message.delete('end-2c', 'end-1c')
        app.update()
    elif change == 'image':
        tab.choose()
    else:
        tab.compare()
    assert tab.version > token
    work, done = pending[0]
    results = work()
    done(results)
    assert not tab.robustness_results
    records = [r for r in app.service.history.get_all() if r['operation'] == 'robustness']
    assert len(records) == 2 and all(r['attack'] == 'gaussian_noise' for r in records)
    assert all(r['attack_parameters'] == '{"sigma":1.0}' for r in records)


def test_stale_compare_token_and_restart(app, tmp_path, monkeypatch):
    tab = prepare_comparison(app, tmp_path, monkeypatch)
    pending = []
    monkeypatch.setattr(app, 'run_job', lambda work, done: pending.append((work, done)))
    tab.compare()
    assert not tab.results and not tab.robustness_results
    assert all(str(b['state']) == 'disabled' for b in tab.save_buttons.values())
    tab.compare()
    pending[0][1](pending[0][0]())
    assert not tab.results
    pending[1][1](pending[1][0]())
    assert tab.results
    tab.compare()
    tab.attack.set('Nén JPEG')
    tab.attack.set('Không tác động')
    pending[2][1](pending[2][0]())
    assert not tab.results


def test_robustness_busy_worker_and_warning(app, tmp_path, monkeypatch):
    import threading
    tab = prepare_comparison(app, tmp_path, monkeypatch)
    owner = threading.get_ident()
    original = app.service.try_robustness
    def work(*args):
        assert threading.get_ident() != owner
        results = original(*args)
        for result in results.values():
            result['history_warning'] = 'Không ghi được lịch sử'
        return results
    monkeypatch.setattr(app.service, 'try_robustness', work)
    app.busy = True  # A job on any tab disables robustness.
    tab.update_busy()
    assert str(tab.try_button['state']) == 'disabled'
    tab.try_robustness()
    assert not tab.robustness_results
    app.busy = False
    tab.update_busy()
    tab.try_robustness()
    wait_job(app)
    assert all(r['success'] for r in tab.robustness_results.values())
    assert 'Không ghi được lịch sử' in app.status.get()
    assert all('Không ghi được lịch sử' in cells['notes'].cget('text')
               for cells in tab.robustness_cells.values())


def robustness_result(**changes):
    result = dict(attack='none', attack_parameters='{}', seed=None, width=128,
                  height=128, ber=0.0, success=True, status='success', error=None,
                  output_image=np.full((128, 128, 3), 128, dtype=np.uint8))
    result.update(changes)
    return result


def test_robustness_table_structure_and_states(app):
    from gui.compare_tab import ROBUSTNESS_ROWS, RESULT_COLORS
    from tkinter.font import Font
    tab = app.compare_tab
    assert [title for title, key in ROBUSTNESS_ROWS] == [
        'Tác động và tham số', 'Seed', 'Kích thước ảnh sau tác động',
        'BER sau tác động', 'Khôi phục toàn bộ packet', 'Nguyên nhân / ghi chú']
    assert set(tab.robustness_cells) == {'PVD', 'DWT'}
    assert set(tab.robustness_headers) == {'Chỉ số', 'PVD', 'DWT'}
    for method, cells in tab.robustness_cells.items():
        assert list(cells) == [key for title, key in ROBUSTNESS_ROWS]
        assert all(cell.cget('text') == 'Chưa thử' for cell in cells.values())
    tab.show_robustness_result('PVD', robustness_result(history_warning='Không ghi được lịch sử'))
    tab.show_robustness_result('DWT', robustness_result(
        status='extraction_failed', success=False, ber=None, error='LENGTH sai',
        history_warning='Cảnh báo lịch sử'))
    for method, text, state in [('PVD', 'Khôi phục đúng', 'success'),
                                ('DWT', 'Thất bại', 'failure')]:
        cell = tab.robustness_cells[method]['recovery']
        assert cell.cget('text') == text
        assert str(cell.cget('foreground')) == RESULT_COLORS[state]
        assert Font(app, font=cell.cget('font')).actual('weight') == 'bold'
        assert tab.robustness_cells[method]['seed'].cget('text') == 'Không dùng'
    cells = tab.robustness_cells['DWT']
    assert cells['ber'].cget('text') == 'Không xác định'
    assert str(cells['ber'].cget('foreground')) == RESULT_COLORS['muted']
    assert cells['notes'].cget('text') == 'LENGTH sai\nCảnh báo lịch sử'
    assert tab.robustness_cells['PVD']['notes'].cget('text') == 'Không ghi được lịch sử'
    tab.show_robustness_result('DWT', robustness_result(
        status='not_tested', success=False, output_image=None, width=None, height=None,
        ber=None, attack='resize', attack_parameters='{"scale":0.5}',
        error='Không thử được — nhúng thất bại'))
    assert cells['attack'].cget('text') == 'Thay đổi kích thước\nTỷ lệ mỗi chiều: 0.5'
    assert cells['recovery'].cget('text') == 'Không thử được'
    assert str(cells['recovery'].cget('foreground')) == RESULT_COLORS['muted']
    assert cells['notes'].cget('text') == 'Nhúng thất bại'
    assert all(cells[key].cget('text') == '—' for key in ('seed', 'dimensions', 'ber'))
    assert tab.attacked_previews['DWT'].photo is None
    assert tab.attacked_previews['DWT'].image_label.cget('text') == 'Không thử được'
    tab.show_robustness_result('PVD', robustness_result())
    assert tab.robustness_cells['PVD']['notes'].cget('text') == '—'
    tab.clear_robustness()
    for method, cells in tab.robustness_cells.items():
        for cell in cells.values():
            assert cell.cget('text') == 'Chưa thử'
            assert str(cell.cget('foreground')) == RESULT_COLORS['neutral']
            assert Font(app, font=cell.cget('font')).actual('weight') == 'normal'
        preview = tab.attacked_previews[method]
        assert preview.photo is None and not preview.image_label.cget('image')
        assert preview.image_label.cget('text') == 'Chưa thử'


def test_robustness_wrapping_alignment_and_thumbnails(app):
    tab = app.compare_tab
    app.notebook.select(tab)
    app.geometry('1000x760')
    note = 'Ghi chú dài cần xuống dòng và giữ toàn bộ nội dung trong cột. ' * 12
    images = {'PVD': np.full((800, 40, 3), 128, dtype=np.uint8),
              'DWT': np.full((40, 800, 3), 128, dtype=np.uint8)}
    for method, image in images.items():
        tab.show_robustness_result(method, robustness_result(
            attack='crop', attack_parameters='{"fraction":0.5}', output_image=image,
            width=image.shape[1], height=image.shape[0], error=note if method == 'PVD' else None))
    app.update()
    for method, image in images.items():
        preview = tab.attacked_previews[method]
        assert max(preview.photo.width(), preview.photo.height()) <= 150
        assert min(preview.photo.width(), preview.photo.height()) < 20
        assert preview.photo.width() / preview.photo.height() == pytest.approx(
            image.shape[1] / image.shape[0], rel=.1)
        assert tab.robustness_cells[method]['dimensions'].cget('text') == f'{image.shape[1]} × {image.shape[0]}'
        column = 1 if method == 'PVD' else 2
        assert int(preview.grid_info()['column']) == column
        header = tab.robustness_headers[method]
        assert preview.master is tab.robustness_grid
        for cell in tab.robustness_cells[method].values():
            assert int(cell.grid_info()['column']) == column
            assert cell.winfo_x() == header.winfo_x() - 6
            assert int(cell.cget('wraplength')) <= cell.winfo_width() - 12
    for key in tab.robustness_row_labels:
        pvd, dwt = (tab.robustness_cells[m][key] for m in ('PVD', 'DWT'))
        assert pvd.winfo_y() == dwt.winfo_y()
        assert pvd.winfo_height() == dwt.winfo_height()
        assert pvd.winfo_width() == dwt.winfo_width()
        assert str(pvd.cget('anchor')) == 'nw'
        assert_scroll_accessible(tab, pvd)
        assert pvd.winfo_x() + pvd.winfo_width() <= dwt.winfo_x()
    assert tab.robustness_cells['PVD']['notes'].winfo_height() > 100
    previous_wrap = int(tab.robustness_cells['PVD']['notes'].cget('wraplength'))
    app.geometry('1400x900')
    app.update()
    assert int(tab.robustness_cells['PVD']['notes'].cget('wraplength')) > previous_wrap


def prepare_batch(app, tmp_path):
    source = tmp_path / 'covers'
    source.mkdir()
    Image.fromarray(np.full((80, 80), 128, dtype=np.uint8)).save(source / 'gray.png')
    Image.fromarray(np.full((80, 80, 3), 128, dtype=np.uint8)).save(source / 'color.bmp')
    (source / 'bad.png').write_text('unreadable')
    tab = app.compare_tab
    app.notebook.select(tab)
    app.geometry('1000x760')
    tab.mode.set('Bộ ảnh')
    tab.mode_changed()
    panel = tab.batch_panel
    panel.source.set(str(source))
    panel.destination.set(str(tmp_path / 'results'))
    panel.payloads.set('0, 8')
    panel.seeds.set('7,8,7')
    for name, (_, enabled, values) in panel.attacks.items():
        enabled.set(name in ('brightness', 'gaussian_noise'))
        if name == 'brightness':
            values.set('0,1')
        elif name == 'gaussian_noise':
            values.set('0,1')
    app.update()
    return tab, panel


def test_batch_gui_real_worker_table_and_four_tabs(app, tmp_path, monkeypatch):
    import threading
    tab, panel = prepare_batch(app, tmp_path)
    assert len(app.notebook.tabs()) == 4
    owner = threading.get_ident()
    original = app.service.run_batch
    def work(*args):
        assert threading.get_ident() != owner
        return original(*args)
    monkeypatch.setattr(app.service, 'run_batch', work)
    captured = panel.inspect()
    assert len(captured[0]) == 2 and captured[1]['seeds'] == [7, 8]
    assert '56' in panel.plan.cget('text')
    assert len(panel.inventory.get_children()) == 3
    panel.start()
    assert app.busy and str(panel.run_button['state']) == 'disabled'
    assert str(tab.try_button['state']) == 'disabled'
    panel.start()  # Busy must prevent a second batch.
    wait_job(app)
    assert not panel.active and panel.result['completed_cases'] == 56
    assert len(app.service.history.get_all()) == 1
    assert panel.table.get_children()
    panel.common.set(True)
    panel.show_summary()
    assert len(panel.table.get_children()) == 20
    assert not panel.config_expanded
    time.sleep(.12)
    app.update()  # A queued worker progress event must not replace the completion caption.
    assert float(panel.progress['value']) == float(panel.progress['maximum'])
    assert '56 ca đã chạy; 0 ca không chạy do baseline' in panel.progress_text.cget('text')
    # No whole-page scrolling is needed for results or persistent actions.
    for widget in (panel.run_button, panel.cancel_button, panel.open_button, panel.table):
        app.update()
        assert widget.winfo_ismapped()
        assert widget.winfo_rooty() >= panel.winfo_rooty()
        assert widget.winfo_rooty() + widget.winfo_height() <= panel.winfo_rooty() + panel.winfo_height()
    panel.table.xview_moveto(1)
    app.update()
    assert panel.table.xview()[1] == 1
    from pathlib import Path
    from PIL import ImageGrab
    artifacts = Path(__file__).parent / 'artifacts'
    artifacts.mkdir(exist_ok=True)
    ImageGrab.grab(bbox=(app.winfo_rootx(), app.winfo_rooty(), app.winfo_rootx() + app.winfo_width(),
                         app.winfo_rooty() + app.winfo_height())).save(artifacts / 'gui_batch_summary_1000x760.png')
    tab.mode.set('Một ảnh')
    tab.mode_changed()
    app.update()
    assert tab.content.winfo_ismapped()


def test_batch_gui_cancel_token_and_snapshot(app, tmp_path, monkeypatch):
    tab, panel = prepare_batch(app, tmp_path)
    original = app.service.run_batch
    pending = []
    monkeypatch.setattr(app, 'run_job', lambda work, done, failed: pending.append((work, done)))
    panel.start()
    captured_seed = panel.seeds.get()
    panel.cancel()  # Cancellation before the worker starts is cooperative too.
    work, done = pending.pop()
    result = work()
    done(result)
    assert result['status'] == 'cancelled' and result['completed_cases'] == 0
    assert 'Đã hủy — kết quả chưa đầy đủ' in panel.progress_text.cget('text')
    assert all(r['pooled_success_rate'] is None for r in result['summary'])
    panel.start()
    work, done = pending.pop()
    panel.seeds.set('99')
    result = work()
    done(result)
    assert panel.result is None  # Old results cannot replace the changed selection.
    assert {r['seed'] for r in result['rows'] if r['attack'] == 'gaussian_noise'} == {7, 8}
    assert captured_seed == '7,8,7'
    assert str(panel.open_button['state']) == 'disabled'


def test_batch_gui_failure_resets_activity(app, tmp_path, monkeypatch):
    tab, panel = prepare_batch(app, tmp_path)
    monkeypatch.setattr('gui.main_window.messagebox.showerror', lambda *args, **kwargs: None)
    def fail(*args):
        raise OSError('Output unavailable')
    monkeypatch.setattr(app.service, 'run_batch', fail)
    panel.start()
    wait_job(app)
    assert not panel.active and panel.result is None
    assert str(panel.run_button['state']) == 'normal'
    assert str(panel.cancel_button['state']) == 'disabled'
