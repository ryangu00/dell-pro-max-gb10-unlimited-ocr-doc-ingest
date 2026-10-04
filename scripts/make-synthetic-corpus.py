"""Writes a synthetic PDF corpus into the current directory (needs: pip install pymupdf).
Files: digital10 (10 text pages, ~2000 chars each, a merged-cell table on pages 1,4,7,10), scanned10 (same pages rasterized,
no text layer), mixed9 (8 text pages + 1 image-only page), slides400 (~400 chars/page), band_just_above (~700 chars/page),
titlepage_dense (14-char title page + 7 dense pages), blank1, broken (not a PDF)."""
import pymupdf, random, textwrap
from pathlib import Path
random.seed(7)
words="the quick brown fox jumps over a lazy dog while sensors report values across several independent measurement windows and the committee reviews each quarterly summary carefully".split()
def para(n):
    return " ".join(random.choice(words) for _ in range(n))
TABLE="""<table border="1" cellpadding="3" style="border-collapse:collapse">
<tr><th rowspan="2">Region</th><th colspan="2">2025</th></tr>
<tr><th>Q1</th><th>Q2</th></tr>
<tr><td>North</td><td>120</td><td>135</td></tr>
<tr><td>South</td><td>98</td><td>101</td></tr>
</table>"""
def digital_page(doc, chars=2000, table=True):
    p=doc.new_page()
    body=para(chars//6)[:chars]
    html=f"<p style='font-size:9pt'>{body}</p>"
    if table: html+=TABLE
    p.insert_htmlbox(p.rect+(36,36,-36,-36), html)
    return p
def make_digital(path,n=10,chars=2000):
    d=pymupdf.open()
    for i in range(n): digital_page(d,chars,table=(i%3==0))
    d.save(path); return d
def rasterize(src_path,dst_path,pages=None):
    s=pymupdf.open(src_path); o=pymupdf.open()
    for i in range(len(s)):
        if pages is not None and i not in pages: continue
        pix=s[i].get_pixmap(matrix=pymupdf.Matrix(2,2))
        p=o.new_page(width=s[i].rect.width,height=s[i].rect.height); p.insert_image(p.rect,pixmap=pix)
    o.save(dst_path)
make_digital("digital10.pdf",10,2000)
rasterize("digital10.pdf","scanned10.pdf")
# mixed: 8 digital pages + 1 image page
d=pymupdf.open("digital10.pdf"); m=pymupdf.open(); m.insert_pdf(d,from_page=0,to_page=7)
pix=d[0].get_pixmap(matrix=pymupdf.Matrix(2,2)); p=m.new_page(width=d[0].rect.width,height=d[0].rect.height); p.insert_image(p.rect,pixmap=pix); m.save("mixed9.pdf")
# low-confidence band ~400 chars/page (slide-like)
make_digital("slides400.pdf",8,400)
# boundary tests
make_digital("band_just_above.pdf",6,700)
# Title-page fixture: short cover followed by dense pages.
t=pymupdf.open(); p=t.new_page(); p.insert_text((72,72),"Annual Report"); 
for i in range(7): digital_page(t,1500,False)
t.save("titlepage_dense.pdf")
# empty pdf is invalid for pymupdf; make 1 blank page
b=pymupdf.open(); b.new_page(); b.save("blank1.pdf")
Path("broken.pdf").write_text("not a pdf")
print("ok")
