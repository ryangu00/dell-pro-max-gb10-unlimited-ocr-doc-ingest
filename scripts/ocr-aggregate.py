"""Aggregate raw bench output: python3 ocr-aggregate.py RAWDIR truth.json score_script > results.json
RAWDIR/<label>/{meta.json,raw/<label>.{mem,stats,stdout},runs/<label>/out/result*.md}"""
import json, os, re, statistics as st, subprocess, sys, glob
from pathlib import Path
raw, truth, scorer = sys.argv[1:4]
UNIT = {"B": 1/2**30, "KiB": 1/2**20, "MiB": 1/2**10, "GiB": 1, "kB": 1/1e6*0.93132, "MB": 0.93132/1e3, "GB": 0.93132}
rows = []
for d in sorted(glob.glob(f"{raw}/*/meta.json")):
    m = json.loads(Path(d).read_text()); L = m["label"]; base = os.path.dirname(d)
    mem = [l.split() for l in Path(f"{base}/raw/{L}.mem").read_text().splitlines() if "WATCHDOG" not in l]
    kib = [int(x[1]) for x in mem]; t = [float(x[0]) for x in mem]
    inrun = [k for tt, k in zip(t, kib) if float(m["t0"]) <= tt <= float(m["t1"])]
    m["memavail_start_gib"] = round(kib[0] / 2**20, 1)
    m["memavail_min_gib"] = round(min(inrun) / 2**20, 1)
    m["peak_drop_gib"] = round((kib[0] - min(inrun)) / 2**20, 1)
    m["mem_samples"] = len(inrun)
    m["watchdog"] = any("WATCHDOG" in l for l in Path(f"{base}/raw/{L}.mem").read_text().splitlines())
    peak = 0.0
    for l in Path(f"{base}/raw/{L}.stats").read_text().splitlines():
        mm = re.match(r"\S+ ([\d.]+)(\w+) /", l)
        if mm: peak = max(peak, float(mm.group(1)) * UNIT[mm.group(2)])
    m["docker_stats_peak_gib"] = round(peak, 2)
    so = Path(f"{base}/raw/{L}.stdout").read_text()
    mm = re.search(r"\[load\] ([\d.]+)s", so); m["load_s"] = float(mm.group(1)) if mm else None
    mm = re.search(r"\[ocr\] (\d+) pages ([\d.]+)s", so)
    m["pages_reported"], m["ocr_s"] = (int(mm.group(1)), float(mm.group(2))) if mm else (None, None)
    m["sentinel"] = "UOCR_DONE" in so
    if m["ocr_s"] is not None:
        m["per_page_s"] = round(m["ocr_s"] / m["pages_reported"], 2)
        m["overhead_s"] = round(m["wall_s"] - m["load_s"] - m["ocr_s"], 1)
    n = int(re.search(r"scan(\d+)", m["pdf"]).group(1))
    mds = sorted(glob.glob(f"{base}/runs/{L}/out/**/result*.md", recursive=True))
    m["result_files"] = len(mds)
    if m["mode"] == "single_each":
        def key(path):
            found = re.search(r"/p(\d+)/|result_page(\d+)", path)
            return int(next(x for x in found.groups() if x))
        # The public converter also copies page results to the output root.
        top = [p for p in mds if re.search(r"/out/result_page\d+\.md$", p)]
        mds = sorted(top or mds, key=key)
        m["result_files"] = len(mds)
        body = "\n<PAGE>\n".join(Path(p).read_text() for p in mds)
    else:
        body = "\n".join(Path(p).read_text() for p in mds)
    if mds:
        tmp = f"{base}/combined.md"; Path(tmp).write_text(body)
        r = subprocess.run([sys.executable, scorer, truth, tmp, str(n)], capture_output=True, text=True)
        m["score"] = json.loads(r.stdout) if r.returncode == 0 else {"error": r.stderr[-300:]}
    rows.append(m)
print(json.dumps(rows, indent=1))
