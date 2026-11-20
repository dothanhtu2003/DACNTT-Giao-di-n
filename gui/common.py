"""Shared Tk widgets; all Tk calls remain on the GUI thread."""

from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageTk

from core.image_utils import load_image, image_info

IMAGE_TYPES = [('Ảnh PNG / BMP', '*.png *.bmp')]


def format_status(value):
    return {
        'success': 'Thành công', 'failed': 'Thất bại',
        'partial': 'Thành công một phần', 'extraction_failed': 'Trích xuất lỗi',
        'not_checked': 'Chưa kiểm tra', 'not_tested': 'Chưa thử',
        'integrity_verified': 'Khớp 100%', 'valid_length_utf8': 'Đọc được văn bản',
        'completed': 'Hoàn tất', 'cancelled': 'Đã hủy',
    }.get(value, format_value(value))


def show_help(parent, title, body):
    window = tk.Toplevel(parent)
    window.title(title)
    window.transient(parent.winfo_toplevel())
    window.geometry('660x480')
    window.minsize(420, 300)
    frame = ttk.Frame(window, padding=16)
    frame.pack(fill='both', expand=True)
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(0, weight=1)
    text = tk.Text(frame, wrap='word', font=('Segoe UI', 10), padx=10, pady=10)
    scroll = ttk.Scrollbar(frame, command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    text.grid(row=0, column=0, sticky='nsew')
    scroll.grid(row=0, column=1, sticky='ns')
    text.insert('1.0', body)
    text.configure(state='disabled')
    ttk.Button(frame, text='Đóng', command=window.destroy).grid(row=1, column=0, columnspan=2, pady=(12, 0))
    return window


def format_value(value):
    if value is None:
        return '—'
    if isinstance(value, float):
        return f'{value:,.4f}'
    return str(value)


class Preview(ttk.LabelFrame):
    def __init__(self, parent, title, size=(330, 220)):
        super().__init__(parent, text=title, padding=10)
        self.size = size
        self.photo = None
        self._source = None
        self._original = None
        self._resize_job = None
        self._rendered_size = None
        self._viewer = None
        # Keep the requested layout independent of the displayed bitmap size.
        self.viewport = ttk.Frame(self, width=size[0], height=size[1])
        self.viewport.pack_propagate(False)
        self.image_label = ttk.Label(self.viewport, text='Chưa chọn ảnh', anchor='center')
        self.caption = ttk.Label(self, text='', anchor='center', wraplength=size[0])
        self.caption.pack(side='bottom', fill='x', pady=(8, 0))
        self.viewport.pack(fill='both', expand=True)
        self.image_label.pack(fill='both', expand=True)
        self.image_label.bind('<Button-1>', self.open_viewer)
        self.viewport.bind('<Configure>', self._queue_resize)
        self.bind('<Destroy>', self._cancel_resize, add='+')

    def show(self, image, caption='', original=None):
        self._close_viewer()
        self._cancel_resize()
        self._source = Image.fromarray(image).copy()
        self._original = Image.fromarray(original).copy() if original is not None else None
        self._rendered_size = None
        self.caption.configure(text=caption)
        self.image_label.configure(cursor='hand2')
        self._render()

    def open_viewer(self, event=None):
        if self._source is None:
            return
        if self._viewer is not None and self._viewer.winfo_exists():
            self._viewer.lift()
            return self._viewer
        from gui.image_view import ImageView
        self._viewer = ImageView(self, self._source, self.cget('text'), original=self._original)
        return self._viewer

    def _close_viewer(self):
        if self._viewer is not None and self._viewer.winfo_exists():
            self._viewer.destroy()
        self._viewer = None

    def _queue_resize(self, event):
        self.caption.configure(wraplength=max(1, event.width))
        self._cancel_resize()
        self._resize_job = self.after(60, self._render)

    def _cancel_resize(self, event=None):
        if event is not None and event.widget is not self:
            return
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
            self._resize_job = None

    def _render(self):
        self._resize_job = None
        if self._source is None:
            return
        width, height = self.viewport.winfo_width(), self.viewport.winfo_height()
        if width <= 1 or height <= 1:
            return
        scale = min(width / self._source.width, height / self._source.height)
        size = (max(1, int(self._source.width * scale)),
                max(1, int(self._source.height * scale)))
        if size == self._rendered_size:
            return
        self.photo = ImageTk.PhotoImage(
            self._source.resize(size, Image.Resampling.LANCZOS), master=self)
        self.image_label.configure(image=self.photo, text='')
        self._rendered_size = size

    def clear(self, text='Chưa có ảnh'):
        self._close_viewer()
        self._cancel_resize()
        self._source = None
        self._original = None
        self._rendered_size = None
        self.photo = None
        self.image_label.configure(image='', text=text, cursor='')
        self.caption.configure(text='')


class BaseTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        self.app = app
        self.path = None
        self.image = None

    def choose_image(self, preview, callback=None):
        path = filedialog.askopenfilename(parent=self, title='Chọn ảnh PNG/BMP', filetypes=IMAGE_TYPES)
        if not path:
            return
        try:
            image = load_image(path)
            info = image_info(image)
            self.path, self.image = path, image
            preview.show(image, f'{Path(path).name} · {info["width"]} × {info["height"]} · {info["mode"]}')
            self.app.set_status('Đã chọn ' + Path(path).name)
            if callback:
                callback()
        except (OSError, ValueError) as exc:
            self.show_error(str(exc))

    def show_error(self, error):
        self.app.set_status(error)
        messagebox.showerror('Không thể thực hiện', error, parent=self)

    def require_image(self):
        if self.path is None:
            self.show_error('Hãy chọn ảnh PNG/BMP trước.')
            return False
        return True

    def save_result(self, result):
        if self.app.busy:
            self.app.set_status('Vui lòng đợi tác vụ hiện tại hoàn tất trước khi lưu.')
            return
        if not result or not result['success']:
            self.show_error('Chưa có kết quả nhúng thành công.')
            return
        path = filedialog.asksaveasfilename(parent=self, title='Lưu ảnh Stego PNG',
                                          defaultextension='.png', filetypes=[('PNG lossless', '*.png')],
                                          initialfile=f'stego_{result["method"].lower()}.png')
        if path:
            try:
                self.app.service.save(result, path)
                self.app.set_status('Đã lưu PNG: ' + path)
                self.app.refresh_history()
            except (OSError, ValueError) as exc:
                self.show_error(str(exc))


def message_editor(parent, height=7):
    frame = ttk.Frame(parent)
    text = tk.Text(frame, height=height, width=36, wrap='word', font=('Segoe UI', 11),
                   relief='solid', borderwidth=1, padx=10, pady=10, undo=True)
    scrollbar = ttk.Scrollbar(frame, orient='vertical', command=text.yview)
    text.configure(yscrollcommand=scrollbar.set)
    text.pack(side='left', fill='both', expand=True)
    scrollbar.pack(side='right', fill='y')
    return frame, text


def method_selector(parent, variable, command=None):
    frame = ttk.Frame(parent)
    ttk.Label(frame, text='Phương pháp:').pack(side='left', padx=(0, 12))
    for method in ('PVD', 'DWT'):
        ttk.Radiobutton(frame, text=method, value=method, variable=variable, command=command).pack(side='left', padx=8)
    return frame
