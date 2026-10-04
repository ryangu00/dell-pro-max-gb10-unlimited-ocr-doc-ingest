#!/usr/bin/env python3
"""doc2md-batch DIR OUT: run doc2md on every file under DIR, write OUT/report.tsv.
Every input gets exactly one row (ok | partial | failed); exit code 1 if any row is not ok.
`python3 doc2md-batch.py --selftest` runs a stub-engine check that touches no network."""
import argparse, csv, os, re, subprocess, sys, tempfile, time
from pathlib import Path

def run(src_dir, out_dir, doc2md="doc2md"):
    src_dir, out_dir = os.path.realpath(src_dir), os.path.realpath(out_dir)
    if not os.path.isdir(src_dir):
        raise ValueError("input directory not found")
    if os.path.commonpath([src_dir, out_dir]) == src_dir:
        raise ValueError("output directory must be outside input directory")
    if os.path.exists(os.path.join(out_dir, "report.tsv")):
        raise ValueError("report.tsv already exists - refusing overwrite")
    rows = []
    os.makedirs(out_dir, exist_ok=True)
    for root, dirs, files in os.walk(src_dir):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for name in sorted(files):
            if name.startswith("."):
                continue  # hidden files only; everything else is attempted, never skipped
            src = os.path.join(root, name)
            rel = os.path.relpath(src, src_dir)
            out = os.path.join(out_dir, rel + ".md")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            t0 = time.time()
            command = [sys.executable, doc2md] if doc2md.endswith("/doc2md") else [doc2md]
            try:
                r = subprocess.run(command + [src, "-o", out], capture_output=True, text=True)
            except OSError as exc:
                r = subprocess.CompletedProcess([], 1, "", str(exc))
            err = r.stderr
            m = re.search(r"engine=(\w+) \((.*)\)", err)
            size = os.path.getsize(out) if os.path.exists(out) else 0
            if r.returncode != 0 or size == 0:
                status, note = "failed", (err.strip().splitlines() or ["no output"])[-1][:200]
            elif "coverage" in err or "partial" in err:
                status, note = "partial", next((l for l in err.splitlines() if "warn" in l), "partial output")[:200]
            else:
                status, note = "ok", next((l[:200] for l in reversed(err.splitlines()) if "warn" in l), "")
            rows.append([rel, status, m.group(1) if m else "", m.group(2) if m else "", size, f"{time.time()-t0:.1f}", note])
    with open(os.path.join(out_dir, "report.tsv"), "w", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["path", "status", "engine", "reason", "out_bytes", "seconds", "note"])
        w.writerows(rows)
    bad = [r for r in rows if r[1] != "ok"]
    print(f"{len(rows)} files, {len(bad)} not ok -> {os.path.join(out_dir, 'report.tsv')}", file=sys.stderr)
    return len(bad)

def selftest():
    stub = r'''#!/bin/sh
src="$1"; out="$3"
case "$src" in
  *good*)    echo "[doc2md] engine=markitdown (stub)" >&2; echo "# ok" > "$out" ;;
  *partial*) echo "[doc2md] engine=ocr (stub)" >&2; echo "[doc2md] warn: OCR page coverage 1/3 - output may be partial" >&2; echo "x" > "$out" ;;
  *empty*)   echo "[doc2md] engine=markitdown (stub)" >&2; : > "$out" ;;
  *)         echo "cannot open PDF (x)" >&2; exit 1 ;;
esac
'''
    with tempfile.TemporaryDirectory(dir=".") as t:
        os.makedirs(f"{t}/in/sub")
        for n in ("good.docx", "sub/partial.pdf", "empty.pdf", "broken.pdf", ".hidden"):
            Path(f"{t}/in/{n}").write_text("x")
        Path(f"{t}/stub").write_text(stub); os.chmod(f"{t}/stub", 0o755)
        bad = run(f"{t}/in", f"{t}/out", f"{t}/stub")
        got = {r[0]: r[1] for r in csv.reader(Path(f"{t}/out/report.tsv").read_text().splitlines(), delimiter="\t")}
        assert got == {"path": "status", "good.docx": "ok", "sub/partial.pdf": "partial",
                       "empty.pdf": "failed", "broken.pdf": "failed"}, got
        assert bad == 3
    print("selftest OK")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?")
    parser.add_argument("output", nargs="?")
    parser.add_argument("--converter", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "doc2md"))
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        selftest()
    elif args.source and args.output:
        try:
            sys.exit(1 if run(args.source, args.output, args.converter) else 0)
        except (ValueError, OSError) as exc:
            parser.exit(1, str(exc) + "\n")
    else:
        parser.error("source and output are required unless --selftest is used")
