import tkinter as tk
from tkinter import ttk, messagebox

from gui.common import BaseTab, format_value

COLUMNS = [('timestamp', 'Thời gian', 180), ('operation', 'Thao tác', 125),
           ('method', 'Phương pháp', 90), ('input_filename', 'Ảnh', 160),
           ('payload_bytes', 'Payload', 75), ('psnr', 'PSNR', 75),
           ('ssim', 'SSIM', 75), ('ber', 'BER', 65), ('status', 'Trạng thái', 130)]


class HistoryTab(BaseTab):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.records = {}
        actions = ttk.Frame(self)
        actions.pack(fill='x', pady=(0, 12))
        for title, command in [('Refresh', self.refresh), ('Xem chi tiết', self.detail),
                               ('Xóa bản ghi', self.delete), ('Xóa tất cả', self.clear_all)]:
            ttk.Button(actions, text=title, command=command).pack(side='left', padx=(0, 8))
        container = ttk.Frame(self)
        container.pack(fill='both', expand=True)
        self.table = ttk.Treeview(container, columns=[item[0] for item in COLUMNS], show='headings', selectmode='browse')
        for key, title, width in COLUMNS:
            self.table.heading(key, text=title)
            self.table.column(key, width=width, minwidth=60)
        vertical = ttk.Scrollbar(container, orient='vertical', command=self.table.yview)
        horizontal = ttk.Scrollbar(container, orient='horizontal', command=self.table.xview)
        self.table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.table.grid(row=0, column=0, sticky='nsew')
        vertical.grid(row=0, column=1, sticky='ns')
        horizontal.grid(row=1, column=0, sticky='ew')
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        self.table.bind('<Double-1>', lambda event: self.detail())
        ttk.Label(self, text='Lịch sử chỉ lưu metadata. Không lưu văn bản bí mật, nội dung trích xuất hoặc raw payload.').pack(anchor='w', pady=(12, 0))

    def refresh(self):
        # Avoid concurrent read-modify-write while a service job logs its result.
        if self.app.busy:
            return
        try:
            records = self.app.service.history.get_all()
            self.table.delete(*self.table.get_children())
            self.records = {}
            for index, record in enumerate(reversed(records)):
                iid = str(index)
                self.records[iid] = record
                operations = {'embed': 'Nhúng', 'extract': 'Trích xuất', 'compare': 'So sánh',
                              'save': 'Lưu Stego', 'robustness': 'Thử độ bền'}
                self.table.insert('', 'end', iid=iid, values=[
                    operations.get(record.get(key), record.get(key)) if key == 'operation'
                    else format_value(record.get(key)) for key, _, _ in COLUMNS])
        except OSError as exc:
            self.app.set_status('Không đọc được lịch sử: ' + str(exc))

    def selected(self):
        selection = self.table.selection()
        return self.records.get(selection[0]) if selection else None

    def detail(self):
        record = self.selected()
        if record is None:
            self.app.set_status('Hãy chọn một bản ghi.')
            return
        window = tk.Toplevel(self)
        window.title('Chi tiết metadata')
        window.geometry('620x560')
        text = tk.Text(window, wrap='word', font=('Segoe UI', 10), padx=18, pady=18)
        text.pack(fill='both', expand=True)
        text.insert('1.0', '\n'.join(f'{key}: {format_value(value)}' for key, value in record.items()))
        text.configure(state='disabled')

    def delete(self):
        if self.app.busy:
            return
        record = self.selected()
        if record:
            try:
                self.app.service.history.delete_record(record['id'])
                self.refresh()
            except OSError as exc:
                self.show_error(str(exc))

    def clear_all(self):
        if self.app.busy:
            return
        if messagebox.askyesno('Xóa lịch sử', 'Xóa tất cả bản ghi metadata?', parent=self):
            try:
                self.app.service.history.clear()
                self.refresh()
            except OSError as exc:
                self.show_error(str(exc))
