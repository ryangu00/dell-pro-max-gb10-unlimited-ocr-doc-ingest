"""Synthetic scanned-page corpus with exact ground truth for OCR measurements.
Run (pymupdf, pillow, numpy must already be installed): python3 make-ocr-bench-corpus.py OUTDIR
Writes OUTDIR/pages/pNN.png (40 scan-like pages, 200 dpi, grey, slight skew + noise),
OUTDIR/scan{1,3,10,40}.pdf (image-only PDFs holding JPEG q85 pages: the first N pages), OUTDIR/truth.json.
Every page: a title line, one ~800-character paragraph, one dense table
(two-level header with rowspan/colspan, 14 data rows x 6 columns, all cells unique to the page)."""
import io, json, os, random, sys
from pathlib import Path

random.seed(20261004)
WORDS = ("the quick brown fox jumps over a lazy dog while sensors report values across several independent "
         "measurement windows and the committee reviews each quarterly summary carefully before approving "
         "the revised schedule for maintenance shipping inventory and staffing at every regional facility").split()
SITES = ["Alder", "Birch", "Cedar", "Dogwood", "Elm", "Fir", "Ginkgo", "Hazel", "Iris", "Juniper", "Kelp", "Larch",
         "Maple", "Nettle", "Oak", "Pine", "Quince", "Rowan", "Spruce", "Tamarisk", "Umber", "Vetch", "Willow", "Yarrow"]
N_PAGES, N_ROWS = 40, 14


def make_page(n):
    para = " ".join(random.choice(WORDS) for _ in range(130))[:800].rsplit(" ", 1)[0]
    para = para[0].upper() + para[1:] + "."
    rows = []
    for r in range(N_ROWS):
        site = f"{random.choice(SITES)}-{n:02d}{r:02d}"  # unique per page and row
        out = [str(random.randint(1000, 99999)) for _ in range(3)]
        cost = [f"{random.randint(100, 9999)}.{random.randint(0, 99):02d}" for _ in range(2)]
        rows.append([site] + out + cost)
    return {"page": n, "title": f"Operations Report Section {n}", "paragraph": para,
            "header": [["Site", "Output (units)", "Cost (USD)"], ["Q1", "Q2", "Q3", "Q1", "Q2"]], "rows": rows}


CELL = "border:1px solid #000;padding:3px;text-align:center"


def html(p):
    t = ('<table cellspacing="0" style="border-collapse:collapse;font-size:9pt;width:100%">'
         f'<tr><th rowspan="2" style="{CELL}">Site</th><th colspan="3" style="{CELL}">Output (units)</th>'
         f'<th colspan="2" style="{CELL}">Cost (USD)</th></tr>'
         '<tr>' + "".join(f'<th style="{CELL}">{c}</th>' for c in p["header"][1]) + "</tr>")
    for row in p["rows"]:
        t += "<tr>" + "".join(f'<td style="{CELL}">{c}</td>' for c in row) + "</tr>"
    t += "</table>"
    return (f"<h3 style='font-size:14pt'>{p['title']}</h3><p style='font-size:10pt'>{p['paragraph']}</p>"
            f"<p></p>{t}")


def render(p, dpi=200):
    import numpy as np
    import pymupdf
    from PIL import Image, ImageFilter
    d = pymupdf.open()
    pg = d.new_page(width=595, height=842)
    pg.insert_htmlbox(pymupdf.Rect(48, 48, 547, 794), html(p))
    pix = pg.get_pixmap(matrix=pymupdf.Matrix(dpi / 72, dpi / 72), colorspace=pymupdf.csGRAY)
    img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
    img = img.rotate(random.uniform(-0.4, 0.4), resample=Image.BICUBIC, fillcolor=255)
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    a = np.asarray(img, dtype=np.float32) * 0.93 + 8  # slightly grey paper
    a += np.random.default_rng(p["page"]).normal(0, 6, a.shape)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "L")


def main(out):
    import pymupdf
    from PIL import Image
    os.makedirs(os.path.join(out, "pages"), exist_ok=True)
    pages = [make_page(n) for n in range(1, N_PAGES + 1)]
    paths = []
    for p in pages:
        f = os.path.join(out, "pages", f"p{p['page']:02d}.png")
        render(p).save(f, dpi=(200, 200))
        paths.append(f)
    for k in (1, 3, 10, 40):
        d = pymupdf.open()
        for f in paths[:k]:
            pg = d.new_page(width=595, height=842)
            buf = io.BytesIO(); Image.open(f).save(buf, "JPEG", quality=85)  # scanners emit JPEG
            pg.insert_image(pg.rect, stream=buf.getvalue())
        d.save(os.path.join(out, f"scan{k}.pdf"))
    Path(out, "truth.json").write_text(json.dumps(pages, indent=1))
    print("ok", out)


if __name__ == "__main__":
    main(sys.argv[1])
