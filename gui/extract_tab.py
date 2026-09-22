import tkinter as tk
from tkinter import ttk

from gui.common import BaseTab, Preview, method_selector, message_editor


class ExtractTab(BaseTab):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.method = tk.StringVar(value='PVD')
        self.columnconfigure((0, 1), weight=1)
        self.rowconfigure(0, weight=1)
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 18))
        self.preview = Preview(left, 'Ảnh Stego', (440, 390))
        self.preview.pack(fill='both', expand=True)
        ttk.Button(left, text='Chọn ảnh PNG/BMP', command=self.choose).pack(anchor='w', pady=12)
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky='nsew')
        method_selector(right, self.method, self.clear).pack(anchor='w', pady=(0, 12))
        ttk.Button(right, text='Trích xuất dữ liệu', style='Accent.TButton', command=self.extract).pack(anchor='w')
        ttk.Label(right, text='Văn bản trích xuất').pack(anchor='w', pady=(20, 6))
        frame, self.message = message_editor(right, height=7)
        frame.pack(fill='both', expand=True)
        self.message.configure(state='disabled')
        self.copy_button = ttk.Button(right, text='Copy', state='disabled', command=self.copy)
        self.copy_button.pack(anchor='w', pady=10)
        self.result_status = tk.StringVar(value='Chọn đúng phương pháp đã dùng khi nhúng.')
        ttk.Label(right, textvariable=self.result_status, wraplength=480).pack(fill='x')

    def choose(self):
        self.choose_image(self.preview, self.clear)

    def clear(self):
        self.message.configure(state='normal')
        self.message.delete('1.0', 'end')
        self.message.configure(state='disabled')
        self.copy_button.configure(state='disabled')
        self.result_status.set('Sẵn sàng trích xuất.')

    def extract(self):
        if not self.require_image():
            return
        self.clear()
        path, method = self.path, self.method.get()
        service = self.app.service
        def completed(result):
            if (self.path, self.method.get()) != (path, method):
                self.app.set_status('Tác vụ đã hoàn tất cho ảnh trước đó. Hãy trích xuất lại lựa chọn hiện tại.')
                return
            self.show_result(result)
        self.app.run_job(lambda: service.extract(path, method), completed)

    def show_result(self, result):
        self.clear()
        if result['success']:
            self.message.configure(state='normal')
            self.message.insert('1.0', result['message'])
            self.message.configure(state='disabled')
            self.copy_button.configure(state='normal')
            self.result_status.set(f'Thành công · LENGTH hợp lệ · UTF-8 hợp lệ · {result["payload_bytes"]} bytes.\n'
                                   'Packet không có checksum; không xác thực được nguồn gốc chỉ từ LENGTH/UTF-8.')
        else:
            self.result_status.set(result['error'])
        self.app.set_status(result.get('history_warning', self.result_status.get()))

    def copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.message.get('1.0', 'end-1c'))
        self.app.set_status('Đã sao chép văn bản.')
