import json,time
from pathlib import Path
from PIL import ImageGrab
O=Path(__file__).parent
def command(action):
    state=O/'state.json'
    if state.exists(): state.unlink()
    (O/'command.tmp').write_text(json.dumps({'action':action}),encoding='utf-8')
    (O/'command.tmp').replace(O/'command.json')
    deadline=time.monotonic()+1200
    while not state.exists():
        if time.monotonic()>deadline:raise TimeoutError(action)
        time.sleep(.2)
    r=json.loads(state.read_text(encoding='utf-8'));assert r['ok'],r
    print(action, r,flush=True);time.sleep(.4)
def shot(n):
    ImageGrab.grab(window=int((O/'window.txt').read_text(),16)).save(O/'screenshots'/f'figure_4_{n}.png')
    print('Captured',n,flush=True)
command('pvd_setup');shot(1)
command('embed');shot(2)
command('extract');shot(3)
command('dwt_setup');shot(4)
command('embed');shot(5)
command('extract');shot(6)
command('compare');shot(7)
command('batch_setup');shot(8)
command('batch_run');shot(9)
