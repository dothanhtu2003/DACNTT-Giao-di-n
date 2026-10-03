"""Desktop shell with exactly four tabs and background service execution."""

from concurrent.futures import ThreadPoolExecutor
import sys
import tkinter as tk
from tkinter import ttk, messagebox

from services.stego_service import StegoService


class MainWindow(tk.Tk):
    def __init__(self, service=None):
        if sys.platform == 'win32':
            # Keep Tk geometry and screen captures in physical pixels on scaled displays.
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except (AttributeError, OSError):
                pass
        super().__init__()
        self.title('Hệ thống giấu tin trong ảnh số PVD & DWT')
        self.geometry('1180x760')
        self.minsize(1000, 760)
        self.service = service if service is not None else StegoService()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='stego')
        self.busy = False
        self.status = tk.StringVar(value='Sẵn sàng · PNG/BMP đầu vào • PNG đầu ra')
        self._style()
        header = ttk.Frame(self, padding=(22, 16))
        header.pack(fill='x')
        ttk.Label(header, text='GIẤU TIN TRONG ẢNH SỐ', style='Title.TLabel').pack(anchor='w')
        ttk.Label(header, text='PVD & DWT  /  Nhúng, trích xuất và đánh giá chất lượng ảnh',
                  style='Subtitle.TLabel').pack(anchor='w', pady=(4, 0))
        ttk.Label(self, textvariable=self.status, padding=(20, 10), wraplength=1100).pack(side='bottom', fill='x')
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=16)
        from gui.embed_tab import EmbedTab
        from gui.extract_tab import ExtractTab
        from gui.compare_tab import CompareTab
        from gui.history_tab import HistoryTab
        self.embed_tab = EmbedTab(self.notebook, self)
        self.extract_tab = ExtractTab(self.notebook, self)
        self.compare_tab = CompareTab(self.notebook, self)
        self.history_tab = HistoryTab(self.notebook, self)
        for tab, title in [(self.embed_tab, 'Nhúng dữ liệu'), (self.extract_tab, 'Trích xuất dữ liệu'),
                           (self.compare_tab, 'So sánh PVD – DWT'), (self.history_tab, 'Lịch sử')]:
            self.notebook.add(tab, text=title)
        self.notebook.bind('<<NotebookTabChanged>>', self._tab_changed)
        self.protocol('WM_DELETE_WINDOW', self.close)

    def _style(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10))
        style.configure('TFrame', background='#f4f6f8')
        style.configure('TLabel', background='#f4f6f8', foreground='#1d2939')
        style.configure('TLabelframe', background='#f4f6f8')
        style.configure('TLabelframe.Label', background='#f4f6f8', font=('Segoe UI', 10, 'bold'))
        style.configure('TButton', padding=(12, 7))
        style.configure('Accent.TButton', foreground='white', background='#176b78')
        style.map('Accent.TButton', background=[('active', '#125762')])
        style.configure('Title.TLabel', font=('Segoe UI', 19, 'bold'))
        style.configure('Subtitle.TLabel', foreground='#667085')
        style.configure('TNotebook.Tab', padding=(20, 10))
        style.configure('Treeview', rowheight=29)
        style.configure('Compare.Treeview', rowheight=24)
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))

    def _tab_changed(self, event=None):
        if self.notebook.select() == str(self.history_tab):
            self.refresh_history()

    def set_status(self, text):
        self.status.set(text)

    def refresh_history(self):
        self.history_tab.refresh()

    def run_job(self, work, on_done):
        if self.busy:
            self.set_status('Đang xử lý; vui lòng đợi tác vụ hiện tại hoàn tất.')
            return
        self.busy = True
        self.compare_tab.update_busy()
        self.set_status('Đang xử lý…')
        self.configure(cursor='watch')
        future = self.executor.submit(work)

        def poll():
            if not future.done():
                self.after(60, poll)
                return
            self.busy = False
            self.compare_tab.update_busy()
            self.configure(cursor='')
            try:
                on_done(future.result())
            except Exception as exc:
                self.set_status('Không thể hoàn tất tác vụ.')
                messagebox.showerror('Lỗi xử lý', str(exc), parent=self)
            self.refresh_history()
        self.after(60, poll)

    def close(self):
        if self.busy:
            self.set_status('Vui lòng đợi tác vụ hoàn tất trước khi đóng ứng dụng.')
            return
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.destroy()
