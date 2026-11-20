"""Large image viewer with fit, zoom and drag-to-pan controls."""

import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk


class ImageView(tk.Toplevel):
    def __init__(self, parent, image, title='Xem ảnh', original=None):
        super().__init__(parent)
        self.title('So sánh trước / sau nhúng — ' + title if original is not None else title)
        self.geometry(f'{min(1200, self.winfo_screenwidth() - 80)}x'
                      f'{min(850, self.winfo_screenheight() - 100)}')
        self.minsize(480, 360)
        self.source = image.copy()
        self.sources = [original.copy(), self.source] if original is not None else [self.source]
        self.canvases, self.items, self.photos = [], [], []
        self.photo = None
        self.scale = 1.0
        self.fit_mode = True
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill='x')
        for label, command in [('−', lambda: self.zoom(1 / 1.25)),
                               ('+', lambda: self.zoom(1.25)),
                               ('100%', self.actual_size),
                               ('Vừa cửa sổ', self.fit)]:
            ttk.Button(toolbar, text=label, command=command).pack(side='left', padx=3)
        self.info = ttk.Label(toolbar)
        self.info.pack(side='left', padx=12)
        ttk.Button(toolbar, text='Đóng (Esc)', command=self.destroy).pack(side='right')
        ttk.Label(self, text='Cuộn chuột để phóng to/thu nhỏ · Giữ và kéo ảnh để di chuyển',
                  padding=(12, 4)).pack(side='bottom', fill='x')
        frame = ttk.Frame(self)
        frame.pack(fill='both', expand=True)
        frame.rowconfigure(0, weight=1)
        for index in range(len(self.sources)):
            frame.columnconfigure(index, weight=1, uniform='images')
            panel = ttk.Frame(frame, padding=4)
            panel.grid(row=0, column=index, sticky='nsew')
            panel.columnconfigure(0, weight=1)
            panel.rowconfigure(1, weight=1)
            if original is not None:
                ttk.Label(panel, text='Trước khi nhúng (ảnh gốc)' if index == 0 else
                          'Sau khi nhúng — ' + title, anchor='center',
                          padding=8).grid(row=0, column=0, columnspan=2, sticky='ew')
            canvas = tk.Canvas(panel, background='#20252b', highlightthickness=0,
                               cursor='fleur')
            canvas.grid(row=1, column=0, sticky='nsew')
            horizontal = ttk.Scrollbar(panel, orient='horizontal',
                                       command=lambda *args: self._scroll('x', *args))
            vertical = ttk.Scrollbar(panel, orient='vertical',
                                     command=lambda *args: self._scroll('y', *args))
            horizontal.grid(row=2, column=0, sticky='ew')
            vertical.grid(row=1, column=1, sticky='ns')
            canvas.configure(xscrollcommand=horizontal.set, yscrollcommand=vertical.set)
            self.canvases.append(canvas)
            self.items.append(canvas.create_image(0, 0, anchor='nw'))
            canvas.bind('<Configure>', self._resize)
            canvas.bind('<MouseWheel>', self._wheel)
            canvas.bind('<Button-4>', lambda event: self._wheel(event, 1))
            canvas.bind('<Button-5>', lambda event: self._wheel(event, -1))
            canvas.bind('<ButtonPress-1>', self._pan_start)
            canvas.bind('<B1-Motion>', self._pan_move)
        self.canvas, self.item = self.canvases[-1], self.items[-1]
        self.bind('<Escape>', lambda event: self.destroy())

    def _scroll(self, axis, *args):
        for canvas in self.canvases:
            getattr(canvas, axis + 'view')(*args)

    def _pan_start(self, event):
        for canvas in self.canvases:
            canvas.scan_mark(event.x, event.y)

    def _pan_move(self, event):
        for canvas in self.canvases:
            canvas.scan_dragto(event.x, event.y, gain=1)

    def _resize(self, event):
        if self.fit_mode:
            self.fit()
        else:
            self._layout()

    def fit(self):
        self.fit_mode = True
        self.scale = min(min(max(1, canvas.winfo_width()) / source.width,
                             max(1, canvas.winfo_height()) / source.height)
                         for canvas, source in zip(self.canvases, self.sources))
        self._render()

    def actual_size(self):
        self.fit_mode = False
        self.scale = 1.0
        self._render()

    def zoom(self, factor):
        self.fit_mode = False
        self.scale = max(0.05, min(8.0, self.scale * factor))
        self._render()

    def _wheel(self, event, direction=None):
        direction = direction if direction is not None else event.delta
        if direction:
            self.zoom(1.25 if direction > 0 else 1 / 1.25)
        return 'break'

    def _render(self):
        self.photos = []
        for canvas, item, source in zip(self.canvases, self.items, self.sources):
            size = (max(1, round(source.width * self.scale)),
                    max(1, round(source.height * self.scale)))
            photo = ImageTk.PhotoImage(source.resize(size, Image.Resampling.LANCZOS), master=self)
            self.photos.append(photo)
            canvas.itemconfigure(item, image=photo)
        self.photo = self.photos[-1]
        self.info.configure(text=f'{self.scale:.0%} · {self.source.width} × {self.source.height}')
        self._layout()

    def _layout(self):
        if self.photo is None:
            return
        for canvas, item, photo in zip(self.canvases, self.items, self.photos):
            width = max(canvas.winfo_width(), photo.width())
            height = max(canvas.winfo_height(), photo.height())
            canvas.coords(item, (width - photo.width()) / 2, (height - photo.height()) / 2)
            canvas.configure(scrollregion=(0, 0, width, height))

