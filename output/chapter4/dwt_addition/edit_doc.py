from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from copy import deepcopy
import re,json
from lxml import etree as E
from docx import Document
from docx.shared import Inches
from PIL import Image
O=Path(__file__).parent
src=Path('hihi_chuong_4_da_ra_soat (1).docx')
dst=Path('hihi_chuong_4_bo_sung_hinh_DWT.docx')
with ZipFile(src) as z: parts={n:z.read(n) for n in z.namelist()}
original=parts.copy(); root=E.fromstring(parts['word/document.xml'])
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
ps=root.findall('w:body/w:p',ns)
def txt(p):return ''.join(p.xpath('.//w:t/text()',namespaces=ns))
def settext(p,s):
    ts=p.xpath('.//w:t',namespaces=ns);ts[0].text=s
    for t in ts[1:]:t.text=''
def fresh(template,s):
    p=deepcopy(template)
    for k in list(p.attrib):del p.attrib[k]
    for child in list(p):
        if child.tag!='{'+ns['w']+'}pPr':p.remove(child)
    r=E.SubElement(p,'{'+ns['w']+'}r');t=E.SubElement(r,'{'+ns['w']+'}t');t.text=s
    return p
# Update captions and explicit references, including the shortened range.
for p in root.xpath('//w:p',namespaces=ns):
    s=txt(p)
    n=re.sub(r'([Hh]ình\s+4\.)([5-9])(?!\d)',lambda m:m[1]+str(int(m[2])+1),s)
    n=n.replace('Hình 4.1–4.7','Hình 4.1–4.8')
    if n!=s:settext(p,n)
anchor=next(p for p in ps if txt(p).startswith('Hình 4.4 –'))
caption=fresh(anchor,'Hình 4.5 – Kết quả phân rã ảnh nguồn thành bốn dải LL, LH, HL và HH bằng DWT Haar mức 1.')
remark=fresh(ps[457],'Quan sát Hình 4.5 cho thấy dải LL thể hiện cấu trúc tổng thể của ảnh nguồn 4.2.06.png; các dải LH và HL thể hiện chi tiết theo các hướng. Dải HH thể hiện chi tiết tần số cao và là dải được thuật toán của nhóm lựa chọn để nhúng dữ liệu.')
d=Document();p=d.add_paragraph();p.alignment=1;p.paragraph_format.keep_with_next=True
p.paragraph_format.space_after=Inches(.03)
p.paragraph_format.line_spacing=1
shape=p.add_run().add_picture(str(O/'dwt_decomposition_4.2.06.png'),width=Inches(5.4))
image=E.fromstring(E.tostring(p._p))
rid='rIdDWTDecomposition2026'
image.find('.//a:blip',ns).set('{'+ns['r']+'}embed',rid)
pr=image.find('.//wp:docPr',ns);pr.set('id',str(max(map(int,root.xpath('//wp:docPr/@id',namespaces=ns)))+1));pr.set('name','Phan ra DWT Haar muc 1');pr.set('descr','Ảnh chụp chức năng Xem phân rã DWT trên ảnh 4.2.06.png với bốn dải LL, LH, HL và HH.')
for node in [image,caption,remark]:anchor.addnext(node);anchor=node
old=next(p for p in ps if txt(p).startswith('Khi nhúng thành công, giao diện'))
settext(old,'Khi nhúng thành công, giao diện hiển thị ảnh kết quả và các chỉ số đánh giá.')
rels=E.fromstring(parts['word/_rels/document.xml.rels']);E.SubElement(rels,'{http://schemas.openxmlformats.org/package/2006/relationships}Relationship',Id=rid,Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/image',Target='media/dwt_decomposition_4.2.06.png')
parts['word/document.xml']=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
parts['word/_rels/document.xml.rels']=E.tostring(rels,xml_declaration=True,encoding='UTF-8',standalone=True)
parts['word/media/dwt_decomposition_4.2.06.png']=(O/'dwt_decomposition_4.2.06.png').read_bytes()
with ZipFile(dst,'w',ZIP_DEFLATED) as z:
    for n,b in parts.items():z.writestr(n,b)
changed=[n for n in original if original[n]!=parts[n]]
assert set(changed)=={'word/document.xml','word/_rels/document.xml.rels'}
caps=[txt(p) for p in root.xpath('//w:body/w:p',namespaces=ns) if re.match(r'Hình 4\.\d+ –',txt(p))]
assert [int(re.match(r'Hình 4\.(\d+)',s)[1]) for s in caps]==list(range(1,11))
(O/'audit.json').write_text(json.dumps({'modified_existing_parts':changed,'captions':caps,'source_image':'data/selected_512/4.2.06.png','capture':'EmbedTab.dwt_button.invoke -> DWTView -> ImageGrab'},ensure_ascii=False,indent=2),encoding='utf-8')
print(dst.resolve())
