"""Display-only relative scores; service metrics are never modified."""

import math
import tkinter as tk

METHODS = ('PVD', 'DWT')
GROUPS = ('Capacity', 'PSNR', 'SSIM', 'Recovery')
COLORS = ('#176b78', '#db8732')


def normalized_scores(results):
    """Return plot values or None when a 0–100 score is undefined.

    Positive infinite PSNR is displayed as 100; finite peers as 0 (limit
    convention). An all-zero denominator, negative SSIM, and invalid/missing
    values are N/A. Valid measurements survive a method's extraction failure.
    """
    scores = {method: {} for method in METHODS}
    for group, key in zip(GROUPS[:3], ('capacity_bits', 'psnr', 'ssim')):
        values = {}
        for method in METHODS:
            value = results.get(method, {}).get(key)
            if (isinstance(value, (int, float)) and not isinstance(value, bool)
                    and value >= 0 and (math.isfinite(value) or group == 'PSNR')
                    and (group != 'SSIM' or value <= 1)):
                values[method] = value
        maximum = max(values.values(), default=0)
        for method in METHODS:
            value = values.get(method)
            if value is None or maximum == 0:
                score = None
            elif math.isinf(maximum):
                score = 100.0 if math.isinf(value) else 0.0
            else:
                score = value / maximum * 100
            scores[method][group] = score
    for method in METHODS:
        value = results.get(method, {}).get('ber')
        scores[method]['Recovery'] = (
            (1 - value) * 100
            if isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and 0 <= value <= 1 else None
        )
    return scores


class CompareChart(tk.Canvas):
    def __init__(self, parent):
        super().__init__(parent, height=190, width=460, background='#ffffff',
                         highlightthickness=0)
        self.scores = None
        self.bind('<Configure>', self.redraw)

    def clear(self):
        self.scores = None
        self.delete('all')

    def show(self, results):
        self.scores = normalized_scores(results)
        self.redraw()

    def redraw(self, event=None):
        self.delete('all')
        if self.scores is None:
            return
        width, height = self.winfo_width(), self.winfo_height()
        if width < 100 or height < 120:
            return
        self.create_text(width / 2, 13, text='SO SÁNH CHẤT LƯỢNG NHÚNG',
                         font=('Segoe UI', 10, 'bold'))
        self.create_text(width / 2, 32, text='Điểm chuẩn hóa tương đối (0–100)',
                         font=('Segoe UI', 9))
        left, right, top, bottom = 38, width - 12, 59, height - 63
        for value in (0, 50, 100):
            y = bottom - (bottom - top) * value / 100
            self.create_line(left, y, right, y, fill='#e4e7ec')
            self.create_text(left - 5, y, text=str(value), anchor='e', font=('Segoe UI', 8))
        step = (right - left) / 4
        bar_width = min(28, step * 0.24)
        for index, group in enumerate(GROUPS):
            center = left + step * (index + 0.5)
            self.create_text(center, bottom + 13, text=group,
                             font=('Segoe UI', 9), tags=('group',))
            for offset, method, color in zip((-1, 1), METHODS, COLORS):
                x = center + offset * (bar_width / 2 + 2)
                score = self.scores[method][group]
                y = bottom if score is None else bottom - (bottom - top) * score / 100
                if score is not None:
                    self.create_rectangle(x - bar_width / 2, y, x + bar_width / 2,
                                          bottom, fill=color, outline=color,
                                          tags=('bar', method, group))
                self.create_text(x, y - 9, text='N/A' if score is None else f'{score:.0f}',
                                 font=('Segoe UI', 8), tags=('value', method, group))
        for offset, method, color in zip((-48, 38), METHODS, COLORS):
            x, y = width / 2 + offset, height - 31
            self.create_rectangle(x - 20, y - 5, x - 10, y + 5, fill=color, outline=color)
            self.create_text(x, y, text=method, anchor='w', font=('Segoe UI', 9))
        self.create_text(width / 2, height - 11,
                         text='N/A: không xác định; PSNR ∞: 100, hữu hạn/∞: 0.',
                         font=('Segoe UI', 8), fill='#667085')
