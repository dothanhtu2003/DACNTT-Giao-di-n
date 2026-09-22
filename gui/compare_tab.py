from tkinter import ttk

from gui.common import BaseTab, Preview, message_editor, format_value

ROWS = [('Capacity bits', 'capacity_bits'), ('Payload bytes', 'payload_bytes'),
        ('Packet bits', 'packet_bits'), ('Usage %', 'usage_percent'), ('bpp', 'bpp'),
        ('PSNR (dB)', 'psnr'), ('SSIM', 'ssim'), ('BER', 'ber'), ('Extract status', 'extract_status')]


class CompareTab(BaseTab):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.results = {}
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=3)
        self.rowconfigure(0, weight=1)
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 18))
        self.preview = Preview(left, 'Cùng ảnh nguồn', (320, 155))
        self.preview.pack(fill='both', expand=True)
        ttk.Button(left, text='Chọn ảnh PNG/BMP', command=self.choose).pack(anchor='w', pady=8)
        ttk.Label(left, text='Cùng văn bản UTF-8').pack(anchor='w')
        frame, self.message = message_editor(left, height=3)
        frame.pack(fill='both', expand=True, pady=8)
        self.message.bind('<<Modified>>', self.message_changed)
        ttk.Button(left, text='Chạy so sánh', style='Accent.TButton', command=self.compare).pack(anchor='w')
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky='nsew')
        self.table = ttk.Treeview(right, columns=('metric', 'PVD', 'DWT'), show='headings', height=9, style='Compare.Treeview')
        for key, width in [('metric', 135), ('PVD', 165), ('DWT', 165)]:
            self.table.heading(key, text='Tiêu chí' if key == 'metric' else key)
            self.table.column(key, width=width, minwidth=90, anchor='w')
        self.table.pack(fill='x')
        preview_row = ttk.Frame(right)
        preview_row.pack(fill='both', expand=True, pady=(12, 0))
        self.previews, self.save_buttons = {}, {}
        for method in ('PVD', 'DWT'):
            column = ttk.Frame(preview_row)
            column.pack(side='left', fill='both', expand=True, padx=3)
            self.previews[method] = Preview(column, method + ' Stego', (230, 100))
            self.previews[method].pack(fill='both', expand=True)
            button = ttk.Button(column, text=f'Lưu {method} PNG', state='disabled',
                                command=lambda m=method: self.save_result(self.results.get(m)))
            button.pack(side='bottom', pady=8, before=self.previews[method])
            self.save_buttons[method] = button
        self.status_label = ttk.Label(right, text='Hai phương pháp chạy độc lập.', wraplength=550)
        self.status_label.pack(side='bottom', fill='x', before=preview_row)

    def choose(self):
        self.choose_image(self.preview, self.clear)

    def clear(self):
        self.results = {}
        self.table.delete(*self.table.get_children())
        for method in ('PVD', 'DWT'):
            self.previews[method].clear()
            self.save_buttons[method].configure(state='disabled')
        self.status_label.configure(text='Hai phương pháp chạy độc lập.')

    def message_changed(self, event=None):
        if self.message.edit_modified():
            self.message.edit_modified(False)
            self.clear()

    def compare(self):
        if not self.require_image():
            return
        path, message = self.path, self.message.get('1.0', 'end-1c')
        service = self.app.service
        def completed(result):
            if (self.path, self.message.get('1.0', 'end-1c')) != (path, message):
                self.app.set_status('Tác vụ đã hoàn tất cho dữ liệu trước đó. Hãy chạy lại so sánh.')
                return
            self.show_result(result)
        self.app.run_job(lambda: service.compare(path, message), completed)

    def show_result(self, comparison):
        self.results = comparison['results']
        self.table.delete(*self.table.get_children())
        for label, key in ROWS:
            self.table.insert('', 'end', values=(label, *(format_value(self.results[m].get(key)) for m in ('PVD', 'DWT'))))
        errors = []
        for method, result in self.results.items():
            self.save_buttons[method].configure(state='normal' if result['success'] else 'disabled')
            if result['output_image'] is not None:
                self.previews[method].show(result['output_image'])
            else:
                self.previews[method].clear()
            if result['error']:
                errors.append(method + ': ' + result['error'])
        text = {'success': 'Cả hai phương pháp trích xuất khớp dữ liệu gốc.',
                'partial': 'Partial · Chỉ một phương pháp thành công.',
                'failed': 'Cả hai phương pháp chưa thành công.'}[comparison['status']]
        self.status_label.configure(text=text + ('\n' + '\n'.join(errors) if errors else ''))
        self.app.set_status(text)
