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
            assert widget.winfo_ismapped(), widget.cget('text')
            assert widget.winfo_rooty() + widget.winfo_height() <= bottom, widget.cget('text')


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
