# The seam to whatever stores the Markdown

## Problem

Markdown output is often handed to an index, a notes store, or a retrieval pipeline.
At that boundary, treating an unknown lookup as an empty lookup can bypass a never-overwrite policy.
Metadata serialization and dry-run behavior can also turn a plausible conversion into a broken write.
This repository supplies a generic example, not an adapter for any particular store.

## Mechanism and procedure

Convert into temporary output first, and abort on a nonzero conversion exit or an empty body.
Serialize frontmatter strings with `json.dumps` rather than inserting raw title text into YAML.
An existence lookup must distinguish a missing key from a lookup failure.
An existing destination is refused, and exclusive creation must also enforce that at write time.
A dry-run consults existence and reports what it would refuse; it does not pretend to have tested a write.
After creation, independently read back and compare the stored page.
Remove temporary bodies in `finally` even on a failed store operation.

The historical review reproduced this title failure:

```text
Quarterly: #1
```

As an unquoted YAML scalar it could raise `ScannerError: mapping values are not allowed here`.
With an embedded newline the JSON string representation is:

```json
"Quarterly: #1\nsecond"
```

This is a valid YAML double-quoted scalar as well as a JSON string.
It preserves the title's colon, hash, and newline without assigning them YAML syntax.

## Results and evidence

Conditions: generic seam review fixes rechecked on 2026-07-22; no store-specific integration is shipped.

| Reproduced issue | Corrected behavior |
|---|---|
| Unescaped metadata scalar | JSON encoding preserves the title |
| Failed query treated as missing | Lookup error aborts |
| Dry-run skipped existence | Existing destination yields a would-refuse warning |
| Temporary body leaked after failed write | Removal in `finally` |
| Colliding target | Still refused after the fixes |

The review recorded three initial findings, with two fixes and one deliberately unchanged content-quality question.
A later review identified the fail-open lookup, YAML escaping, and temporary-file leak.
Those are historical observations about the seam; the small public example is new and tested with a mock store.
The example does not implement a force-overwrite switch.

## Output shapes a consumer must handle

- HTML `<table>` elements, including spans, alongside ordinary Markdown.
- `<PAGE>` markers produced by OCR, and form-feed page boundaries from text extraction.
- Image-crop links whose target files are not copied back by the converter.
- Spreadsheet `NaN` strings and float-looking integers.
- Tables whose header semantics were already lost by text extraction.

The example normalizer preserves HTML tables.
It replaces form feeds with `<PAGE>` boundaries and missing crop links with `[image crop omitted]`.
It does not flatten table text, remove page markers, rewrite numbers, or guess header semantics.
Those choices need a downstream format contract not supplied by this book.

```sh
python3 scripts/normalize-markdown.py fixtures/perfect.md normalized.md \
  --title 'Quarterly: #1'
```

This demonstration uses generated source HTML as the body.
It writes only to a new destination and does not contact a store.
The `ingest` function exposes `exists`, `create`, and `read` methods so offline tests can simulate lookup failure and bad readback.
A real adapter must make `create` exclusive; a preflight lookup by itself does not close a concurrent-write race.

## What did not work

Dry-run acceptance did not predict real-write acceptance when their checks differed.
An existence query that failed open gave an outage the same meaning as a missing key.
A force flag cannot establish whether converted content is useful.
The normalizer is not an accuracy repair and has no measured improvement on real documents.

## Rule

Stop on empty conversion, failed lookup, existing target, or failed readback.
Keep serialization, storage policy, and content-quality evidence separate.
