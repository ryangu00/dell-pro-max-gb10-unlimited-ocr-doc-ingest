# Sharing the box

## Problem and mechanism

The Dell Pro Max with GB10 shares unified memory between CPU and GPU.
A Docker memory limit is an upper bound in container accounting, not a reservation of free host capacity.
The sampled host effect can exceed what Docker reports.
The wrapper therefore asks the host for available memory before starting a container.

```sh
awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo
```

The number is truncated to whole GiB.
The default threshold is 32 GiB, selected as a conservative starting rule.
The relationship to a 30 GiB cap plus about 2 GiB headroom was an inference in the original record, not a measured derivation.
The public script keeps that threshold so the historical policy is visible, rather than inventing a newly validated threshold.

## Procedure as run

The initial guard check on 2026-09-24 saw about 24 GiB available and refused with exit code 1.
The new synthetic measurement on 2026-10-04 ran only with at least 115 GiB available and no running containers.
Its admission check would abort below 40 GiB or with any running container.
A watchdog would kill the named test container below 8 GiB; it never fired.
These are benchmark conditions, distinct from the converter's 32 GiB default.
The watchdog is not implemented by the shipped wrapper.

Host `MemAvailable` was sampled once per second around the whole container run.
Docker memory was sampled in a `docker stats --no-stream` loop about every 2 s.
The drop is start availability minus the minimum observed availability.
The complete table includes starting values, minima, drop, and Docker peak in [results](results.md#host-and-container-memory).

Conditions: original synthetic benchmark settings, 2026-10-04, no overlapping container workload.

| Pages | Host drop GiB | Docker peak GiB | Interpretation |
|---|---|---|---|
| 1 | 14.1 to 14.6 | 6.64 to 6.75 | Minimum near model load |
| 3 | 13.6 to 13.9 | 6.57 to 6.72 | Similar host effect |
| 10 | 14.0 to 14.4 | 6.59 to 6.79 | Similar host effect |
| 40 | 31.5 to 31.7 | 6.91 to 6.94 | Larger early OCR-phase drop |

A 32 GiB threshold would leave about 0.3 GiB above the sampled 31.7 GiB multi-page drop.
That is almost no operating margin; the threshold must not be advertised as safe for that workload.
The 40-page case used multi-page inference and produced unusable output.
The per-page setting at 40 pages was measured on 2026-10-04 at a 14.8 GiB host drop, leaving about 17 GiB under the 32 GiB guard (one run); its long-document memory requirement beyond 40 pages remains unknown.

`MemAvailable` includes reclaimable page cache, and 1 Hz sampling can miss transient peaks.
These values are lower bounds on the observed host effect, not GPU allocation measurements.
The model's 6.4 GB file size does not describe working memory.
The contributions from CUDA context, buffers, and other allocations were not separately measured.
The reason container accounting missed much of the host drop was not isolated.

## Cleanup

Containers can write root-owned files into a bind mount.
The container script runs `chmod -R a+rwX` on its output directory in `finally`.
The client then attempts normal remote removal, falling back to `sudo -n rm -rf` for that controlled job directory.
No interactive elevation prompt is allowed in this path.
If both removals fail, the wrapper reports cleanup failure on stderr.
Reader-specific cleanup permissions are a prerequisite, not supplied by a configuration file.

Conditions: recorded cleanup checks on 2026-07-22, not a current-node inspection.

| Check | Observation |
|---|---|
| Stale directories after earlier failures | 5, including root-owned output |
| After corrected successful run | 0 remote job directories |

The synthetic measurement containers used `--rm`.
The measurement record reports no containers left afterwards and available memory returning to about 116 GiB.
That observation is not a claim about any present machine state.

## Minimal-environment invocation

An `env`-based launcher that searches for `uv` can fail under `env -i PATH=/usr/bin:/bin`.
The historical launcher was repaired with an installation-specific absolute path and checked at exit 0 on 2026-07-22.
Such a path cannot be portable in a public repository.
The public script instead permits direct invocation with an explicit reader-selected Python interpreter.
Its inline PyMuPDF pin is also usable by `uv run --script` in a provisioned environment.

A scheduler should select its interpreter explicitly and set `DOC2MD_MARKITDOWN` to the installed executable if its `PATH` is minimal.
The wrapper does not prepend installation-specific directories to `PATH`.
Do not source `configs/ocr.env.example` as if it contained working values: host and workspace are deliberately blank.
Export populated values in the reader's environment before executing OCR.

## What did not work and the rule

A cap alone did not characterize memory demand.
Interactive-shell success did not establish unattended startup.
Normal deletion alone did not clean up every container artifact.
The guard also is not a reservation: another job can consume memory after it passes.
There is no shared scheduler or concurrency lock in this repository.

**Rule:** run in an idle window, retain explicit memory refusals, and evaluate capacity from the host measurements for the workload actually attempted.
A reader changing `DOC2MD_MIN_AVAIL_GIB` is choosing a policy; no alternate safe threshold is measured here.
