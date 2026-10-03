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
        assert message not in tab.robustness_text['PVD'].get()
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
    assert all('Không ghi được lịch sử' in v.get() for v in tab.robustness_text.values())
