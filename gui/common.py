"""Shared Tk widgets; all Tk calls remain on the GUI thread."""

from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import ImageTk

from core.image_utils import load_image, image_info, create_thumbnail

IMAGE_TYPES = [('Ảnh PNG / BMP', '*.png *.bmp')]


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
        self.image_label = ttk.Label(self, text='Chưa chọn ảnh', anchor='center')
        self.caption = ttk.Label(self, text='', anchor='center', wraplength=size[0])
        self.caption.pack(side='bottom', fill='x', pady=(8, 0))
        self.image_label.pack(fill='both', expand=True)

    def show(self, image, caption=''):
        self.photo = ImageTk.PhotoImage(create_thumbnail(image, self.size))
        self.image_label.configure(image=self.photo, text='')
        self.caption.configure(text=caption)

    def clear(self, text='Chưa có ảnh'):
        self.photo = None
        self.image_label.configure(image='', text=text)
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
