# Results and evidence conditions

The OCR tables are the dated synthetic measurements from 2026-10-04.
They are historical GPU observations, not results of executing this repository's adapted converter.
`results/measurements.json` retains the supplied numeric precision and per-page scores.
Run labels and absolute timestamps are omitted from that public JSON; repeats below are identified descriptively.
The displayed table precision is preserved from the measurement record rather than recalculated.
All repeat runs exited 0 and printed `UOCR_DONE`; the watchdog never fired.

## Measurement setup

Conditions: one Dell Pro Max with GB10; 2026-10-04; synthetic scans only; no other running container.

| Item | Value |
|---|---|
| Node | One Dell Pro Max with GB10 (aarch64, unified memory shared by CPU and GPU), driver 580.178.04, Docker 29.6.2 |
| State before every run | At least 115 GiB `MemAvailable`, zero running containers (checked before each run; the run would have been aborted below 40 GiB or if any container was running) |
| Container image | Local image of about 19 GB (162 layers, 38 of them non-empty; the five largest layers are about 5.3, 1.85, 1.77, 1.56 and 1.27 GB; the topmost layer, which holds the Python package installs, is 446 MB). Built on an NVIDIA NGC PyTorch base. Sizes only; torch and CUDA versions inside the image were not queried |
| Model | `baidu/Unlimited-OCR`, BF16, 6.4 GB on disk. Hugging Face cache metadata records commit `2a06ebf2d6f600f95fd2b99f6ccdee18a52e3b8f` for all 15 file records. This is not the upstream head observed on 2026-10-03 (a later commit; the upstream repository was modified after our download) |
| Container flags | Same as the converter wrapper: `--rm --gpus all --ipc=host --memory=30g --memory-swap=30g`, workspace mounted at `/ws`. One addition: `--name`, so the container could be watched and, as a safety stop, killed if `MemAvailable` fell under 8 GiB (it never did) |
| Batch script | Historical script for the main runs; the shipped public adaptation uses per-page calls. A PDF is rasterised at 300 dpi; one page uses the single-image setting (`base_size=1024, image_size=640, crop_mode=True`, prompt "document parsing", `ngram_window=128`); two or more pages use one multi-page call (`image_size=1024`, prompt "Multi page parsing", `ngram_window=1024`); `max_length=32768` in both |
| Variant script | For the settings comparison only: a copy with one environment switch that either forces the multi-page call on a one-page file or applies the single-image setting to each page in turn with one model load. Nothing else changed |
| Sampling | `MemAvailable` from `/proc/meminfo` once per second on the host for the whole run; `docker stats --no-stream` in a loop on the container (about one sample per 2 s); wall time taken on the node around the `docker run` (so SSH and file copy are not included) |
| Order | 1-page x3, 3-page x3, 10-page x2, 40-page x2, then the variant runs. All 16 runs back to back, about 25 minutes of node time |

## Raw timing and memory

Conditions: original single-image setting for 1 page, multi-page for larger inputs; node-side container wall clock excludes SSH/SCP; memory sampled throughout.

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

## Variant runs

Conditions: same node, corpus, image, and revision; variants change only the call setting; 2026-10-04.

| Run | Setting | Pages | Wall s | Load s | OCR s | OCR s/page | Drop GiB |
|---|---|---|---|---|---|---|---|
| 1-page multi repeat 1 | multi-page call forced | 1 | 56.6 | 44.0 | 8.2 | 8.20 | 14.4 |
| 1-page multi repeat 2 | multi-page call forced | 1 | 57.5 | 44.8 | 8.3 | 8.30 | 13.7 |
| 1-page multi repeat 3 | multi-page call forced | 1 | 50.6 | 38.4 | 7.8 | 7.80 | 13.9 |
| 3-page single repeat 1 | single-image setting per page | 3 | 77.5 | 44.1 | 26.6 | 8.87 | 13.7 |
| 3-page single repeat 2 | single-image setting per page | 3 | 77.9 | 44.6 | 26.6 | 8.87 | 13.9 |
| 10-page single repeat 1 | single-image setting per page | 10 | 145.8 | 44.8 | 86.1 | 8.61 | 13.7 |

## Medians

Conditions: medians of the original-setting runs above; the failed 40-page generation is not usable throughput.

| Pages | Runs | Median wall s | Median wall s/page | Median load s | Median OCR s | Median OCR s/page | Median other s |
|---|---|---|---|---|---|---|---|
| 1 | 3 | 57.7 | 57.7 | 44.0 | 9.3 | 9.30 | 4.4 |
| 3 | 3 | 67.1 | 22.4 | 37.8 | 22.6 | 7.53 | 6.7 |
| 10 | 2 | 126.8 | 12.7 | 37.0 | 75.0 | 7.50 | 14.9 |
| 40 | 2 | 436.7 | 10.9 | 44.3 | 342.1 | 8.56 | 50.3 |

## Host and container memory

Conditions: original-setting runs; host samples at 1 Hz, Docker samples about every 2 s; sampled drops are lower bounds on true peaks.

| Pages | `MemAvailable` at start (GiB) | Minimum during run (GiB) | Drop (GiB) | When the minimum occurred | Docker memory peak (GiB) |
|---|---|---|---|---|---|
| 1 | 115.5 to 116.7 | 101.3 to 102.1 | 14.1 to 14.6 | about 47 s, just after model load | 6.64 to 6.75 |
| 3 | 115.1 to 115.3 | 101.4 to 101.6 | 13.6 to 13.9 | after model load | 6.57 to 6.72 |
| 10 | 115.3 to 116.4 | 101.3 to 102.1 | 14.0 to 14.4 | about 50 s | 6.59 to 6.79 |
| 40 | 116.3 to 116.6 | 84.8 to 85.0 | 31.5 to 31.7 | about 105 s, shortly after OCR began | 6.91 to 6.94 |

## Coverage and quality

Conditions: one score per distinct output, identical across repeats within each setting; original calls; exact synthetic ground truth.

| Pages in | Page markers out | Prose CER | Table text CER (mean per page) | Header survives | Pages with exactly one table | Rows present / total | Rows exact / total | Truth cells found / total |
|---|---|---|---|---|---|---|---|---|
| 1 | 0 (single-page call writes no marker) | 0.0000 | 0.0000 | 1 / 1 | 1 / 1 | 14 / 14 | 14 / 14 | 84 / 84 |
| 3 | 3 | 0.0000 | 0.0000 | 3 / 3 | 3 / 3 | 42 / 42 | 42 / 42 | 252 / 252 |
| 10 | 10 | 0.0022 | 0.0731 | 6 / 10 | 9 / 10 | 138 / 140 | 70 / 140 | 774 / 840 |
| 40 | 1 | 1.0691 | 1.0000 | 0 / 40 | 0 / 40 | 0 / 560 | 0 / 560 | 0 / 3,360 |

## Ten-page table damage

Conditions: 10-page multi-page output on 2026-10-04; both runs byte-identical; all page markers present.

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

## Call-setting comparison

Conditions: common synthetic prefixes and ground truth; OCR-only time excludes load; 10-page per-page result observed once.

| Input | Setting | Runs | OCR s/page | Prose CER | Truth cells found | Rows exact |
|---|---|---|---|---|---|---|
| 1 page | single-image setting (historical default) | 3 | 9.30 | 0.0000 | 84 / 84 | 14 / 14 |
| 1 page | multi-page call forced | 3 | 8.2, 8.3, 7.8 | 0.0061 | 84 / 84 | 14 / 14 |
| 3 pages | multi-page call (historical default) | 3 | 7.5 to 7.9 | 0.0000 | 252 / 252 | 42 / 42 |
| 3 pages | single-image setting per page, one model load | 2 | 8.87 | 0.0000 | 252 / 252 | 42 / 42 |
| 10 pages | multi-page call (historical default) | 2 | 7.50 | 0.0022 | 774 / 840 | 70 / 140 |
| 10 pages | single-image setting per page, one model load | 1 | 8.61 | 0.0000 | 840 / 840 | 140 / 140 |

## Text-engine probes

Conditions: generated documents, client Mac, markitdown 0.1.6, 2026-10; timings include process startup; only digital and scanned controls have three timed runs.

| Input (synthetic) | markitdown 0.1.6 result | Exit code | Time (3 runs) |
|---|---|---|---|
| 10-page digital PDF, about 2,000 characters per page, merged-cell table on 4 pages | 19,988 bytes, zero newlines in the output; the table came out as one fused run of text, `Region2025Q1Q2North120135South98101`; pages separated by a form-feed character (`\x0c`), not a heading | 0 | 0.76, 0.74, 0.78 s (process start included; about 0.075 s per page) |
| Same 10 pages rasterized (image-only PDF) | 1 byte (a newline) | **0** | 0.38, 0.37, 0.41 s |
| 9-page mixed PDF (8 digital pages plus 1 image-only page) | 15,984 bytes: the 8 digital pages, the image page absent; no warning | **0** | not timed |
| `.xlsx` with integer cells and blank cells | integers rendered as floats (`3` became `3.0`, `1` became `1.0`); every blank cell rendered as the string `NaN`; a merged range produced an extra all-`NaN` row | 0 | not timed |
| `.docx` with a 3x2 table whose first row is a header | table emitted with an **empty header row** (`|  |  |`) and the real header demoted to the first body row; heading and paragraph correct | 0 | not timed |
| PNG, `.tif`, `.gif` | empty (whitespace-only) output | 0 | not timed |

## Routing rule

Conditions: decision order in the historical and public wrappers; thresholds are starting rules, not calibrated estimates.

| Condition (evaluated top to bottom) | Engine | Warning |
|---|---|---|
| average < 200 | OCR | none ("scanned") |
| 200 <= average < 600 | OCR | yes ("mixed or low text layer") |
| average >= 600 and minimum page < 50 | OCR | yes ("mixed PDF") |
| otherwise (average >= 600 and minimum page >= 50) | markitdown | none |

## Routing corpus

Conditions: synthetic PDFs, local routing with both engines stubbed, 2026-10; no OCR host involved.

| Synthetic file | Pages | Average chars/page | Minimum page | Decision |
|---|---|---|---|---|
| `digital10.pdf` | 10 | 2019 | 2000 | markitdown |
| `scanned10.pdf` (image-only) | 10 | 0 | 0 | OCR (scanned) |
| `mixed9.pdf` (8 text pages + 1 image page) | 9 | 1794 | 0 | OCR (mixed) |
| `slides400.pdf` | 8 | 418 | 400 | OCR (low-confidence band, warning) |
| `band_just_above.pdf` (about 700 chars/page) | 6 | 716 | 700 | markitdown |
| `titlepage_dense.pdf` (14-char title page + 7 dense pages) | 8 | 1315 | 14 | **OCR (mixed)**: a false positive |
| `blank1.pdf` | 1 | 0 | 0 | OCR |
| `broken.pdf` (not a PDF) | n/a | n/a | n/a | exit 1: `cannot open PDF (...)`; no engine is invoked |

## Routing boundaries

Conditions: chosen values supplied to the decision function, 10 pages assumed; these are test inputs, not observed document densities.

| Average | Minimum | Engine | Warning |
|---|---|---|---|
| 0 | 0 | OCR | no |
| 199 | 199 | OCR | no |
| 200 | 200 | OCR | yes |
| 599 | 300 | OCR | yes |
| 600 | 600 | markitdown | no |
| 600 | 49 | OCR | yes |
| 600 | 50 | markitdown | no |
| 5000 | 0 | OCR | yes |
| 5000 | 49 | OCR | yes |
| 5000 | 50 | markitdown | no |

## Historical failure signatures

Conditions: historical wrapper behavior as recorded; these are message/exit contracts, not new GPU runs. The public converter hard-fails incomplete recovery and refuses existing destinations.

| Situation | Exit | Message prefix | Output written? |
|---|---|---|---|
| Input not found | 1 | `not found: <path>` | no |
| Output equals input | 1 | `output would overwrite input (...)` | no |
| Not a PDF / damaged PDF | 1 | `cannot open PDF (<name>): ...` | no |
| Password-protected PDF | 1 | `PDF is password-protected: <name>` | no |
| `--max-pages` below 1 | 2 | `argument --max-pages: must be >= 1` | no |
| Text engine fails | 1 | `markitdown failed: <stderr, 300 chars>` | no |
| Text engine returns nothing | 1 | `markitdown produced empty output - refusing to write empty markdown` | no |
| OCR host unreachable | 1 | `OCR host unreachable (<host>): ...` | no |
| Free memory below the guard (Chapter 5) | 1 | `<host> ... GiB < <need> GiB ... OCR refuses to run` | no |
| OCR container fails or no sentinel | 1 | `OCR run failed (rc=<n>): <last 400 chars>` | no |
| OCR produced no result file | 1 | `OCR produced no result*.md (scp: ...)` | no |
| OCR result empty | 1 | `OCR output is empty - refusing to write empty markdown` | no |
| OCR returned fewer page markers than source pages | 0 | stderr: `warn: OCR page coverage x/y - output may be partial` | yes |
| Mixed or low text layer routed to OCR | 0 | stderr: `warn: mixed ...` | yes |

## Historical guard and cleanup checks

Conditions: dates shown per row; generic host availability and cleanup observations, not present machine state.

| Check | Result | Date |
|---|---|---|
| `MemAvailable` on the GB10 under another workload | about 24 GiB | 2026-09-24 |
| Guard behaviour at 24 GiB, threshold 32 | refused, exit 1 | 2026-09-24 |
| Stale remote job directories after the pre-fix failures | 5 found, owned by root; 0 after the fixes | 2026-07-22 |
| Wrapper `--help` under `env -i PATH=/usr/bin:/bin` | failed before the shebang fix, exit 0 after (re-run by the second reviewer) | 2026-07-22 |

## Container bring-up

Conditions: 2026-07-21 dependency launches; private-input timing details are replaced by the later synthetic measurement tables. The historical 14.0 s model load is not comparable to the 2026-10-04 state.

| # | Change before the launch | First failing line (or result) |
|---|---|---|
| 1 | Bare NGC image, run the script | `ModuleNotFoundError: No module named 'transformers'` |
| 2 | `pip install transformers pymupdf` (latest) | `ImportError: This modeling file requires the following packages that were not found in your environment: addict. Run pip install addict` |
| 3 | `+ addict easydict einops matplotlib` (still latest transformers) | `ImportError: cannot import name 'is_torch_fx_available' from 'transformers.utils.import_utils'` |
| 4 | Stop guessing after three crashes; read the model README; pin `transformers==4.57.1 pymupdf==1.27.2.2` | `ModuleNotFoundError: No module named 'torchao.prototype.safetensors.safetensors_utils'` |
| 5 | `pip uninstall -y torchao` before the installs | Working environment; model load `[load] 14.0s` |

## Wrapper defect ledger

Conditions: independent historical reviews, 2026-07-22 unless noted; A/B identify reviews only. Reproduction status is per finding. Private-input detail is omitted.

| Finding | Review | Reported severity | Historical fix | Historical evidence |
|---|---|---|---|---|
| Quote in filename breaks the remote shell | A | critical | Controlled remote name `input.<ext>` | Quote-bearing filename converted after the fix |
| Damaged PDF raises raw traceback | A | critical | Catch open errors; distinguish password protection | Invalid-PDF refusal repeated in 2026-10 |
| Temporary directories leak on failure | A | critical | `try/finally`; remote deletion with noninteractive privileged fallback | 5 stale directories found; 0 after a successful corrected run |
| Alphabetical merge could order page10 before page2 | A | critical, as reported | Natural-number sorting | Reasoning only; original multi-page output was a single file |
| Empty OCR output or failed copy can produce an empty destination | A | critical | Check transfer and reject empty body | Code-path review only |
| Output equal to input overwrites source | B | high | Resolve paths and reject equality | Reproduced after the fix; rechecked in 2026-10 |
| Empty text-engine success is accepted; writes are not atomic | B | high | Reject empty stdout; temporary file and atomic replacement | Stub returned nothing; no output file was created |
| Front-only average misses mixed PDFs | B | high | Sample up to 100 pages; inspect minimum | Mixed 9-page synthetic fixture selected OCR |
| Extension can carry shell syntax | B | medium | Require `^\.[a-z0-9]{1,8}$`; otherwise `.bin` | Code-path review only |
| Sentinel alone ignores return code and completeness | B | medium | Require return code 0 and sentinel; warn on low coverage | Code-path review only |
| Nonpositive page cap accepted | B | low | Positive-integer argument | Exit 2 rechecked in 2026-10 |
| Host layout fixed in source | B | low | Not fixed in the historical wrapper | No portability validation |

## Downstream seam

Conditions: historical generic seam fixes rechecked on 2026-07-22; public example has a mock store only.

| Reproduced issue | Corrected behavior |
|---|---|
| Unescaped metadata scalar | JSON encoding preserves the title |
| Failed query treated as missing | Lookup error aborts |
| Dry-run skipped existence | Existing destination yields a would-refuse warning |
| Temporary body leaked after failed write | Removal in `finally` |
| Colliding target | Still refused after the fixes |

## Hardware and software

Conditions: historical runtime and 2026-10-04 measurement settings; public client pin is an adaptation, not a new GPU observation.

| Role or component | Recorded setting |
|---|---|
| OCR hardware | One Dell Pro Max with GB10, aarch64; CPU and GPU share unified memory |
| Client | Apple silicon Mac running the wrapper, markitdown, and PyMuPDF; no client GPU required |
| Transport | SSH/SCP over a private LAN; the public wrapper requires a configured remote host |
| Driver / Docker | 580.178.04 / 29.6.2 for the synthetic OCR measurements |
| Model | Baidu Unlimited-OCR, `baidu/Unlimited-OCR`, BF16; 6.4 GB on disk; MIT |
| Model revision | `2a06ebf2d6f600f95fd2b99f6ccdee18a52e3b8f`, recorded in all 15 cache file records |
| Runtime | `transformers==4.57.1`, `pymupdf==1.27.2.2`, plus unpinned `addict easydict einops matplotlib` |
| Base image | `nvcr.io/nvidia/pytorch:25.10-py3`; PyTorch and CUDA versions inside the measured image were not queried |
| Image construction | Interactive installs followed by `docker commit`; about 19 GB; supplied Dockerfile equivalent is unbuilt |
| Text engine | `markitdown==0.1.6`, MIT; client PyMuPDF resolved to 1.28.2 with `uv` 0.11.14 in 2026-10 |
| Public client pin | `pymupdf==1.28.2`; uses `import pymupdf` |
| Container flags | `--rm --gpus all --ipc=host --memory=30g --memory-swap=30g` |

## Image and model artifacts

Conditions: download observation dated 2026-07-21; layer inspection from the 2026-10-04 setup; disk estimate is approximate.

| Artifact | Recorded detail |
|---|---|
| Model download | 20 files, 6.4 GB, about 2 minutes on 2026-07-21 |
| Image | About 19 GB; 162 layers, 38 non-empty |
| Largest layers | About 5.3, 1.85, 1.77, 1.56, and 1.27 GB |
| Topmost package-install layer | 446 MB |
| Estimated provisioning disk | About 26 GB for model plus image |

## Interpreting the numbers

"Other" is wall time minus model load minus OCR time.
Wall time here excludes SSH and file transfer; all runs were measured on the node.
The original 40-page setting produced a failed generation, so its wall/page figure is not successful throughput.
The host drop is a sampled lower bound, and container memory is a separately sampled quantity.
The 32 GiB guard leaves about 0.3 GiB above the 31.7 GiB host drop; its adequacy for other layouts is unknown.

The historical estimate of about 26 s fixed cost is superseded: measured model load alone was 36.6-44.8 s.
Old private-input timing rows are not reproduced; the later synthetic tables supply the publishable comparison.
The original empty-output, partial-output, and warning signatures are documented as historical contracts.
The public wrapper instead requires exact recovered-page coverage and validates table shape before publishing.

For the ten-page table, "header spans OK" can coexist with malformed HTML because scoring deliberately reads attributes leniently.
The malformed-quote failure on page 4 is still an output defect even though every row value is recovered.
The page-8 output combines a malformed attribute with structural loss.
That is why the source describes 6 damaged pages: 5 structurally and 1 additional malformed-only page.

The synthetic settings comparison does not establish a general multi-page break point, per-page performance at 40 pages, or root causes.
The model-load bimodality and the difference from the historical 14.0 s load remain unexplained.
