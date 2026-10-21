import tkinter as tk
from tkinter import ttk

from gui.common import BaseTab, Preview, message_editor, method_selector, format_value


class EmbedTab(BaseTab):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.method = tk.StringVar(value='PVD')
        self.result = None
        self.columnconfigure(0, weight=1, uniform='halves')
        self.columnconfigure(1, weight=1, uniform='halves')
        self.rowconfigure(0, weight=1)
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 16))
        self.cover_preview = Preview(left, 'Ảnh gốc', (360, 145))
        self.cover_preview.pack(fill='both', expand=True)
        ttk.Button(left, text='Chọn ảnh PNG/BMP', command=self.choose).pack(anchor='w', pady=8)
        self.stego_preview = Preview(left, 'Ảnh sau nhúng', (360, 145))
        self.stego_preview.pack(fill='both', expand=True)
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky='nsew')
        method_selector(right, self.method, self.changed).pack(anchor='w', pady=(0, 12))
        ttk.Label(right, text='Văn bản bí mật').pack(anchor='w')
        frame, self.message = message_editor(right, height=3)
        frame.pack(fill='both', expand=True, pady=(6, 10))
        self.message.bind('<<Modified>>', self.message_changed)
        self.metric_text = tk.StringVar(value='Chọn ảnh để xem dung lượng.')
        ttk.Label(right, textvariable=self.metric_text, justify='left', wraplength=470).pack(fill='x', pady=6)
        actions = ttk.Frame(right)
        actions.pack(fill='x', pady=8)
        ttk.Button(actions, text='Nhúng dữ liệu', style='Accent.TButton', command=self.embed).pack(side='left')
        self.result_text = tk.StringVar()
        ttk.Label(right, textvariable=self.result_text, wraplength=470).pack(fill='x', pady=8)
        self.save_button = ttk.Button(right, text='Lưu Stego PNG', state='disabled', command=lambda: self.save_result(self.result))
        self.save_button.pack(anchor='w')
        self.dwt_button = ttk.Button(right, text='Xem phân rã DWT', command=self.show_dwt)

    def choose(self):
        self.choose_image(self.cover_preview, self.changed)

    def changed(self):
        self.result = None
        self.save_button.configure(state='disabled')
        self.stego_preview.clear()
        self.result_text.set('')
        if self.method.get() == 'DWT':
            self.dwt_button.pack(anchor='w', pady=(10, 0))
        else:
            self.dwt_button.pack_forget()
        self.check_capacity()

    def message_changed(self, event=None):
        if self.message.edit_modified():
            self.message.edit_modified(False)
            self.changed()

    def text(self):
        return self.message.get('1.0', 'end-1c')

    def check_capacity(self):
        if self.path is None:
            return
        try:
            from services.stego_service import engine_for
            from metrics.metrics import payload_metrics
            metrics = payload_metrics(len(self.text().encode('utf-8')),
                                      engine_for(self.method.get()).calculate_capacity(self.image),
                                      self.image.shape[1], self.image.shape[0])
            usage = format_value(metrics['usage_percent'])
            self.metric_text.set(f'Dung lượng: {metrics["capacity_bits"]:,} bits · Văn bản: {metrics["payload_bytes"]} byte\n'
                                 f'Đã dùng: {metrics["packet_bits"]:,} bits ({usage}%) · '
                                 + ('Đủ dung lượng.' if metrics['packet_bits'] <= metrics['capacity_bits'] else 'Không đủ dung lượng.'))
        except ValueError as exc:
            self.metric_text.set(f'Không thể kiểm tra dung lượng: {exc}')

    def embed(self):
        if not self.require_image():
            return
        path, message, method = self.path, self.text(), self.method.get()
        service = self.app.service
        def completed(result):
            if (self.path, self.text(), self.method.get()) != (path, message, method):
                self.app.set_status('Tác vụ đã hoàn tất cho dữ liệu trước đó. Hãy nhúng lại lựa chọn hiện tại.')
                return
            self.show_result(result)
        self.app.run_job(lambda: service.embed(path, message, method), completed)

    def show_result(self, result):
        self.result = result
        self.save_button.configure(state='normal' if result['success'] else 'disabled')
        if result['output_image'] is not None:
            self.stego_preview.show(result['output_image'], result['method'] + ' · PNG')
        else:
            self.stego_preview.clear()
        if result['success']:
            self.result_text.set(f'Khôi phục dữ liệu khớp 100%.\nPSNR: {format_value(result["psnr"])} dB · SSIM: {format_value(result["ssim"])} · bpp: {result["bpp"]:.6f}')
            self.app.set_status(result.get('history_warning', 'Nhúng thành công.'))
        else:
            self.result_text.set(result['error'])
            self.app.set_status('Nhúng không thành công: ' + result['error'])

    def show_dwt(self):
        if self.require_image():
            from gui.dwt_view import DWTView
            DWTView(self, self.image)
