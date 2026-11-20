from pathlib import Path
import sys,time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from gui.main_window import MainWindow
from services.stego_service import StegoService
from storage.history_store import HistoryStore
import gui.common as common
from PIL import ImageGrab
out=Path(__file__).parent
app=MainWindow(StegoService(HistoryStore(out/'capture_history.json')))
app.geometry('1180x900+20+20')
e=app.embed_tab
common.filedialog.askopenfilename=lambda **kw:str(ROOT/'data/selected_512/4.2.06.png')
e.choose();e.method.set('DWT');e.changed();app.update()
e.dwt_button.invoke();app.update()
from gui.dwt_view import DWTView
view=next(w for w in e.winfo_children() if isinstance(w,DWTView))
view.geometry('740x700+80+60');view.lift();app.update();time.sleep(.7)
ImageGrab.grab(window=int(view.wm_frame(),16)).save(out/'dwt_decomposition_4.2.06.png')
app.close()

