# Measure the failure, then change the call

Measured on 2026-10-04 (UTC). Everything here comes from one idle GB10 node, one synthetic corpus and one container image. Nothing was run on real documents. Numbers are first-hand unless marked "derived".

## 1. What was measured and why

An earlier version of this book's fact sheet had three open gaps: OCR timing was known only for 1 and 3 pages (and only on private inputs), the peak memory of an OCR run was never measured, and the revision of the downloaded model was not recorded. The dated record fills those gaps with a corpus that can be regenerated, adds page coverage and quality against exact ground truth, and compares the single-page and multi-page model settings.

## 2. Setup

| Item | Value |
|---|---|
| Node | One Dell Pro Max with GB10 (aarch64, unified memory shared by CPU and GPU), driver 580.178.04, Docker 29.6.2 |
| State before every run | At least 115 GiB `MemAvailable`, zero running containers (checked before each run; the run would have been aborted below 40 GiB or if any container was running) |
| Container image | Local image of about 19 GB (162 layers, 38 of them non-empty; the five largest layers are about 5.3, 1.85, 1.77, 1.56 and 1.27 GB; the topmost layer, which holds the Python package installs, is 446 MB). Built on an NVIDIA NGC PyTorch base. Sizes only; torch and CUDA versions inside the image were not queried |
| Model | `baidu/Unlimited-OCR`, BF16, 6.4 GB on disk. Hugging Face cache metadata records commit `2a06ebf2d6f600f95fd2b99f6ccdee18a52e3b8f` for all 15 file records. This is not the upstream head observed on 2026-10-03 (a later commit; the upstream repository was modified after our download) |
| Container flags | Recorded container flags: `--rm --gpus all --ipc=host --memory=30g --memory-swap=30g`, workspace mounted at `/ws`. One addition: `--name`, so the container could be watched and, as a safety stop, killed if `MemAvailable` fell under 8 GiB (it never did) |
| Batch script | The historical batch script, unchanged for the main runs. The public converter shipped here instead uses per-page calls and hard validation failures. A PDF is rasterised at 300 dpi; one page uses the single-image setting (`base_size=1024, image_size=640, crop_mode=True`, prompt "document parsing", `ngram_window=128`); two or more pages use one multi-page call (`image_size=1024`, prompt "Multi page parsing", `ngram_window=1024`); `max_length=32768` in both |
| Variant script | For the settings comparison only: a copy with one environment switch that either forces the multi-page call on a one-page file or applies the single-image setting to each page in turn with one model load. Nothing else changed |
| Sampling | `MemAvailable` from `/proc/meminfo` once per second on the host for the whole run; `docker stats --no-stream` in a loop on the container (about one sample per 2 s); wall time taken on the node around the `docker run` (so SSH and file copy are not included) |
| Order | 1-page x3, 3-page x3, 10-page x2, 40-page x2, then the variant runs. All 16 runs back to back, about 25 minutes of node time |

### Corpus

Generated locally by a script (shipped with the book), seed fixed, never any real document. 40 pages, A4, rendered, converted to grey, skewed by up to +/-0.4 degrees, blurred, given paper tone and Gaussian noise, scanned-style at 200 dpi, embedded as JPEG (quality 85) in image-only PDFs with no text layer (verified: 0 extractable characters). The 1, 3, 10 and 40-page inputs are the first N pages of the same set, so ground truth is shared.

Every page holds:

- a title line ("Operations Report Section N"),
- one paragraph of about 800 characters of random words from a small vocabulary (so a language model cannot guess the words from context),
- one dense bordered table with a two-level header (a cell spanning two rows, a cell spanning three columns, a cell spanning two columns), 14 data rows and 6 columns, all labels unique to the page (84 data cells per page, 3,360 in the full set).

Ground truth is exact: the generator writes every string it renders to a JSON file. Scoring (shipped with the book) reads the OCR Markdown, splits it on the `<PAGE>` marker, and compares per page.

Metrics:

- **Prose CER**: character error rate of the text outside tables against title plus paragraph (whitespace normalised, tags removed).
- **Table text CER**: same for the text inside tables against header plus all cells.
- **Header survives**: the row-spanning cell and both column-spanning cells are present with the right spans.
- **Row present**: a data row whose first cell (the unique label) appears.
- **Row exact**: a present row whose cells equal the truth exactly (no missing, no extra cells).
- **Value found**: a truth cell whose text appears in its own OCR row.

Tables are read with a lenient regex reader because the model sometimes emits a malformed attribute that makes a strict HTML parser swallow the rest of the page.

## 3. Raw timing and memory, every run

"Other" is wall time minus model load minus OCR time: container start, 300 dpi rasterisation of the PDF, writing results. "Drop" is `MemAvailable` at the start of the run minus its minimum during the run. Docker peak is the largest `docker stats` memory figure sampled.

| Run | Pages | Wall s | Load s | OCR s | OCR s/page | Other s | Wall s/page | Drop GiB | Docker peak GiB |
|---|---|---|---|---|---|---|---|---|---|
| 1-page repeat 1 | 1 | 57.7 | 44.0 | 9.3 | 9.30 | 4.4 | 57.7 | 14.6 | 6.75 |
| 1-page repeat 2 | 1 | 57.9 | 44.1 | 9.4 | 9.40 | 4.4 | 57.9 | 14.1 | 6.75 |
| 1-page repeat 3 | 1 | 50.2 | 36.6 | 9.3 | 9.30 | 4.3 | 50.2 | 14.2 | 6.64 |
| 3-page repeat 1 | 3 | 74.7 | 44.4 | 23.6 | 7.87 | 6.7 | 24.9 | 13.6 | 6.67 |
| 3-page repeat 2 | 3 | 65.9 | 36.7 | 22.5 | 7.50 | 6.7 | 22.0 | 13.7 | 6.57 |
| 3-page repeat 3 | 3 | 67.1 | 37.8 | 22.6 | 7.53 | 6.7 | 22.4 | 13.9 | 6.72 |
| 10-page repeat 1 | 10 | 126.4 | 36.6 | 74.9 | 7.49 | 14.9 | 12.6 | 14.0 | 6.59 |
| 10-page repeat 2 | 10 | 127.2 | 37.3 | 75.0 | 7.50 | 14.9 | 12.7 | 14.4 | 6.79 |
| 40-page repeat 1 | 40 | 441.2 | 44.6 | 346.3 | 8.66 | 50.3 | 11.0 | 31.5 | 6.94 |
| 40-page repeat 2 | 40 | 432.1 | 44.0 | 337.9 | 8.45 | 50.2 | 10.8 | 31.7 | 6.91 |

Variant runs (settings comparison, section 6):

| Run | Setting | Pages | Wall s | Load s | OCR s | OCR s/page | Drop GiB |
|---|---|---|---|---|---|---|---|
| 1-page multi repeat 1 | multi-page call forced | 1 | 56.6 | 44.0 | 8.2 | 8.20 | 14.4 |
| 1-page multi repeat 2 | multi-page call forced | 1 | 57.5 | 44.8 | 8.3 | 8.30 | 13.7 |
| 1-page multi repeat 3 | multi-page call forced | 1 | 50.6 | 38.4 | 7.8 | 7.80 | 13.9 |
| 3-page single repeat 1 | single-image setting per page | 3 | 77.5 | 44.1 | 26.6 | 8.87 | 13.7 |
| 3-page single repeat 2 | single-image setting per page | 3 | 77.9 | 44.6 | 26.6 | 8.87 | 13.9 |
| 10-page single repeat 1 | single-image setting per page | 10 | 145.8 | 44.8 | 86.1 | 8.61 | 13.7 |

All 16 runs exited 0 and printed the completion sentinel. The memory watchdog never fired.

### Medians

| Pages | Runs | Median wall s | Median wall s/page | Median load s | Median OCR s | Median OCR s/page | Median other s |
|---|---|---|---|---|---|---|---|
| 1 | 3 | 57.7 | 57.7 | 44.0 | 9.3 | 9.30 | 4.4 |
| 3 | 3 | 67.1 | 22.4 | 37.8 | 22.6 | 7.53 | 6.7 |
| 10 | 2 | 126.8 | 12.7 | 37.0 | 75.0 | 7.50 | 14.9 |
| 40 | 2 | 436.7 | 10.9 | 44.3 | 342.1 | 8.56 | 50.3 |

Observations on timing:

- Model load took 36.6 to 44.8 s in every run and is bimodal (about 37 s or about 44 s) with no pattern by run order or page count. The cause was not isolated. An earlier log from 2026-07 shows a 14.0 s load for the same model on the same node; the driver and image state differ since then, so the two are not comparable.
- For a one-page file, only 9.3 s of a 50 to 58 s container run was OCR; the rest was model load plus container start and rasterisation. That is about 41 to 48 s that is not OCR, before any network copy. The earlier fact-sheet figure of "about 26 s fixed cost (superseded estimate)" (derived from two end-to-end runs on a private document) does not agree with this measurement.
- Once the model is loaded, OCR cost per page was about 7.5 s in the multi-page call for 3 and 10 pages (the single-page call took 9.3 s). From 3 to 10 pages the wall time grew 8.5 s per extra page (derived: (126.8 - 67.1) / 7).
- Rasterisation and container overhead ("other") grew with pages: 4.4, 6.7, 14.9 and 50.3 s for 1, 3, 10 and 40 pages, about 1.2 s per page.
- The 40-page time is not a throughput number. The output was a runaway generation (section 5), so the 342 s of OCR time is the cost of generating a long wrong answer.
- Run-to-run spread inside a page count was small apart from the load time (OCR time within about 1 s of each other for 1, 3 and 10 pages; 8 s apart at 40 pages).

## 4. Peak memory

| Pages | `MemAvailable` at start (GiB) | Minimum during run (GiB) | Drop (GiB) | When the minimum occurred | Docker memory peak (GiB) |
|---|---|---|---|---|---|
| 1 | 115.5 to 116.7 | 101.3 to 102.1 | 14.1 to 14.6 | about 47 s, just after model load | 6.64 to 6.75 |
| 3 | 115.1 to 115.3 | 101.4 to 101.6 | 13.6 to 13.9 | after model load | 6.57 to 6.72 |
| 10 | 115.3 to 116.4 | 101.3 to 102.1 | 14.0 to 14.4 | about 50 s | 6.59 to 6.79 |
| 40 | 116.3 to 116.6 | 84.8 to 85.0 | 31.5 to 31.7 | about 105 s, shortly after OCR began | 6.91 to 6.94 |

What this shows and does not show:

- For 1 to 10 pages the node lost about 14 GiB of available memory, reached once the model was loaded and flat afterwards (the one-page curve has the same minimum as the ten-page curve). The model file is 6.4 GB, so the 14 GiB includes more than the weights (CUDA context and working buffers); the split was not measured.
- For the 40-page input the drop was 31.5 to 31.7 GiB, more than twice as large, and reached early in the OCR phase. That is consistent with a large one-shot cost for encoding 40 pages in a single call; the cause was not isolated.
- `docker stats` never showed more than 6.94 GiB, even while the host lost 31.7 GiB. On this unified-memory node the container's own accounting therefore did not track what the node lost. The 31.7 GiB drop was above the 30 GiB `--memory` cap; in these runs the cap did not bound the host-level effect.
- A free-memory guard has to be judged against these numbers: 14 GiB for up to 10 pages of this corpus, and 31.7 GiB for 40 pages. A 32 GiB threshold would have left about 0.3 GiB of margin for the 40-page case. This is one corpus at one page density; a denser or sparser page may differ.
- `MemAvailable` counts reclaimable page cache as available, and sampling at 1 Hz can miss a brief spike. Treat the numbers as lower bounds on the true peak.
- GPU memory as reported by the GPU's own tool was not sampled (outside the authorised measurements).

## 5. Page coverage and quality against ground truth

Both runs of each page count produced byte-identical output files (1, 3, 10 and 40 pages). The 1 and 3-page outputs were also identical across the three runs. The model is deterministic enough here that a repeat run adds no information about quality; quality was therefore scored once per distinct output.

| Pages in | Page markers out | Prose CER | Table text CER (mean per page) | Header survives | Pages with exactly one table | Rows present / total | Rows exact / total | Truth cells found / total |
|---|---|---|---|---|---|---|---|---|
| 1 | 0 (single-page call writes no marker) | 0.0000 | 0.0000 | 1 / 1 | 1 / 1 | 14 / 14 | 14 / 14 | 84 / 84 |
| 3 | 3 | 0.0000 | 0.0000 | 3 / 3 | 3 / 3 | 42 / 42 | 42 / 42 | 252 / 252 |
| 10 | 10 | 0.0022 | 0.0731 | 6 / 10 | 9 / 10 | 138 / 140 | 70 / 140 | 774 / 840 |
| 40 | 1 | 1.0691 | 1.0000 | 0 / 40 | 0 / 40 | 0 / 560 | 0 / 560 | 0 / 3,360 |

### 1 and 3 pages

Perfect on this corpus: every character of prose, every cell of every table, both header spans. Page markers matched the page count for 3 pages.

### 10 pages: prose fine, tables damaged on 6 of 10 pages (5 structurally, 1 by a malformed attribute)

Every page produced output and all 10 markers were present, so a marker-count coverage check passes. The prose was nearly exact (CER 0.0022: a handful of character slips). The tables were not:

| Page | Header spans OK | Tables | Rows present | Rows exact | Truth cells found | What went wrong |
|---|---|---|---|---|---|---|
| 1 | yes | 1 | 14 | 14 | 84 | nothing |
| 2 | yes | 1 | 14 | 0 | 84 | every row has an extra empty seventh cell; all values correct |
| 3 | yes | 1 | 14 | 14 | 84 | nothing |
| 4 | yes | 1 | 14 | 14 | 84 | one malformed attribute in the header (`colspan='2"`); values correct, but a strict HTML parser mis-reads the page |
| 5 | yes | 1 | 14 | 14 | 84 | nothing |
| 6 | yes | 1 | 14 | 14 | 84 | nothing |
| 7 | no | 1 | 14 | 0 | 70 | last column missing from the header and from all 14 rows |
| 8 | no | 1 | 14 | 0 | 70 | last column missing, plus the malformed attribute |
| 9 | no | 1 | 13 | 0 | 65 | last column missing; one row label misread ("Barich-0904" for "Birch-0904") |
| 10 | no | 2 | 13 | 0 | 65 | table split into a header-only stub and a second table with a repeated header; last column missing; one label truncated ("Larch-000" for "Larch-1000") |

Of the cell text that did come out, the digits were right: the loss is structural (a dropped column, an extra column, a split table, a broken attribute) plus two misread labels, not noisy numbers. The failure is silent: exit code 0, sentinel present, ten page markers, no warning from the wrapper's coverage check.

### 40 pages: runaway generation, one page recovered

The 40-page output holds one `<PAGE>` marker and 38,983 characters. The first words of the first paragraph are correct, then the model leaves the page and writes a short sentence of unrelated text followed by an ascending list of parenthesised integers, "(1) (2) (3) ..." up to "(5691)", ending mid-token with no closing text. Pages 2 to 40 and all tables are absent. Both runs produced exactly the same file. The exit code was 0 and the sentinel was printed.

The same first page was transcribed perfectly when it was alone (1 page) or with two more (3 pages) and in the 10-page document, so the cause is the 40-page input as a whole, not that page. The size of the output (the model stops at a length limit; the batch script sets `max_length=32768`) is consistent with the run ending at the generation limit, but the token count was not recorded.

Where between 10 and 40 pages the multi-page call stops being reliable was not measured (no 20 or 25-page run was authorised). The failure was caught only by a marker-count comparison: reading the historical converter code, 1 marker against 40 source pages would print its "page coverage 1/40" warning, but the converter itself was not run end to end here, and its exit code stays 0.

## 6. Single-page versus multi-page settings

Same pages, same node, different call. "Truth cells found" uses the same ground truth as section 5.

| Input | Setting | Runs | OCR s/page | Prose CER | Truth cells found | Rows exact |
|---|---|---|---|---|---|---|
| 1 page | single-image setting (historical default) | 3 | 9.30 | 0.0000 | 84 / 84 | 14 / 14 |
| 1 page | multi-page call forced | 3 | 8.2, 8.3, 7.8 | 0.0061 | 84 / 84 | 14 / 14 |
| 3 pages | multi-page call (historical default) | 3 | 7.5 to 7.9 | 0.0000 | 252 / 252 | 42 / 42 |
| 3 pages | single-image setting per page, one model load | 2 | 8.87 | 0.0000 | 252 / 252 | 42 / 42 |
| 10 pages | multi-page call (historical default) | 2 | 7.50 | 0.0022 | 774 / 840 | 70 / 140 |
| 10 pages | single-image setting per page, one model load | 1 | 8.61 | 0.0000 | 840 / 840 | 140 / 140 |

- At 10 pages the single-image setting applied page by page was perfect (all 840 cells, all 140 rows, all 10 headers, prose CER 0) at about 15 % more OCR time per page than the multi-page call (8.61 s against 7.50 s). Only one run of this variant was made.
- For one page, the multi-page call forced on a single page was slightly faster per page and its prose had one 6-character substitution ("across area" for "across a"); tables were perfect in both. Three runs each, identical outputs within each setting.
- At 3 pages the two settings tied on quality; the multi-page call was about 15 % faster per page.
- Both settings share the same container start and model load, so per-invocation overhead is unchanged. The variant loads the model once and loops, so it does not pay the load per page; calling the wrapper once per page would pay a full container start plus a model load (about 41 to 48 s non-OCR in this run) for every page.

## 7. What the numbers show

- On this corpus the OCR path is accurate and structure-faithful for 1 and 3 pages (zero errors in 336 table cells and about 3,300 prose characters).
- OCR time once the model is loaded is about 7.5 to 9.3 s per page, close to the earlier "about 9 s per page" estimate. The fixed per-invocation cost is not 26 s: model load alone was 37 to 45 s here.
- Memory needed was about 14 GiB for runs of up to 10 pages and about 32 GiB for the 40-page run, measured as the fall in the node's available memory. Container accounting under-reported both.
- Multi-page mode degrades silently as page count grows: damaged tables on 6 of 10 pages at 10 pages (5 with wrong structure, 1 with a malformed attribute), and one recovered page out of 40 at 40 pages. A count of page markers catches the second but not the first.
- Applying the single-image setting page by page avoided the table damage at 10 pages, at a time cost of about 15 % per page.

## 8. What the numbers do not show

- **One synthetic layout.** Bordered tables with a fixed header shape and random-word prose at about 800 characters per page. A different layout, density, language, scan quality or handwriting can change every number. A page with less text may tolerate more pages per call; a denser one fewer. No claim is made about real documents.
- **One seed, one image, one node, one driver version.** Repeat runs here were deterministic (identical output files), so the repeats confirm timing, not the quality result. Results with a different model commit, image, or driver may differ. The model commit used here is not the current upstream head.
- **The break point for multi-page mode is unknown.** Only 1, 3, 10 and 40-page multi-page cases were run. The 10-page result was already damaged; the 40-page result was a collapse; nothing between was tested.
- **The single-image 10-page benchmark result is one run.** Per-page OCR at 10 and 40 pages was also run once each through the production converter on 2026-10-04 (see the production follow-up in [results](results.md)); per-page OCR beyond 40 pages was not measured.
- **Cause of the 40-page collapse and of the dropped columns is not established.** The data show the failure and its repeatability, not why.
- **The benchmark did not measure end-to-end converter time.** These are container runs on the node; SSH, file copy up and result copy back are not included. The production follow-up in [results](results.md) does measure end-to-end time for the per-page converter (149 s for 10 pages, 432 s for 40 pages, one run each). The historical converter itself was not run, so its warnings and exit codes at 10 and 40 pages are read from its code, not observed. The public adaptation fails on a coverage mismatch and has offline mock tests only.
- **Cold start was not isolated.** Runs went back to back; a first-ever model load after a long idle may be slower.
- **The 32 GiB guard** in the converter is judged against a single corpus; it is not a safe-for-all-documents number.
- **GPU-side memory and the software versions inside the image** (PyTorch, CUDA) were not measured or queried.
- **No comparison with the text-extraction engine's accuracy on this corpus** was done, because the corpus has no text layer; that engine returns nothing for it by construction.
- **Both production runs used the converter version before a final review fix** (copy-back failure handling and the warning matcher); that fix does not touch the success path. The final version was run end to end only on a 3-page scan (252/252 cells, 42/42 rows, CER 0.000).
- **Documents longer than 40 pages, real (non-synthetic) documents, and a page-count mismatch on real hardware** were not tested.
- **Per-page results at 10 and 40 pages are each one run**; repeatability is not established.

## 9. Cleanup and reproducibility

The run directory on the node holding the input PDFs, the variant script and the raw logs was removed after the last run, and it was verified absent. No container was left (all runs used `--rm`; none running afterwards, none listed). Available memory returned to about 116 GiB. No other file or service on the node was touched. The corpus generator, scorer, and aggregator are shipped. The fixed seed reconstructs the ground-truth construction; pixel-identical rendering also depends on unrecorded rendering dependencies. This repository includes numerical run records and per-page scores in `results/measurements.json`, not the original OCR output files or raw monitoring logs.

## Reproducing the analysis

The scorer uses the exact strings from `truth.json`, not a visual judgement.
Whitespace is normalized; prose and table text are compared separately.
The regex table reader deliberately tolerates malformed attributes so that a syntax error does not hide every later cell.
This is a measurement choice; the converter's separate validator rejects malformed HTML.
Document-level CER remains order-preserving when markers disappear.
Per-page scores align by position; missing pages are scored as empty.
CER can exceed one when insertions dominate, as in the runaway output.

Run the small synthetic reference without optional dependencies:

```sh
python3 scripts/ocr-score.py fixtures/truth.json fixtures/perfect.md 1
```

The reference Markdown is generated HTML with known content, not a newly observed model result.
`rapidfuzz` accelerates Levenshtein distance if installed; otherwise the scorer uses an exact stdlib fallback.
The fallback is intended to keep small offline checks usable, not to promise fast long-document scoring.

The aggregator accepts a directory containing this layout for each run label:

```text
collected/
  sample/
    meta.json
    raw/
      sample.mem
      sample.stats
      sample.stdout
    runs/
      sample/
        out/
          p001/result.md
```

`meta.json` supplies `label`, `pdf` (such as `scan1.pdf`), `mode`, `rc`, `wall_s`, `t0`, and `t1`.
Use `mode=single_each` for per-page results; `auto` describes the original default and `multi_force` the forced multi-page comparison.
Memory rows are timestamp and available KiB; stats rows are timestamp and the Docker memory-use expression.
The stdout log contains `[load]`, `[ocr]`, and the completion sentinel.
The aggregator also handles the public converter's top-level `result_pageNNN.md` copies without double-counting the nested originals.
It writes `combined.md` in each supplied run directory, then invokes the scorer with the current interpreter.
It does not contact a node or collect metrics itself.

```sh
python3 scripts/ocr-aggregate.py collected fixtures/benchmark/truth.json \
  scripts/ocr-score.py > collected-results.json
```

The original raw logs and OCR Markdown were not supplied as publishable repository inputs, so the historical aggregate cannot be regenerated here from raw logs.
The numerical JSON preserves all supplied non-identifying metrics and per-page scores; absolute timestamps and run labels are omitted.
Tables retain the source's displayed precision, while JSON retains raw precision.
For example, a displayed wall value may have fewer decimals than its raw JSON value; the book does not silently recompute those displays.

## The rule

**Problem:** a short-file success concealed a scale-dependent failure.
**Mechanism:** measure coverage, structural recovery, text accuracy, and time separately.
**Procedure:** retain a common synthetic ground truth across page-count and call-setting variants.
**What did not work:** a process return code, completion sentinel, and page markers were insufficient at 10 pages.
**Rule:** infer per page within one model load, then require recovered pages and validate the expected table shape before accepting output.
The per-page 40-page case was measured once; the causes of the multi-page failures remain open, and per-page OCR beyond 40 pages was not tested.
