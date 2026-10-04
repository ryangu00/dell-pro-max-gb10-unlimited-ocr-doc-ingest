# Pitfalls: symptom, root cause, fix

The evidence labels distinguish recorded observations from code-level defenses.
The later synthetic measurements supersede the early fixed-overhead and unmeasured-host-memory assumptions.
All examples here are synthetic or generic error conditions.

## Conversion and routing

| Symptom | Root cause | Fix | Evidence |
|---|---|---|---|
| Exit 0, file contains only a newline | Image-only PDF has no text layer | OCR route and empty-output refusal | Observed with markitdown 0.1.6, synthetic input, 2026-10 |
| Converted document omits scanned appendix | Average-only sampling misses an empty page | Inspect minimum within the sampled pages | Mixed synthetic fixture selected OCR after the change |
| Digital cover causes unexpectedly slow route | Short legitimate cover triggers the minimum rule | Inspect densities and use an explicit per-document override when justified | 14-character cover, average 1315, minimum 14, observed false positive |
| Searchable scan passes but text is junk | Text quantity is not text quality | Inspect output; use explicit OCR for the known bad layer | Random-letter overlay, average 1500, minimum 1497; no automated language check built |
| PDF tables become fused text | Text runs do not retain cell boundaries | Force OCR when structure is required, then validate tables | Synthetic table output recorded in 2026-10 |
| Spreadsheet blanks say `NaN`; integers gain `.0` | Dataframe-based representation | Choose a format-aware post-processing policy or preserve and document | Observed; no tested general repair shipped |
| Word table has empty header row | Extraction demotes the real header | Preserve the limitation or supply a document-specific repair | Observed on generated 3x2 table; no general repair shipped |
| `.tif` or `.gif` yields empty extraction | Original OCR extension list omitted aliases | Include both aliases in image routing | Public wrapper includes them; actual decoder compatibility is not proven by alias routing |
| Density differs across environments | Extraction versions and whitespace affect counts | Pin client PyMuPDF and compare a fixed corpus | Version sensitivity is a caveat, not a measured cross-version error rate |
| A test stub never runs | Historical wrapper prepended fixed executable directories | Stub the function or use explicit executable configuration | Public wrapper no longer rewrites `PATH` |

The public router still samples only the first 100 pages.
An empty page beyond that cap can remain invisible to automatic routing.
A manually selected text route also intentionally bypasses density-based routing.
Neither case is claimed to be protected by the OCR page-count check, which runs only on the OCR path.

## Model calls and output quality

| Symptom | Root cause or known limit | Fix | Evidence |
|---|---|---|---|
| All 10 markers present, tables damaged | Multi-page output loses structure; causal mechanism unknown | Per-page inference within one load, plus known-layout checks | 2026-10-04, 2 multi-page runs and 1 per-page run |
| Last column absent from every row | Structurally consistent loss can evade generic shape checks | Require expected column count and header spans | Present in the 10-page output |
| Every value present but rows still wrong | Extra empty seventh cell | Validate exact shape separately from value presence | Page 2 of the 10-page output |
| Strict HTML parser swallows later content | Mismatched attribute quotes such as `colspan='2"` | Reject malformed attributes; use a lenient reader only for measurement | Seen on pages 4 and 8 of the 10-page output |
| One recovered block from 40 pages, exit 0 | Runaway multi-page generation; exact cause unknown | Refuse page-count mismatch; do not present elapsed time as successful throughput | Both 40-page runs, 2026-10-04 |
| Marker total seems short in per-page analysis | A separator appears between pages, not necessarily before the first | Count nonempty blocks and validate per-page files | Measured 10-page per-page aggregate has 9 separators and 10 blocks |
| Slow single-page jobs despite quick OCR | Model load and startup dominate | Loop per-page calls inside one model load | Model load 36.6-44.8 s across the measured runs |
| A huge answer looks like completeness | Generated character count can grow without recovering source pages | Require expected recovery and shape, not just a minimum byte count | 40-page output: 38,983 characters, one page marker |

A correct shape does not establish that every number was transcribed correctly.
The shipped scorer needs exact ground truth for that additional comparison.
The benchmark schema describes one known synthetic layout and is not an arbitrary-document schema.

## Environment and resource handling

| Symptom | Root cause | Fix | Evidence |
|---|---|---|---|
| Missing `transformers` | Base image lacks it | Install the recorded runtime | Historical launch 1 |
| Missing `addict` | Model remote code has auxiliary dependencies | Add the recorded packages | Historical launch 2 |
| `is_torch_fx_available` import fails | Latest Transformers is incompatible with model code | Pin 4.57.1 | Historical launch 3 |
| `torchao.prototype.safetensors.safetensors_utils` import fails | Bundled `torchao` conflicts with the pinned environment | Uninstall `torchao` | Historical launch 4; working launch 5 |
| `Failed to infer device type` in a registry probe | Probe lacked GPU access | Read package files for a static registry check | Historical diagnostic; does not validate serving support |
| Image input order is wrong | Alphabetical ordering puts page10 before page2 | Numeric-aware order; retain zero-padded PDF render names | Defensive fix; not an observed original multi-file merge loss |
| A model rebuild behaves differently | Upstream revision changed | Pin the recorded commit | Cache metadata identifies the measured revision |
| 30 GiB cap seems to protect a 32 GiB window | Container accounting does not track full host effect | Check host-level demand; use an idle window | 31.7 GiB sampled host drop, Docker peak at most 6.94 GiB |
| Remote job directories cannot be removed | Container writes root-owned output | Set removable output permissions and use noninteractive cleanup fallback | Earlier stale directories observed; public failure path is mocked in tests |
| Unattended launch cannot find `uv` or a converter | Minimal `PATH` lacks interactive tools | Use explicit installed executable paths | Historical minimal-environment failure and recheck |
| OCR host is unreachable | SSH, authentication, or connection setup failed | Fail with the transport diagnostic; resolve the prerequisite | No fallback to empty text extraction |

The measured memory values are sampled host drops, not GPU-side memory counters.
A one-second sampling interval can miss brief spikes.
The multi-page 40-page failure does not establish per-page 40-page memory use.

## Wrapper and downstream seams

| Symptom | Root cause | Fix | Evidence |
|---|---|---|---|
| Quote-bearing filename breaks a command | User-controlled basename reaches a remote shell | Copy to `input.<ext>` and validate extension | Historical filename reproduction; current mocked transport test |
| Source disappears after conversion | Destination aliases input | Resolve and compare paths, including existing hard links | Public offline test |
| Existing output is replaced | Publication uses replacement semantics | Exclusive atomic publication | Public offline test; stronger than historical replacement behavior |
| Container prints success but returns error | Sentinel-only success check | Require both return code and standalone sentinel | Public offline test |
| Missing page still creates output | Historical warning-only coverage policy | Nonzero failure before publication | Public offline test with successful mocked container exit |
| YAML title fails parsing | Raw scalar contains syntax characters | JSON-encode the scalar | Historical reproduction and public encoding test |
| Store outage permits overwrite | Failed lookup treated as missing | Propagate lookup failure | Generic historical fix and public mock test |
| Dry-run promises success for a collision | Dry-run skipped existence | Run the lookup and report would-refuse | Generic historical recheck and public mock test |
| Report driver processes its own results | Output tree nested under input | Reject nested output directories | Public offline test |

## Rule

Each check should name the failure it detects and the uncertainty it leaves.
A regression test with a mocked container verifies the wrapper's behavior, not OCR quality or GPU compatibility.
The dated measurements supply the quality evidence; the code tests enforce the selected failure policy.
