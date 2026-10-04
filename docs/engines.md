# One engine is the wrong bet

## Problem and mechanism

The same `.pdf` suffix can contain text objects, images, or both.
markitdown reads supported embedded content; a vision model reads rendered pixels.
Neither path makes exit status a completeness certificate.
A nonempty digital extraction can still have unusable tables, and OCR can still lose columns.

The text engine in these probes was markitdown 0.1.6.
The observed environment in 2026-10 contained pdfminer.six 20260107, pdfplumber 0.11.10,
mammoth 1.11.0, openpyxl 3.1.5, pandas 3.0.3, python-pptx 1.0.2, and magika 0.6.3.
Those dependency observations are dated; they are not a lockfile for the original build.
The installation command recorded in the source is:

```sh
uv tool install "markitdown[pdf,docx,xlsx,pptx]==0.1.6"
```

Installation is a separate provisioning activity, not part of the offline suite.
The public converter accepts an explicit executable via `DOC2MD_MARKITDOWN`.

## Procedure as run

The routing generator builds the following PDFs:

- A digital 10-page file, about 2,000 characters per page, with merged-cell tables on pages 1, 4, 7, and 10.
- The same pages rasterized into an image-only file.
- A mixed 9-page file containing 8 digital pages and an image-only page.
- Low-density slides, a document above the routing band, a short title page, a blank page, and an invalid PDF.

The text-engine timing probe ran the digital and scanned controls three times, including process startup.
Separate generated Office files tested a heading, paragraph, a 3x2 Word table,
and spreadsheet integers, two blank cells, and a merged range.
A PNG was copied to `.tif` and `.gif`; this tested extension handling, not TIFF or GIF encoding fidelity.
The original Office-generation scripts were not supplied; this repository does not claim byte-identical reconstruction of those probes.

## Results

Conditions: synthetic documents, markitdown 0.1.6 on the client Mac, 2026-10.
Complete result rows and timing repetitions appear in [results](results.md#text-engine-probes).

| Failure class | Recorded observation |
|---|---|
| Empty success | Image-only 10-page PDF: 1 byte, exit 0 |
| Partial success | Mixed PDF: 15,984 bytes, image page absent, exit 0 |
| Lost table boundaries | Digital PDF cells fused into `Region2025Q1Q2North120135South98101` |
| Spreadsheet representation | Integer-to-float rendering, `NaN` for blanks, extra all-`NaN` merged-range row |
| Word structure | Empty Markdown header row, real header moved into body |

The all-digital control emitted 19,988 bytes with zero newlines.
Its page boundaries were form-feed characters, not Markdown headings.
The output must therefore be understood before using line counts as a structural metric.

OCR output can contain HTML `<table>` elements with `rowspan` and `colspan`.
The original multi-page call used `<PAGE>` markers; the original single-page call used none.
Image-crop references can appear as `![](images/page_0_0.jpg)`.
The wrapper copies Markdown, not crop files, so those links are not usable assets after cleanup.
The supplied downstream example replaces such missing crop links with an explicit omission note.

## What did not work

Empty-output checks catch the image-only case but not the missing scanned appendix of an otherwise nonempty extraction.
Density checks catch that appendix only when it lies within the sampled pages.
Text-rich tables route to markitdown unless the caller forces OCR.
The benchmark now also shows that selecting OCR alone does not establish structural correctness.

No numeric-coercion or `NaN` cleanup is applied automatically.
A string equal to `NaN` might be literal document content, so a reader must choose that policy for a known format.
The fact sheet proposed post-processing, but supplied no validated implementation or measured effect.
The Word header loss is likewise documented rather than silently guessed away.

## Rule

Choose the engine from evidence in the file, then check properties the consumer needs.
Use the original process status to detect execution errors, not to infer that the document was read correctly.
Preserve the distinction between text recovery and table recovery in every report.
