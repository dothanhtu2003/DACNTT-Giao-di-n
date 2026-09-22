import tkinter as tk
from tkinter import ttk

import numpy as np
from PIL import Image, ImageTk

from core.dwt import decompose_for_visualization


class DWTView(tk.Toplevel):
    def __init__(self, parent, image):
        super().__init__(parent)
        self.title('Phân rã DWT — Haar level 1')
        self.geometry('740x640')
        self.photos = []
        ttk.Label(self, text='Wavelet: Haar  ·  Level: 1  ·  Band: HH  ·  QIM Delta: 18  ·  Repetition: 5',
                  padding=12).pack(fill='x')
        grid = ttk.Frame(self, padding=12)
        grid.pack(fill='both', expand=True)
        grid.columnconfigure((0, 1), weight=1)
        grid.rowconfigure((0, 1), weight=1)
        for index, (name, band) in enumerate(decompose_for_visualization(image).items()):
            label = name + (' — Dải được sử dụng để nhúng dữ liệu' if name == 'HH' else '')
            frame = ttk.LabelFrame(grid, text=label, padding=8)
            frame.grid(row=index // 2, column=index % 2, sticky='nsew', padx=5, pady=5)
            span = float(np.ptp(band))
            pixels = np.full(band.shape, 128, dtype=np.uint8) if span == 0 else np.rint((band - band.min()) / span * 255).astype(np.uint8)
            display = Image.fromarray(pixels)
            display.thumbnail((310, 215), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(display)
            self.photos.append(photo)
            ttk.Label(frame, image=photo, anchor='center').pack(fill='both', expand=True)
        ttk.Label(self, text='Mỗi dải được chuẩn hóa riêng để hiển thị; không dùng ảnh này để nhúng.', padding=10).pack(fill='x')
