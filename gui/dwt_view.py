import tkinter as tk
from tkinter import ttk

import numpy as np
from core.dwt import decompose_for_visualization
from gui.common import Preview


class DWTView(tk.Toplevel):
    def __init__(self, parent, image):
        super().__init__(parent)
        self.title('Phân rã DWT — Haar level 1')
        self.geometry('740x640')
        self.previews = []
        ttk.Label(self, text='Haar · Mức 1 · QIM Δ = 18 · Lặp 5',
                  padding=12).pack(fill='x')
        grid = ttk.Frame(self, padding=12)
        grid.pack(fill='both', expand=True)
        grid.columnconfigure((0, 1), weight=1)
        grid.rowconfigure((0, 1), weight=1)
        for index, (name, band) in enumerate(decompose_for_visualization(image).items()):
            label = name + (' — Dải nhúng' if name == 'HH' else '')
            frame = Preview(grid, label, (310, 215))
            frame.grid(row=index // 2, column=index % 2, sticky='nsew', padx=5, pady=5)
            span = float(np.ptp(band))
            pixels = np.full(band.shape, 128, dtype=np.uint8) if span == 0 else np.rint((band - band.min()) / span * 255).astype(np.uint8)
            frame.caption.pack_forget()
            frame.show(pixels)
            self.previews.append(frame)
        ttk.Label(self, text='Các dải được chuẩn hóa riêng, chỉ để minh họa.', padding=10).pack(fill='x')
