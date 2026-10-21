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
    assert 'Dung lượng:' in embed.metric_text.get()
    assert 'Văn bản: 0 byte' in embed.metric_text.get()
    embed.method.set(method)
    embed.message.insert('1.0', 'Kiểm thử 🔐')
    app.update()
    assert f'Văn bản: {len("Kiểm thử 🔐".encode("utf-8"))} byte' in embed.metric_text.get()
    embed.changed()
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
    wait_job(app)
    return tab


def test_stale_compare_token_and_restart(app, tmp_path, monkeypatch):
    tab = prepare_comparison(app, tmp_path, monkeypatch)
    pending = []
    monkeypatch.setattr(app, 'run_job', lambda work, done: pending.append((work, done)))
    tab.compare()
    assert not tab.results
    assert all(str(b['state']) == 'disabled' for b in tab.save_buttons.values())
    tab.compare()
    pending[0][1](pending[0][0]())
    assert not tab.results
    pending[1][1](pending[1][0]())
    assert tab.results
    tab.compare()
    tab.mode.set('Bộ ảnh')
    tab.mode_changed()
    tab.mode.set('Một ảnh')
    tab.mode_changed()
    pending[2][1](pending[2][0]())
    assert not tab.results


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
    assert len(panel.entries) == 3
    panel.start()
    assert app.busy and str(panel.run_button['state']) == 'disabled'
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
    assert '2 ảnh chạy thành công · 0 ảnh thất bại' in panel.progress_text.cget('text')
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
