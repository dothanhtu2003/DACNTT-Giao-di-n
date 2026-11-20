from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
from copy import deepcopy
import re,json

O=Path(__file__).parent
SRC=Path(r'C:\Users\thuho\Downloads\hihi_chuong_4_day_du_anh_va_bang.docx')
DEST=O/'hihi_chuong_4_da_ra_soat.docx'
with ZipFile(SRC) as z:parts={n:z.read(n) for n in z.namelist()}
original=parts['word/document.xml'].decode('utf-8');xml=original
root=E.fromstring(parts['word/document.xml']);W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
ns={'w':W,'a':'http://schemas.openxmlformats.org/drawingml/2006/main','wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
paras=root.findall('w:body/w:p',ns)
def txt(p):return ''.join(p.xpath('.//w:t/text()',namespaces=ns))
def tag(t):return '{'+W+'}'+t
def serialize(p):return E.tostring(p,encoding='unicode')
def raw_p(index):
    # Match through text parsed with the original namespace context.
    wanted=txt(paras[index]);assert wanted
    found=[]
    for m in re.finditer(r'<w:p\b[^>]*>.*?</w:p>',original,re.S):
        wrapper=E.Element('wrapper',nsmap=root.nsmap)
        wrapper=E.fromstring((serialize(wrapper).replace('/>','>')+m.group()+'</wrapper>').encode('utf-8'))
        if txt(wrapper[0])==wanted:found.append(m.group())
    assert len(found)==1,(index,wanted,len(found))
    return found[0]
changes=[]
def apply(old,new):
    global xml
    assert xml.count(old)==1,old[:100]
    xml=xml.replace(old,new,1);changes.append((old,new))
def text_replace(index,text):
    p=deepcopy(paras[index]);ts=p.findall('.//w:t',ns);assert ts
    ts[0].text=text
    for t in ts[1:]:t.text=''
    apply(raw_p(index),serialize(p))
def newp(text,template=434,keep=False):
    p=E.Element(tag('p'));source=paras[template]
    pr=source.find('w:pPr',ns)
    if pr is not None:p.append(deepcopy(pr))
    if keep:
        pr=p.find('w:pPr',ns)
        if pr is None:pr=E.SubElement(p,tag('pPr'))
        if pr.find('w:keepNext',ns) is None:E.SubElement(pr,tag('keepNext'))
    r=E.SubElement(p,tag('r'));rp=source.find('w:r/w:rPr',ns)
    if rp is not None:r.append(deepcopy(rp))
    text_node=E.SubElement(r,tag('t'));text_node.text=text
    if text.startswith(' ') or text.endswith(' '):text_node.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
    return p
def insert_after(index,nodes):
    old=raw_p(index);apply(old,old+''.join(serialize(n) for n in nodes))

revisions={
444:'Phần này trình bày kết quả đã thực hiện trên phần mềm: nhúng thông điệp, lưu PNG stego, mở lại để trích xuất và so sánh PVD với DWT. Hình 4.1–4.7 ghi nhận ca minh họa trên ảnh 4.2.06.png với thông điệp UTF-8 dài 128 byte. Hình 4.8–4.9 và các bảng đánh giá sử dụng kết quả chế độ Bộ ảnh với payload ASCII tự sinh; phạm vi ảnh, mức tải và số lần chạy được ghi rõ kèm từng bảng.',
452:'Ảnh kết quả được lưu dưới định dạng PNG, sau đó mở lại trong thẻ Trích xuất dữ liệu với phương pháp PVD. Chương trình đọc LENGTH, lấy payload và giải mã UTF-8. Thông điệp trích xuất đã được đối chiếu với thông điệp gốc, cho kết quả trùng khớp.',
455:'Trên ảnh 4.2.06.png kích thước 512 × 512, PVD nhúng và khôi phục đúng thông điệp UTF-8 128 byte sau khi lưu/đọc lại PNG. Packet gồm 1056 bit; capacity đạt 432265 bit, mức sử dụng 0,2443% và bpp = 0,004028. PSNR đạt 70,8446 dB, SSIM xấp xỉ 0,999999 và BER = 0. Đây là kết quả của ca minh họa không tác động ảnh, chưa chứng minh khả năng khôi phục sau chỉnh sửa.',
462:'Hình 4.5 – Ảnh stego DWT và các chỉ số đánh giá sau khi nhúng',
463:'Với DWT, ảnh stego được lưu dưới định dạng PNG rồi mở lại trong thẻ Trích xuất dữ liệu. Thông điệp khôi phục trùng với thông điệp UTF-8 ban đầu; kết quả được xác nhận bằng đối chiếu dữ liệu gốc, không chỉ dựa vào việc giải mã được văn bản.',
466:'Trên cùng ảnh và thông điệp 128 byte, DWT khôi phục đúng toàn bộ packet, BER = 0, PSNR = 51,0217 dB và SSIM = 0,997354. Capacity logic là 13107 bit; packet 1056 bit chiếm 8,0568%, với bpp = 0,004028. So với PVD trong ca minh họa này, DWT có capacity thấp hơn và mức sai khác ảnh lớn hơn, dù cả hai đều khôi phục chính xác khi chưa tác động ảnh.',
470:'Hình 4.7 – Vùng bảng chỉ số và biểu đồ so sánh PVD – DWT được phóng to',
471:'Trong Hình 4.7, hai phương pháp dùng chung ảnh 4.2.06.png và thông điệp UTF-8 128 byte. Bpp được tính bằng số bit packet, gồm 32 bit LENGTH và payload, chia cho số điểm ảnh nguồn. Biểu đồ là điểm chuẩn hóa tương đối của từng tiêu chí trong giao diện, không phải điểm chất lượng tổng hợp. Kết quả BER = 0 ở cả hai phương pháp chỉ xác nhận khôi phục đúng ca không tác động ảnh này.',
478:'Hình 4.9 – Kết quả Bộ ảnh ở payload 128 byte: (a) bảng tổng hợp; (b) vùng tỷ lệ khôi phục phóng to',
479:'Bộ thử nghiệm gồm 8 ảnh, 2 phương pháp và 4 mức payload (128, 512, 1024, 1500 byte), tạo thành 64 cấu hình nhúng. PVD hợp lệ ở 32/32 cấu hình; DWT hợp lệ ở 27/32 cấu hình. Tổng cộng 59 cấu hình vượt kiểm tra baseline, còn 5 cấu hình DWT không khôi phục đúng ngay sau lưu/đọc PNG. Các mức tác động được chạy riêng trên từng ảnh stego hợp lệ; số liệu độ bền trong Bảng 4.6 chỉ xét payload 128 byte và 7 ảnh hợp lệ đồng thời ở hai phương pháp.',
481:'Các bảng sau sử dụng số liệu của cùng lần chạy Bộ ảnh ngày 08/11/2026. Bảng 4.3–4.4 đánh giá ảnh 4.2.06.png; Bảng 4.5 xét toàn bộ 8 ảnh ở payload 128 byte; Bảng 4.6 xét 7 ảnh có baseline hợp lệ ở cả hai phương pháp tại mức tải này. Mỗi cấu hình được chạy một lần. Các mức payload và tham số tác động được trình bày riêng, không gộp thành một giá trị chất lượng trung bình.',
486:'Trên ảnh 4.2.06.png, khi payload tăng từ 128 lên 1500 byte, PSNR của PVD giảm từ 70,1952 xuống 58,2922 dB và SSIM giảm từ 0,999999 xuống 0,999870. DWT giảm từ 50,9456 xuống 40,2753 dB về PSNR và từ 0,997304 xuống 0,969669 về SSIM. PVD đạt PSNR và SSIM cao hơn DWT ở cả bốn mức tải trong bảng; cả hai phương pháp vẫn khôi phục đúng packet. Xu hướng này chỉ được xác nhận trên ảnh và cấu hình đang xét.',
491:'Trên ảnh 4.2.06.png, capacity PVD là 432265 bit, cao hơn khoảng 33 lần capacity logic DWT là 13107 bit. Khi payload tăng từ 128 lên 1500 byte, mức sử dụng tăng từ 0,2443% lên 2,7835% ở PVD và từ 8,0568% lên 91,7983% ở DWT. Trên toàn bộ 8 ảnh, capacity PVD dao động từ 394607 bit (gray21.512.png) đến 476319 bit (4.2.03.png), còn DWT giữ mức 13107 bit do cùng kích thước ảnh. Không cấu hình nào bị loại do thiếu dung lượng; 5 ca DWT lỗi cho thấy đủ capacity chưa bảo đảm khôi phục đúng sau tái tạo ảnh.',
496:'Ở payload 128 byte, PVD khôi phục đúng 8/8 ảnh (100%), còn DWT đúng 7/8 ảnh (87,50%). Ca DWT trên ruler.512.png sai LENGTH nên BER không xác định; 7 ca DWT còn lại có BER = 0. Vì vậy, BER trung bình bằng 0 trên các ca hợp lệ không đồng nghĩa với tỷ lệ khôi phục 100% trên toàn tập. Năm cấu hình DWT lỗi trong toàn bộ bốn mức tải đã được phân loại ở mục 4.3.4; không có lỗi thiếu dung lượng hay lỗi đọc/ghi ảnh trong lần chạy này.',
501:'Mỗi dòng Bảng 4.6 là một mức tác động độc lập; các tỷ lệ chỉ mô tả 7 ảnh chung ở payload 128 byte trong lần chạy này.',
503:'Trong phạm vi ảnh 4.2.06.png và bốn mức tải đã thử, PVD có capacity lớn hơn, PSNR và SSIM cao hơn DWT. Trên 7 ảnh chung ở payload 128 byte, DWT khôi phục tốt hơn PVD trước một số mức nhiễu và biến đổi quang học, nhưng cả hai đều không khôi phục được sau các mức JPEG, làm mờ, resize và crop đã chọn. Kết quả cho thấy việc lựa chọn phương pháp phải gắn với ảnh nguồn, mức tải và loại tác động cụ thể.',
504:'Kết luận giới hạn ở 8 ảnh nguồn, tập chung 7 ảnh tại payload 128 byte, một lần chạy/mức/ảnh và seed nhiễu 20260919; chưa đánh giá biến thiên giữa các seed hoặc khả năng khái quát cho tập ảnh khác. Khi dùng DWT cần kiểm tra baseline vì bước giới hạn giá trị điểm ảnh có thể làm mất dữ liệu. Báo cáo không dùng điểm tổng hợp tự gán trọng số để xếp hạng hai phương pháp.'
}
for i,text in revisions.items():text_replace(i,text)

# Fill the missing Table 4.1 using the existing table format.
source_text='Tập dữ liệu gồm 8 ảnh thuộc mục Miscellaneous của USC-SIPI Image Database, do Signal and Image Processing Institute, Đại học Southern California cung cấp [14]. Bảng 4.1 liệt kê mã ảnh, tên trong danh mục và các tệp PNG được dùng trong thư mục selected_512. Bộ ảnh gồm 4 ảnh RGB và 4 ảnh xám, đều có kích thước 512 × 512 pixel. Nguồn USC-SIPI phân phối ảnh TIFF; các tệp đầu vào của thực nghiệm được lưu ở dạng PNG.'
table=deepcopy(root.findall('.//w:tbl',ns)[18]);rows=table.findall('w:tr',ns)
header=deepcopy(rows[0]);template=deepcopy(rows[1])
for r in rows:table.remove(r)
grid=table.find('w:tblGrid',ns)
widths=[2350,3100,1250,2087]
for g,width in zip(grid,widths):g.set(tag('w'),str(width))
def values(row,vals):
    for c,v,width in zip(row.findall('w:tc',ns),vals,widths):
        tcw=c.find('w:tcPr/w:tcW',ns)
        if tcw is not None:tcw.set(tag('w'),str(width))
        ts=c.findall('.//w:t',ns);ts[0].text=v
        for t in ts[1:]:t.text=''
    return row
table.append(values(header,['Tệp PNG sử dụng','Tên ảnh tại USC-SIPI','Loại ảnh','Kích thước']))
dataset=[('4.2.01.png','Splash','RGB'),('4.2.03.png','Mandrill (Baboon)','RGB'),('4.2.05.png','Airplane (F-16)','RGB'),('4.2.06.png','Sailboat on lake','RGB'),('5.2.10.png','Stream and bridge','Ảnh xám'),('7.1.02.png','Airplane','Ảnh xám'),('gray21.512.png','21 level step wedge','Ảnh xám'),('ruler.512.png','Pixel ruler','Ảnh xám')]
for filename,name,mode in dataset:table.append(values(deepcopy(template),[filename,name,mode,'512 × 512']))
for row in table.findall('w:tr',ns)[:-1]:
    for cell_p in row.findall('.//w:p',ns):
        pr=cell_p.find('w:pPr',ns)
        if pr is None:pr=E.SubElement(cell_p,tag('pPr'));cell_p.insert(0,pr)
        if pr.find('w:keepNext',ns) is None:E.SubElement(pr,tag('keepNext'))
insert_after(435,[newp(source_text),newp('Bảng 4.1: Danh sách ảnh thực nghiệm từ USC-SIPI, mục Miscellaneous [14]',441,keep=True),table])

failure_notes=[
'Năm cấu hình lỗi gồm ruler.512.png tại cả bốn mức payload và gray21.512.png tại 1500 byte. Với ruler.512.png, trường LENGTH khác packet gốc nên không xác lập được ranh giới dữ liệu, BER = NA. Với gray21.512.png ở 1500 byte, LENGTH vẫn đúng nhưng 114 bit payload bị sai; BER của toàn packet là 114/12032 ≈ 0,009475. Hai ảnh này vẫn đủ capacity DWT, nên các lỗi được phân loại là không khớp packet, không phải vượt dung lượng. Thông báo “6 ảnh chạy thành công · 2 ảnh thất bại” ở Hình 4.9 đếm theo ảnh: 6 ảnh vượt mọi cấu hình nhúng, 2 ảnh có ít nhất một cấu hình lỗi; không phải tỷ lệ khôi phục sau tác động.',
'Để xác định nguyên nhân, nhóm tái dựng các bước DWT từ ảnh nguồn và payload đã dùng rồi đối chiếu với PNG stego được lưu. Ở cả năm cấu hình, giải mã sau biến đổi ngược với giá trị thực và sau làm tròn nhưng chưa giới hạn miền giá trị đều khớp packet. Sau khi chặn giá trị điểm ảnh về [0, 255], lỗi xuất hiện và ảnh thu được trùng từng điểm ảnh với PNG đã lưu. Kiểm tra này xác định bước giới hạn miền giá trị là nguyên nhân trực tiếp trong năm ca trên; chưa cho thấy làm tròn riêng lẻ gây lỗi. Đây là kiểm tra chẩn đoán trên các cấu hình cũ, không phải một đợt đo độ bền mới.',
'Mỗi cấu hình nhúng có 17 ca dự kiến: 1 ca không tác động và 16 ca tương ứng 8 phép xử lý × 2 mức tham số. Vì chỉ 59 cấu hình vượt baseline nên đã thực hiện 59 × 17 = 1003 ca. Năm cấu hình lỗi khiến 5 × 17 = 85 ca không được chạy. Các ca này không được gán là khôi phục thất bại do tác động; chúng được ghi nhận riêng là không đủ điều kiện baseline. Trong 1003 ca đã chạy có 59 ca không tác động và 944 ca có tác động ảnh.'
]
# Insert after the newly revised 4.3.4 observation.
anchor=next(new for old,new in changes if 'Bộ thử nghiệm gồm 8 ảnh, 2 phương pháp' in new)
apply(anchor,anchor+''.join(serialize(newp(t)) for t in failure_notes))

robust_notes=[
'Với 7 ảnh chung và payload 128 byte, DWT khôi phục đúng 6/7 ảnh (85,71%) ở nhiễu Gaussian σ = 1 và 1/7 ảnh (14,29%) ở σ = 3; PVD không khôi phục đúng ảnh nào ở hai mức này. Với nhiễu muối tiêu mức 0,001, cả hai phương pháp đúng 7/7 ảnh; tại 0,01, DWT vẫn đúng 7/7 còn PVD đúng 0/7. Kết quả nhiễu là một mẫu theo seed 20260919, không phải tỷ lệ trung bình qua nhiều seed.',
'Ở độ sáng −10, cả hai phương pháp đúng 5/7 ảnh; ở +10, PVD đúng 6/7 và DWT đúng 7/7. DWT đúng 5/7 và 4/7 ảnh khi hệ số tương phản lần lượt là 0,9 và 1,1, trong khi PVD đúng 0/7. Với JPEG ở quality 90/70, làm mờ Gaussian ở kernel 3/5, resize ở 0,75/1,25 và crop ở 0,9/0,75, cả hai đều đúng 0/7. Kết quả resize/crop gắn với chính sách không căn chỉnh hoặc phục hồi kích thước trước trích xuất.',
'Tỷ lệ khôi phục và BER phản ánh hai khía cạnh khác nhau. Ví dụ, ở JPEG quality 90, DWT đúng 0/7 ảnh nhưng chỉ 1 ca có BER hợp lệ (0,246212), còn 6 ca là NA; ở nhiễu Gaussian σ = 1, cả 7 ca DWT đều có BER hợp lệ, trung bình 0,003247. Do đó không diễn giải BER trên một tập con hợp lệ như đại diện cho mọi ca, và không thay BER = NA bằng 0 hoặc 1.'
]
robust_anchor=next(new for old,new in changes if 'Mỗi dòng Bảng 4.6 là một mức tác động độc lập' in new)
apply(robust_anchor,robust_anchor+''.join(serialize(newp(t)) for t in robust_notes))

# Crop within DrawingML: retain the original screenshots, enlarge selected regions.
def image_p(n):
    found=[m.group() for m in re.finditer(r'<w:p\b[^>]*>.*?</w:p>',original,re.S) if f'rIdChapter4Image{n}"' in m.group()]
    assert len(found)==1
    p=next(p for p in paras if p.xpath(f'.//a:blip[@r:embed="rIdChapter4Image{n}"]',namespaces=ns))
    return found[0],deepcopy(p)
def crop(p,box,docid=None):
    x1,y1,x2,y2=box
    blip=p.find('.//a:blip',ns);fill=blip.getparent()
    for old in fill.findall('a:srcRect',ns):fill.remove(old)
    rect=E.Element('{'+ns['a']+'}srcRect',l=str(round(x1/1180*100000)),t=str(round(y1/900*100000)),r=str(round((1180-x2)/1180*100000)),b=str(round((900-y2)/900*100000)))
    fill.insert(1,rect)
    cx=8787*635;cy=round(cx*(y2-y1)/(x2-x1))
    extent=p.find('.//wp:extent',ns);extent.set('cx',str(cx));extent.set('cy',str(cy))
    ext=p.find('.//a:xfrm/a:ext',ns);ext.set('cx',str(cx));ext.set('cy',str(cy))
    if docid is not None:
        dp=p.find('.//wp:docPr',ns);dp.set('id',str(docid));dp.set('name','Hinh 4.9 chi tiet');dp.set('descr','Phóng to các cột phương pháp, tác động, tham số và tỷ lệ khôi phục của Hình 4.9')
        for a in list(p.attrib):del p.attrib[a]
    return p
old,p=image_p(7);apply(old,serialize(crop(p,(532,211,1132,719))))
old,p=image_p(9)
full=crop(deepcopy(p),(33,253,1131,765))
detail=crop(deepcopy(p),(34,347,878,761),docid=9909)
labela=newp('(a) Bảng tổng hợp và các cột BER',478,keep=True)
labelb=newp('(b) Phóng to phương pháp, tác động và tỷ lệ khôi phục',478,keep=True)
apply(old,serialize(labela)+serialize(full)+serialize(labelb)+serialize(detail))

# Append a matching bibliography entry with a real hyperlink.
reference=newp('[14] Signal and Image Processing Institute, University of Southern California, “USC-SIPI Image Database — Volume 3: Miscellaneous.” [Online]. Available: ',524)
link=E.SubElement(reference,tag('hyperlink'));link.set('{'+ns['r']+'}id','rIdSIPI2026')
run=E.SubElement(link,tag('r'));rp=E.SubElement(run,tag('rPr'));E.SubElement(rp,tag('rStyle')).set(tag('val'),'Hyperlink');E.SubElement(run,tag('t')).text='https://sipi.usc.edu/database/database.php?volume=misc'
run=E.SubElement(reference,tag('r'));E.SubElement(run,tag('t')).text='. Truy cập ngày 08/11/2026.'
insert_after(524,[reference])
rels=parts['word/_rels/document.xml.rels'].decode('utf-8')
rels=rels.replace('</Relationships>','<Relationship Id="rIdSIPI2026" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://sipi.usc.edu/database/database.php?volume=misc" TargetMode="External"/></Relationships>')
parts['word/_rels/document.xml.rels']=rels.encode('utf-8')

# Keep Chapter 4 headings with their following text; retain fonts and spacing.
for index in [432,433,436,443,445,456,467,472,480,482,487,492,497,502]:
    p=deepcopy(paras[index]);pr=p.find('w:pPr',ns)
    if pr is None:pr=E.Element(tag('pPr'));p.insert(0,pr)
    keep=pr.find('w:keepNext',ns)
    if keep is None:keep=E.SubElement(pr,tag('keepNext'))
    keep.set(tag('val'),'1')
    apply(raw_p(index),serialize(p))
# The 17-level robustness table fits on one page with its repeated header.
old_tables=list(re.finditer(r'<w:tbl\b[^>]*>.*?</w:tbl>',original,re.S))
robust_table=deepcopy(root.findall('.//w:tbl',ns)[18])
for row in robust_table.findall('w:tr',ns)[:-1]:
    for p in row.findall('.//w:p',ns):
        pr=p.find('w:pPr',ns)
        if pr is None:pr=E.Element(tag('pPr'));p.insert(0,pr)
        keep=pr.find('w:keepNext',ns)
        if keep is None:keep=E.SubElement(pr,tag('keepNext'))
        keep.set(tag('val'),'1')
apply(old_tables[18].group(),serialize(robust_table))
E.fromstring(xml.encode('utf-8'));restored=xml
for old,new in reversed(changes):restored=restored.replace(new,old,1)
assert restored==original
for term in ['[Bổ sung','[Mô tả','[So sánh','[Nêu','[Điền','sẽ được bổ sung sau','và/hoặc ảnh phân rã']:
    assert term not in xml,term
parts['word/document.xml']=xml.encode('utf-8')
with ZipFile(DEST,'w',ZIP_DEFLATED) as z:
    for name,data in parts.items():z.writestr(name,data)
with ZipFile(SRC) as a,ZipFile(DEST) as b:
    modified=[n for n in a.namelist() if a.read(n)!=b.read(n)]
    assert set(modified)=={'word/document.xml','word/_rels/document.xml.rels'}
(O/'final_revision_audit.json').write_text(json.dumps({'modified_parts':modified,'all_image_files_byte_identical':True,'styles_margins_headers_footers_preserved':True,'targeted_replacements':len(changes),'no_pending_chapter4_placeholders':True},indent=2),encoding='utf-8')
print(DEST)
