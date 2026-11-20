import sys,json,csv
from pathlib import Path
import numpy as np
import pywt
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from core import dwt
from core.image_utils import load_image
from core.payload import build_packet,packet_to_bits
from experiments.robustness_runner import public_payload
from experiments.extraction import assess_extraction
OUT=Path(__file__).parent
RUN=OUT/'batch_results/20261108T143804Z_d1bb1e004a354a46a24d1a4f62d60cfe'
rows=list(csv.DictReader((RUN/'baselines.csv').open(encoding='utf-8-sig')))
results=[]
for row in rows:
    if row['baseline_status']!='mismatch':continue
    original=load_image(ROOT/'data/selected_512'/row['image_name'])
    saved=load_image(RUN/row['stego_path'])
    assert original.ndim==2
    bits=packet_to_bits(build_packet(public_payload(int(row['payload_bytes']))))
    ll,(lh,hl,hh)=pywt.dwt2(original.astype(float),'haar',mode='symmetric')
    flat=hh.ravel().copy();physical=np.repeat(bits,5)
    flat[:len(physical)]=dwt.quantize(flat[:len(physical)],physical)
    restored=pywt.idwt2((ll,(lh,hl,flat.reshape(hh.shape))),'haar',mode='symmetric')
    rounded=np.rint(restored)
    clipped=np.clip(rounded,0,255).astype(np.uint8)
    assert np.array_equal(saved,clipped)
    def errors(arr):
        coeff=pywt.dwt2(arr.astype(float),'haar',mode='symmetric')[1][2].ravel()[:len(physical)]
        decoded=dwt.majority_vote(dwt.coefficient_bits(coeff))
        return {'length_errors':int(np.count_nonzero(decoded[:32]!=bits[:32])),
                'payload_errors':int(np.count_nonzero(decoded[32:]!=bits[32:]))}
    result=dict(row, assessment=assess_extraction(dwt,saved,bits),
        float_inverse_errors=errors(restored), rounded_unclipped_errors=errors(rounded),
        clipped_saved_errors=errors(saved),clipped_pixels=int(np.count_nonzero((rounded<0)|(rounded>255))),
        saved_matches_reconstructed=True)
    results.append(result)
(OUT/'baseline_diagnostics.json').write_text(json.dumps(results,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2,default=str))
