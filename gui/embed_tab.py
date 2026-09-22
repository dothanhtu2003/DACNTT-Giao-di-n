import tkinter as tk
from tkinter import ttk, messagebox

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
        ttk.Label(right, text='Văn bản bí mật (UTF-8)').pack(anchor='w')
        frame, self.message = message_editor(right, height=3)
        frame.pack(fill='both', expand=True, pady=(6, 10))
        self.message.bind('<<Modified>>', self.message_changed)
        self.metric_text = tk.StringVar(value='Chọn ảnh và nhập văn bản để kiểm tra dung lượng.')
        ttk.Label(right, textvariable=self.metric_text, justify='left', wraplength=470).pack(fill='x', pady=6)
        actions = ttk.Frame(right)
        actions.pack(fill='x', pady=8)
        ttk.Button(actions, text='Kiểm tra dung lượng', command=self.check_capacity).pack(side='left')
        ttk.Button(actions, text='Nhúng dữ liệu', style='Accent.TButton', command=self.embed).pack(side='left', padx=8)
        self.result_text = tk.StringVar(value='Chưa có kết quả nhúng.')
        ttk.Label(right, textvariable=self.result_text, wraplength=470).pack(fill='x', pady=8)
        self.save_button = ttk.Button(right, text='Lưu Stego PNG', state='disabled', command=lambda: self.save_result(self.result))
        self.save_button.pack(anchor='w')
        config = ttk.Frame(right)
        config.pack(fill='x', pady=(10, 0))
        ttk.Button(config, text='Xem cấu hình', command=self.show_config).pack(side='left')
        self.dwt_button = ttk.Button(config, text='Xem phân rã DWT', command=self.show_dwt)

    def choose(self):
        self.choose_image(self.cover_preview, self.changed)

    def changed(self):
        self.result = None
        self.save_button.configure(state='disabled')
        self.stego_preview.clear()
        self.result_text.set('Chưa có kết quả nhúng cho lựa chọn hiện tại.')
        if self.method.get() == 'DWT':
            self.dwt_button.pack(side='left', padx=8)
        else:
            self.dwt_button.pack_forget()
        self.check_capacity(silent=True)

    def message_changed(self, event=None):
        if self.message.edit_modified():
            self.message.edit_modified(False)
            self.changed()

    def text(self):
        return self.message.get('1.0', 'end-1c')

    def check_capacity(self, silent=False):
        if self.path is None:
            if not silent:
                self.require_image()
            return
        try:
            from services.stego_service import engine_for
            from metrics.metrics import payload_metrics
            metrics = payload_metrics(len(self.text().encode('utf-8')),
                                      engine_for(self.method.get()).calculate_capacity(self.image),
                                      self.image.shape[1], self.image.shape[0])
            usage = format_value(metrics['usage_percent'])
            self.metric_text.set(f'Payload: {metrics["payload_bytes"]} bytes  ·  Packet: {metrics["packet_bits"]} bits\n'
                                 f'Capacity: {metrics["capacity_bits"]:,} bits  ·  Usage: {usage}%\n'
                                 f'bpp: {metrics["bpp"]:.6f} (bao gồm LENGTH)')
            if not silent:
                self.app.set_status('Đủ dung lượng.' if metrics['packet_bits'] <= metrics['capacity_bits'] else 'Không đủ dung lượng.')
        except ValueError as exc:
            if not silent:
                self.show_error(str(exc))

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
            self.stego_preview.show(result['output_image'], result['method'] + ' · PNG lossless')
        else:
            self.stego_preview.clear()
        if result['success']:
            self.result_text.set(f'Đã nhúng và kiểm tra trích xuất khớp 100%.\nPSNR: {format_value(result["psnr"])} dB  ·  SSIM: {format_value(result["ssim"])}\n'
                                 f'bpp: {result["bpp"]:.6f}  ·  Capacity: {result["capacity_bits"]:,} bits  ·  Payload: {result["payload_bytes"]} bytes')
            self.app.set_status(result.get('history_warning', 'Nhúng thành công. Có thể lưu ảnh PNG.'))
        else:
            self.result_text.set(result['error'])
            self.app.set_status('Nhúng không thành công: ' + result['error'])

    def show_config(self):
        messagebox.showinfo('Cấu hình cố định',
                            'PVD: Blue / intensity; raster; cặp ngang không chồng lấp.\n'
                            'Khoảng: 0–7 / 8–15 / 16–31 / 32–63 / 64–127 / 128–255.\n'
                            'Bit: 3 / 3 / 4 / 5 / 6 / 7.\n\n'
                            'DWT: Y / intensity; Haar; level 1; HH; Delta 18; repeat 5; majority vote 3/5.\n\n'
                            'Packet: LENGTH 32-bit big-endian + UTF-8.\nVăn bản rỗng được phép (packet 32 bit).', parent=self)

    def show_dwt(self):
        if self.require_image():
            from gui.dwt_view import DWTView
            DWTView(self, self.image)
