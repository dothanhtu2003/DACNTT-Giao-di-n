from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import re,json
from lxml import etree
from docx import Document
from docx.shared import Emu

BASE=Path(__file__).parent
SOURCE=Path(r'C:\Users\thuho\Downloads\hihi.docx')
TARGET=BASE/'hihi_da_chen_anh_chuong_4.docx'
with ZipFile(SOURCE) as z: original={n:z.read(n) for n in z.namelist()}
parts=original.copy()
xml=parts['word/document.xml'].decode('utf-8')
rels=parts['word/_rels/document.xml.rels'].decode('utf-8')
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
root=etree.fromstring(parts['word/document.xml'])
next_id=max([int(x) for x in root.xpath('//wp:docPr/@id',namespaces=ns)]+[0])+1
matches=[m for m in re.finditer(r'<w:p\b[^>]*>.*?</w:p>',xml,re.S) if '[Chèn ảnh chụp thực tế:' in m.group()]
assert len(matches)==9
replacements=[]
for n,m in enumerate(matches,1):
    path=BASE/'screenshots'/f'figure_4_{n}.png'
    d=Document();p=d.add_paragraph();shape=p.add_run().add_picture(str(path),width=Emu(8787*635))
    inline=shape._inline
    inline.docPr.set('id',str(next_id+n));inline.docPr.set('name',f'Hinh 4.{n}')
    inline.docPr.set('descr',f'Ảnh chụp giao diện chạy thực tế cho Hình 4.{n}')
    rid=f'rIdChapter4Image{n}'
    inline.xpath('.//a:blip')[0].set('{'+ns['r']+'}embed',rid)
    run=etree.tostring(p._p[0],encoding='unicode')
    old=m.group()
    opening=old[:old.index('>')+1]
    ppr=re.search(r'<w:pPr>.*?</w:pPr>',old,re.S).group()
    ppr=ppr.replace('</w:pPr>','<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/><w:ind w:left="0" w:right="0" w:firstLine="0"/></w:pPr>')
    new=opening+ppr+run+'</w:p>'
    replacements.append((old,new))
    target=f'media/chapter4_figure_{n}.png'
    parts['word/'+target]=path.read_bytes()
    rels=rels.replace('</Relationships>',f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="{target}"/></Relationships>')
for old,new in replacements:
    assert xml.count(old)==1
    xml=xml.replace(old,new,1)
parts['word/document.xml']=xml.encode('utf-8')
parts['word/_rels/document.xml.rels']=rels.encode('utf-8')
assert b'Extension="png"' in parts['[Content_Types].xml']
for name in ['word/document.xml','word/_rels/document.xml.rels']:etree.fromstring(parts[name])
with ZipFile(TARGET,'w',ZIP_DEFLATED) as z:
    for name,value in parts.items():z.writestr(name,value)
restored=xml
for old,new in replacements:restored=restored.replace(new,old,1)
assert restored.encode('utf-8')==original['word/document.xml']
changed=[k for k in original if parts[k]!=original[k]]
assert changed==['word/document.xml','word/_rels/document.xml.rels'] or set(changed)=={'word/document.xml','word/_rels/document.xml.rels'}
(BASE/'preservation_audit.json').write_text(json.dumps({'replaced_image_placeholders':9,'modified_existing_zip_parts':changed,'all_other_parts_byte_identical':True,'document_xml_identical_after_reversing_nine_replacements':True},indent=2),encoding='utf-8')
print(TARGET)
