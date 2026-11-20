import sys, json, time, traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from gui.main_window import MainWindow
from services.stego_service import StegoService
from storage.history_store import HistoryStore
import gui.common as common
OUT=Path(__file__).parent
app=MainWindow(StegoService(HistoryStore(OUT/'history.json')))
app.geometry('1180x900+20+20')
app.deiconify()
app.lift()
cover=ROOT/'data/selected_512/4.2.06.png'
message='Nghiên cứu kỹ thuật giấu tin trong ảnh số PVD và DWT. Kiểm tra nhúng và khôi phục thông điệp UTF-8.'
message += ' '*(128-len(message.encode('utf-8')))
assert len(message.encode('utf-8'))==128
def choose(tab,path):
    common.filedialog.askopenfilename=lambda **kw:str(path)
    tab.choose()
def wait():
    end=time.monotonic()+900
    while app.busy and time.monotonic()<end:
        app.update();time.sleep(.02)
    assert not app.busy
    app.update()
def execute(cmd):
    e=app.embed_tab;x=app.extract_tab;c=app.compare_tab
    if cmd in ('pvd_setup','dwt_setup'):
        app.notebook.select(e);choose(e,cover)
        e.method.set('PVD' if cmd.startswith('pvd') else 'DWT')
        e.message.delete('1.0','end');e.message.insert('1.0',message)
        e.changed();app.update()
    elif cmd=='embed':
        e.embed();wait();assert e.result['success'],e.result['error']
        (OUT/('metrics_'+e.method.get()+'.json')).write_text(json.dumps({k:v for k,v in e.result.items() if k!='output_image'},ensure_ascii=False,default=str,indent=2),encoding='utf-8')
    elif cmd=='extract':
        method=e.method.get();path=OUT/('stego_'+method.lower()+'.png')
        common.filedialog.asksaveasfilename=lambda **kw:str(path)
        e.save_button.invoke();assert path.exists()
        app.notebook.select(x);choose(x,path);x.method.set(method);x.extract();wait()
        assert x.message.get('1.0','end-1c')==message
    elif cmd=='compare':
        app.notebook.select(c);choose(c,cover)
        c.message.delete('1.0','end');c.message.insert('1.0',message);app.update()
        c.compare();wait();assert all(r['success'] for r in c.results.values())
    elif cmd=='batch_setup':
        app.notebook.select(c);c.mode.set('Bộ ảnh');c.mode_changed()
        p=c.batch_panel;p.source.set(str(ROOT/'data/selected_512'))
        p.destination.set(str(OUT/'batch_results'));p.payloads.set('128, 512, 1024, 1500');p.seeds.set('20260919')
        for name,(_,enabled,values) in p.attacks.items(): enabled.set(True)
        p.inspect();app.update()
    elif cmd=='batch_run':
        p=c.batch_panel;p.start();wait();assert p.result and p.result['status']=='completed'
        p.filter_payload.set('128');p.show_summary()
        (OUT/'batch_done.json').write_text(json.dumps({k:v for k,v in p.result.items() if k not in ('rows','summary','baselines')},ensure_ascii=False,default=str,indent=2),encoding='utf-8')
    elif cmd.startswith('shot_'):
        from PIL import ImageGrab
        app.deiconify();app.lift();app.update();time.sleep(.5)
        ImageGrab.grab(bbox=(app.winfo_rootx(),app.winfo_rooty(),app.winfo_rootx()+app.winfo_width(),app.winfo_rooty()+app.winfo_height())).save(OUT/'screenshots'/(cmd[5:]+'.png'))
    elif cmd=='batch_chart':c.batch_panel.show_chart()
    elif cmd=='close':app.close();return
    app.update()
def poll():
    f=OUT/'command.json'
    if f.exists():
        try: cmd=json.loads(f.read_text(encoding='utf-8-sig'))
        except (ValueError,OSError):
            app.after(200,poll);return
        f.unlink()
        try:
            execute(cmd['action']);result={'ok':True,'action':cmd['action'],'status':app.status.get()}
        except Exception:
            result={'ok':False,'error':traceback.format_exc()}
        (OUT/'state.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    app.after(200,poll)
app.update()
(OUT/'window.txt').write_text(app.wm_frame())
app.after(200,poll)
app.mainloop()
