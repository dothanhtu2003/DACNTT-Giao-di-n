from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from copy import deepcopy
from xml.sax.saxutils import escape
import csv,json,re

O=Path(__file__).parent
SRC=Path(r'C:\Users\thuho\Downloads\hihi_da_chen_anh_chuong_4.docx')
DEST=O/'hihi_chuong_4_day_du_anh_va_bang.docx'
RUN=O/'batch_results/20261108T143804Z_d1bb1e004a354a46a24d1a4f62d60cfe'
metrics=json.loads((O/'table_metrics.json').read_text(encoding='utf-8'))
summary=list(csv.DictReader((RUN/'summary.csv').open(encoding='utf-8-sig')))
base=list(csv.DictReader((RUN/'baselines.csv').open(encoding='utf-8-sig')))
config=json.loads((RUN/'config.json').read_text(encoding='utf-8'))
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
ns={'w':W}
def q(t):return '{'+W+'}'+t
def fmt(v,n=4):return f'{float(v):.{n}f}'.replace('.',',')
def met(m,p):return next(x for x in metrics if x['method']==m and x['payload_bytes']==str(p))
def setcell(cell,text):
    texts=cell.findall('.//w:t',ns)
    assert texts
    texts[0].text=str(text)
    for t in texts[1:]:t.text=''
def setrow(row,values):
    cells=row.findall('w:tc',ns);assert len(cells)==len(values)
    for cell,value in zip(cells,values):setcell(cell,value)
def note(text):
    return '<w:p><w:pPr><w:pStyle w:val="Nidungvnbn"/></w:pPr><w:r><w:t>'+escape(text)+'</w:t></w:r></w:p>'

with ZipFile(SRC) as z:parts={n:z.read(n) for n in z.namelist()}
original=parts['word/document.xml'].decode('utf-8')
xml=original
root=E.fromstring(parts['word/document.xml'])
tables=root.findall('.//w:tbl',ns)
matches=list(re.finditer(r'<w:tbl\b[^>]*>.*?</w:tbl>',original,re.S))
assert len(matches)==len(tables)
notes={}
t=tables[14];rows=t.findall('w:tr',ns)
setcell(rows[1].findall('w:tc',ns)[1],'Python '+config['environment']['python'])
setcell(rows[2].findall('w:tc',ns)[1],'Windows 10 Home Single Language (10.0.19045); Intel Core i5-10500H 2,50 GHz; RAM 16 GB')
setcell(rows[3].findall('w:tc',ns)[1],'8 ảnh PNG, 512 × 512 pixel, RGB hoặc ảnh xám; thư mục selected_512')
setcell(rows[8].findall('w:tc',ns)[1],'128, 512, 1024 và 1500 byte; thông điệp ASCII tự sinh, cố định theo độ dài')
setcell(rows[9].findall('w:tc',ns)[1],'Seed nhiễu 20260919; không tác động và 8 phép xử lý, mỗi phép 2 mức tham số như Bảng 4.6; mỗi cấu hình chạy 1 lần')
notes[14]='Lần chạy Bộ ảnh ngày 08/11/2026 có 64 cấu hình nhúng: 59 hợp lệ, 5 lỗi DWT. Đã chạy 1003/1088 ca dự kiến; 85 ca không chạy do baseline lỗi; các ca chưa chạy không được tính là thất bại khi đánh giá phép tác động.'
t=tables[15]
for row,p in zip(t.findall('w:tr',ns)[1:],[128,512,1024,1500]):
    a,b=met('PVD',p),met('DWT',p)
    setrow(row,[p,fmt(a['psnr']),fmt(b['psnr']),fmt(a['ssim'],6),fmt(b['ssim'],6)])
notes[15]='Bảng 4.3 dùng ảnh 4.2.06.png (RGB, 512 × 512), cùng payload ASCII tự sinh cho PVD/DWT, 1 lần/cấu hình. Chỉ số tính từ PNG stego đã lưu. Payload khác ví dụ UTF-8 trong Hình 4.1–4.7 nên chỉ số 128 byte khác các hình.'
t=tables[16]
for row,(p,m) in zip(t.findall('w:tr',ns)[1:],[(128,'PVD'),(128,'DWT'),(1500,'PVD'),(1500,'DWT')]):
    a=met(m,p)
    setrow(row,[f'4.2.06.png / {p} byte',m,a['capacity_bits'],a['packet_bits'],fmt(a['usage_percent'])])
notes[16]='Bảng 4.4 dùng cùng ảnh và lần chạy với Bảng 4.3; cả bốn cấu hình đều khôi phục đúng packet. Bpp ở mức 128 và 1500 byte lần lượt là 0,004028 và 0,045898 cho cả hai phương pháp.'
t=tables[17]
for row,m in zip(t.findall('w:tr',ns)[1:],['PVD','DWT']):
    selected=[b for b in base if b['method']==m and b['payload_bytes']=='128']
    success=sum(b['baseline_status']=='valid' for b in selected)
    assert len(selected)==8
    setrow(row,[m,len(selected),success,fmt(success/len(selected)*100,2),'0,000000 (8 ca)' if m=='PVD' else '0,000000 (7 ca); 1 NA'])
notes[17]='Bảng 4.5 xét 8 ảnh, payload 128 byte, 1 lần/ảnh, sau lưu/đọc PNG. DWT lỗi LENGTH trên ruler.512.png: tính là thất bại, BER = NA. BER trung bình chỉ tính trên các ca có BER hợp lệ.'
t=tables[18];rows=t.findall('w:tr',ns);templates=[deepcopy(r) for r in rows[1:]]
for r in rows[1:]:t.remove(r)
labels={'none':'Không tác động','jpeg':'Nén JPEG','gaussian_noise':'Nhiễu Gaussian','salt_pepper':'Nhiễu muối tiêu','blur':'Làm mờ Gaussian','brightness':'Độ sáng','contrast':'Độ tương phản','resize':'Thay đổi kích thước','crop':'Cắt ảnh'}
orders=list(labels)
for attack in config['config']['attacks']:
    name=attack['name'];params=attack['parameters']
    values=[]
    for m in ['PVD','DWT']:
        found=[s for s in summary if s['scope']=='common' and s['payload_bytes']=='128' and s['method']==m and s['attack']==name and json.loads(s['attack_parameter'])==params]
        assert len(found)==1
        s=found[0];assert int(s['completed_cases'])==7
        values.append(fmt(float(s['image_success_mean'])*100,2)+f" ({s['success_cases']}/7)")
    parameter='Baseline' if not params else ', '.join(f'{("kernel" if k=="kernel_size" else k)} = {str(v).replace(".",",")}' for k,v in params.items())
    row=deepcopy(templates[orders.index(name)])
    setrow(row,[labels[name],parameter,*values]);t.append(row)
notes[18]='Bảng 4.6 xét payload 128 byte trên 7 ảnh có baseline hợp lệ ở cả hai phương pháp (loại ruler.512.png); 1 lần/mức/ảnh, seed nhiễu 20260919. Ngoặc ghi số ca đúng/7 ca chạy. Resize/crop không căn chỉnh hay phục hồi kích thước trước trích xuất.'
changes=[]
for i in range(14,19):
    old=matches[i].group();new=E.tostring(tables[i],encoding='unicode')+note(notes[i])
    assert xml.count(old)==1;xml=xml.replace(old,new,1);changes.append((old,new))
for n in range(3,7):
    cap=next(p for p in root.findall('.//w:body/w:p',ns) if ''.join(p.xpath('.//w:t/text()',namespaces=ns)).startswith(f'Bảng 4.{n}:'))
    oldtext=''.join(cap.xpath('.//w:t/text()',namespaces=ns))
    # Remove only the now-obsolete pending-result label.
    if ' (điền kết quả)' in oldtext:
        old=next(m.group() for m in re.finditer(r'<w:p\b[^>]*>.*?</w:p>',xml,re.S) if escape(oldtext) in m.group())
        new=old.replace(' (điền kết quả)','');xml=xml.replace(old,new,1);changes.append((old,new))
oldnote='Lưu ý: Những tham số ghi bằng dấu “/” thể hiện các mức thử nghiệm riêng, không phải một phép tác động ghép. Khi điền bảng chính thức nên tách thành từng dòng nếu có kết quả cho từng mức. Không kết luận DWT bền vững hơn PVD chỉ từ cơ chế miền biến đổi; nhận xét phải dựa trên tỷ lệ khôi phục thực tế của cấu hình đang nghiên cứu.'
newnote='Lưu ý: Mỗi mức tham số trong bảng là một phép tác động riêng. Không kết luận DWT bền vững hơn PVD chỉ từ cơ chế miền biến đổi; nhận xét phải dựa trên tỷ lệ khôi phục thực tế của cấu hình đang nghiên cứu.'
assert oldnote in xml;xml=xml.replace(oldnote,newnote,1);changes.append((oldnote,newnote))
E.fromstring(xml.encode('utf-8'))
check=xml
for old,new in reversed(changes):check=check.replace(new,old,1)
assert check==original
parts['word/document.xml']=xml.encode('utf-8')
with ZipFile(DEST,'w',ZIP_DEFLATED) as z:
    for n,data in parts.items():z.writestr(n,data)
with ZipFile(SRC) as a,ZipFile(DEST) as b:
    assert all(a.read(n)==b.read(n) for n in a.namelist() if n!='word/document.xml')
assert not any('[Điền' in ''.join(t.itertext()) for t in tables[14:19])
(O/'tables_audit.json').write_text(json.dumps({'tables_filled':['4.2','4.3','4.4','4.5','4.6'],'only_document_xml_changed':True,'outside_targeted_tables_captions_notes_unchanged':True,'image_parts_preserved':True},indent=2),encoding='utf-8')
print(DEST)
