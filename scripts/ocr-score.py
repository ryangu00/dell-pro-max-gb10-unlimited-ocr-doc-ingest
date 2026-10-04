"""Score OCR Markdown against truth.json from make-ocr-bench-corpus.py.
Run: python3 ocr-score.py truth.json result.md [npages_in_input]
Prints one JSON object: page markers, per-document and per-page character error rate (CER) for prose and for table text,
table count, header-structure survival, row and cell recovery. Uses rapidfuzz when installed, otherwise an exact stdlib edit-distance fallback."""
import json, re, sys
from pathlib import Path
try:
    from rapidfuzz.distance import Levenshtein
except ImportError:
    class Levenshtein:
        @staticmethod
        def distance(a, b):
            if a == b:
                return 0
            if len(a) < len(b):
                a, b = b, a
            previous = list(range(len(b) + 1))
            for i, ca in enumerate(a, 1):
                current = [i]
                for j, cb in enumerate(b, 1):
                    current.append(min(current[-1] + 1, previous[j] + 1,
                                       previous[j - 1] + (ca != cb)))
                previous = current
            return previous[-1]


def norm(s): return re.sub(r"\s+", " ", s).strip()
def cer(ref, hyp): return Levenshtein.distance(ref, hyp) / max(1, len(ref))


def split_pages(md):
    parts = [p for p in re.split(r"^\s*<PAGE>\s*$", md, flags=re.M)]
    return [p for p in parts if p.strip()]


def split_blocks(page):
    """-> (prose text, table html list). Prose = everything outside <table>...</table>, tags and image refs removed."""
    tabs = re.findall(r"<table.*?</table>", page, flags=re.S | re.I)
    rest = re.sub(r"<table.*?</table>", " ", page, flags=re.S | re.I)
    rest = re.sub(r"!\[\]\([^)]*\)", " ", rest)
    rest = re.sub(r"<[^>]+>", " ", rest)
    rest = re.sub(r"^#+\s*", "", rest, flags=re.M)
    return norm(rest), tabs


def cells_of(row_html):
    return [(m.group(1), norm(re.sub(r"<[^>]+>", " ", m.group(3))), int((re.search(r"colspan\D*(\d+)", m.group(2)) or [0, 1])[1]),
             int((re.search(r"rowspan\D*(\d+)", m.group(2)) or [0, 1])[1]))
            for m in re.finditer(r"<t([dh])([^>]*)>(.*?)</t[dh]>", row_html, flags=re.S | re.I)]


def score_page(t, page):
    """Lenient regex table reading (a strict HTML parser swallows text after a malformed attribute such as colspan='2")."""
    prose, tabs = split_blocks(page)
    ref_prose = norm(t["title"] + " " + t["paragraph"])
    out = {"prose_cer": round(cer(ref_prose, prose), 4), "n_tables": len(tabs),
           "malformed_html": bool(re.search(r"=\s*'[^'>]*\"|=\s*\"[^\">]*'", page))}
    ref_cells = [c for r in t["rows"] for c in r]
    ref_tab = norm(" ".join(["Site", "Output (units)", "Cost (USD)"] + t["header"][1] + ref_cells))
    txt = norm(re.sub(r"<[^>]+>", " ", " ".join(tabs)))
    out["table_cer"] = round(cer(ref_tab, txt), 4)
    rows = [cells_of(r) for h in tabs for r in re.findall(r"<tr[^>]*>(.*?)</tr>", h, flags=re.S | re.I)]
    hdr = [c for r in rows[:2] for c in r]
    ok = lambda text, cs, rs: any(c[1] == text and c[2] == cs and c[3] == rs for c in hdr)
    out["header_ok"] = bool(ok("Site", 1, 2) and ok("Output (units)", 3, 1) and ok("Cost (USD)", 2, 1))
    got = {r[0][1]: [c[1] for c in r] for r in rows if r}
    present = exact_rows = pos_cells = val_cells = six = 0
    for r in t["rows"]:
        g = got.get(r[0])
        if g is None: continue
        present += 1; exact_rows += g == r; six += len(g) == len(r)
        pos_cells += sum(a == b for a, b in zip(g, r)); val_cells += sum(c in g for c in r)
    out.update(rows_present=present, rows_exact=exact_rows, rows_six_cells=six, rows_total=len(t["rows"]),
               cells_pos_exact=pos_cells, cells_value_found=val_cells, cells_total=len(ref_cells))
    return out


def main(truth_path, md_path, n_in=None):
    truth = json.loads(Path(truth_path).read_text()); md = Path(md_path).read_text()
    n_in = int(n_in or len(truth))
    if not 1 <= n_in <= len(truth):
        raise ValueError("input page count must be positive and within ground truth")
    truth = truth[:n_in]
    pages = split_pages(md)
    res = {"input_pages": n_in, "page_markers": len(re.findall(r"^\s*<PAGE>\s*$", md, flags=re.M)),
           "page_blocks": len(pages), "output_chars": len(md)}
    # document level: whole output vs whole truth (order-preserving), robust to missing markers
    prose_all, tabs_all = split_blocks(md)
    ref_prose = norm(" ".join(t["title"] + " " + t["paragraph"] for t in truth))
    res["doc_prose_cer"] = round(cer(ref_prose, prose_all), 4)
    if len(pages) == n_in:
        per = [score_page(t, p) for t, p in zip(truth, pages)]
    else:  # fewer/more blocks than pages: align by position, missing pages scored as empty
        per = [score_page(t, pages[i] if i < len(pages) else "") for i, t in enumerate(truth)]
    res["aligned_by_position"] = len(pages) != n_in
    for k in ("rows_present", "rows_exact", "rows_six_cells", "rows_total", "cells_pos_exact", "cells_value_found", "cells_total"):
        res[k] = sum(p[k] for p in per)
    res["pages_header_ok"] = sum(p["header_ok"] for p in per)
    res["pages_malformed_html"] = sum(p["malformed_html"] for p in per)
    res["pages_with_one_table"] = sum(p["n_tables"] == 1 for p in per)
    res["mean_page_prose_cer"] = round(sum(p["prose_cer"] for p in per) / n_in, 4)
    res["mean_page_table_cer"] = round(sum(p["table_cer"] for p in per) / n_in, 4)
    res["pages_nonempty"] = sum(1 for p in pages if p.strip())
    res["per_page"] = per
    print(json.dumps(res))


if __name__ == "__main__":
    main(*sys.argv[1:])
