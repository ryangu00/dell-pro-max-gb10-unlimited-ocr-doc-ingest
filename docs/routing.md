# Routing by text-layer density

## Problem and mechanism

An extension cannot distinguish an image-only PDF from a digital PDF.
The router reads `get_text()` from up to the first 100 pages and counts extracted characters.
It returns average density, the minimum page density, and the full document page count.
It closes the document after reading and refuses unreadable or password-protected PDFs.

Conditions: starting rules from the original converter; thresholds were not experimentally optimized.

| Condition, in order | Route | Warning |
|---|---|---|
| Average < 200 | OCR | no |
| 200 <= average < 600 | OCR | yes |
| Average >= 600, minimum < 50 | OCR | yes |
| Otherwise | markitdown | no |

Only 600 changes the engine at the average boundary.
The 200 threshold distinguishes a quiet scanned route from a warning-bearing low-confidence route.
The separate minimum catches mixed documents whose digital pages dominate the average.

For non-PDF files, office formats route directly to markitdown:
`.docx .pptx .xlsx .xls .csv .html .htm .epub .json .xml`.
Images route to OCR: `.png .jpg .jpeg .webp .bmp .tiff .tif .gif`.
Unknown extensions default to markitdown, whose empty-output refusal remains active.
A manual `--engine` setting overrides routing.

## Procedure as run

The first version averaged the first 8 pages.
A later scanned page could therefore vanish after text extraction without changing the route.
The correction sampled up to 100 pages and used the minimum as well as the average.
The synthetic 9-page mixed fixture confirmed the changed decision in 2026-10.

`route-check.py` loads the wrapper from its first command-line argument and replaces both engine functions.
It exercises argument handling, density calculation, and routing without running markitdown or contacting an OCR host.
It does not create conversion outputs.
The PDF dependency still has to be installed; the unittest suite separately mocks it.

```sh
python3 scripts/route-check.py scripts/doc2md fixtures/routing/*.pdf
```

The [routing corpus table](results.md#routing-corpus) and [boundary table](results.md#routing-boundaries)
retain every recorded case, including invalid input and a false positive.

Conditions: synthetic routing corpus, local checks only, 2026-10.

| Case | Average / minimum | Outcome |
|---|---|---|
| Mixed 9-page PDF | 1794 / 0 | OCR |
| Digital control | 2019 / 2000 | markitdown |
| 14-character cover followed by dense pages | 1315 / 14 | OCR; false positive |
| Searchable scan with random-letter text layer | 1500 / 1497 | markitdown; wrong for text quality |

## What did not work

A title page or separator can trigger OCR even when the useful content is digital.
Conversely, a long junk text layer can look dense enough for extraction.
The measured junk-layer probe used 1,500 random characters per page over rasterized content.
The router measures existence, not correctness, of text.
It also cannot infer whether cell boundaries matter in an otherwise dense digital PDF.

Only the first 100 pages are sampled.
A scan beyond that cap may still pass the text route.
Do not describe the implementation as an unconditional all-page check.
The offline test deliberately demonstrates this sampling limit.

`get_text()` includes whitespace and newlines.
The recorded PyMuPDF environment and a reader's version can therefore produce different densities.
The public inline dependency pins 1.28.2 and imports `pymupdf` rather than deprecated `fitz`.
A direct `python3` invocation does not install that inline dependency automatically.

## Tuning, proposed but not measured

The source recommends collecting 50 or more documents labeled by eye as scanned, digital, or mixed.
For a public exercise, generate or use appropriately licensed synthetic fixtures for each class.
Tabulate average and minimum values before invoking an engine.
Choose the average threshold to avoid scans and mixed documents reaching extraction, then reduce false positives.
Account for legitimate covers or separator pages separately if needed.
No such calibration was performed for the shipped 200 and 600 values.
Ignoring a cover page or adding a dictionary-word ratio remains unimplemented and untested.

## Rule

Take the weakest sampled page seriously, print the measured values, and retain an explicit override.
A conservative route trades time for coverage; it does not replace downstream quality checks.
