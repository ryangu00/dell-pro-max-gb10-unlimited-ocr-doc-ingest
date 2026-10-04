# A converter that refuses to lie

## Problem

The original wrapper's happy paths passed while its failure paths could still damage or shorten output.
Two independent reviews found partially overlapping problems.
This chapter records the findings without reproducing review briefs, private inputs, or implementation identities.

## Historical defect ledger

Conditions: wrapper reviews and fixes on 2026-07-22 unless a later recheck is stated; evidence is per finding, not a blanket validation claim.

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

The sorting finding was defensive: the historical multi-page model emitted one `result.md`, so no observed page-file misordering was established.
The historical coverage fix warned and still published partial output.
That behavior is superseded by the public converter's hard coverage failure.
Historical findings about empty OCR, ordering, extension handling, and coverage were not individually rerun at the time.
The new offline suite tests those code paths with mocks; it does not retroactively change the historical evidence.

## Public implementation and procedure

1. Parse arguments and reject a missing input, nonpositive cap, source alias, or existing destination.
2. Route from the extension or sampled PDF text density; print the engine and reason to stderr.
3. For OCR, require `DOC2MD_OCR_HOST` and `DOC2MD_OCR_HOME`; no default host is embedded.
4. Check remote `MemAvailable`; an unreachable host, malformed number, or insufficient memory stops the job.
5. Create a fresh local temporary directory beside the output and a controlled remote job directory.
6. Copy the source to `input.<ext>` using a subprocess argument list.
7. Run the configured image with the recorded memory flags and the per-page batch script.
8. Require return code 0 and a standalone `UOCR_DONE` line.
9. Fetch `result*.md`; require exactly the expected `result_pageNNN.md` set and nonempty content.
10. Check each file has a single nonempty page block; validate table shape; merge in numeric page order.
11. Recheck the combined page-block count and publish exclusively.
12. Remove temporary directories in `finally`, warning if remote cleanup fails.

The original filename never enters the remote shell command.
The validated extension and quoted configuration values are used in the remote command.
The image name is shell-quoted, and the remote workspace rejects spaces, parent traversal, and root-directory use.
SSH uses noninteractive authentication and `ConnectTimeout=15`.
A key prompt or unavailable host must not silently fall back to extraction.

The output write differs deliberately from the historical implementation.
It writes a unique temporary file in the destination directory, then uses an exclusive hard link to publish the completed file.
This retains atomic visibility and refuses an existing destination even if it appeared after the preflight check.
A filesystem that cannot perform this same-directory link fails explicitly rather than falling back to overwriting.
The temporary file is removed after either outcome.

## Recovered-page count

For PDFs, the expected count is `min(total pages, max_pages)`.
The wrapper reads the original PDF count even when OCR was selected manually.
For a single image the expected count is a single page.
The client wrapper accepts files; image-directory input is a container-script capability.

A successful container return cannot override a missing file, an empty page, or an unexpected extra result.
The client constructs a `<PAGE>` marker before each validated page.
The helper counts nonempty blocks, accommodating both leading markers and between-page separators when evaluating a model result.
It does not confuse the measured per-page variant's 9 separators with only 9 recovered pages from 10 inputs.

When `--max-pages` intentionally selects only a prefix, the wrapper warns that the output is partial by request.
Missing a page within that selected prefix is still an error.
The selected prefix is a conversion policy, not evidence that the entire source was processed.

## Table shape and its boundary

Generic checks reject unclosed table/row/cell tags, malformed attribute quotes,
invalid spans, overlapping spans, empty rows, and unequal expanded row widths.
Span expansion accounts for `rowspan` and `colspan` rather than counting physical cells blindly.

A structurally consistent missing column cannot be detected from the output alone.
For the benchmark, `configs/benchmark-table.json` requires exactly one table per page,
6 columns, 14 data rows, and the recorded text and spans of the two-level header.
This is a known-layout contract, not a model-free proof of accuracy for arbitrary tables.
The scorer supplies a separate exact-value comparison when ground truth exists.

Without a schema, a page with no table passes the generic shape check.
That is an explicit limitation for arbitrary documents, not evidence that the source had no table.
The benchmark example always supplies its schema.

## Folder-level reporting

The directory driver walks every non-hidden file, including unsupported extensions, and gives each an attempted-conversion row.
Hidden directories are excluded as well as hidden files.
The output tree must be outside the input tree, so it cannot recursively convert its own outputs.
An existing `report.tsv` is refused.
Each destination retains the complete source filename and adds `.md`, avoiding collisions between equal stems with different extensions.

Columns are `path`, `status`, `engine`, `reason`, `out_bytes`, `seconds`, and `note`.
`ok` means the wrapper succeeded and a nonempty result exists, not that unknown-layout text is exact.
`partial` records coverage/partial warnings from compatible callers.
`failed` records a nonzero exit or missing/empty output.
The driver's process exit is 1 if any row is not `ok`, otherwise 0.
With this public wrapper, missing-page refusal becomes `failed`; a deliberate page cap can still be `partial`.

Conditions: historical small directory-driver check in 2026-10; no large-corpus claim.

| Inputs | Recorded outcome |
|---|---|
| Synthetic digital PDF, Word file, spreadsheet, and broken PDF | 3 `ok` rows, 1 `failed` row |
| Stub-engine self-test | `selftest OK` |

Run the same public self-test offline with `python3 scripts/doc2md-batch.py --selftest`.
The normal driver command is `python3 scripts/doc2md-batch.py INPUT_DIR OUTPUT_DIR`.

## What did not work and the rule

Passing representative happy paths left dangerous assumptions in error handling.
Counting pages alone left silent table corruption undetected.
A completion sentinel alone even ignored failed process status.

**Rule:** check every transition from input to output, and make an incomplete or structurally rejected result a nonzero exit before publishing it.
Record what each check can establish and what still requires known content or a known layout.
