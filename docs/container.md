# The OCR container on a Dell Pro Max with GB10

## Problem and mechanism

The base image was not ready to load Unlimited-OCR.
The model's remote code depended on a particular Transformers API and additional Python packages.
The working environment was assembled interactively, then committed as an image.

The public batch converter uses the same recorded single-image parameters:

```python
model.infer(
    tokenizer,
    prompt="<image>document parsing.",
    image_file=image_path,
    output_path=page_output,
    base_size=1024,
    image_size=640,
    crop_mode=True,
    max_length=32768,
    no_repeat_ngram_size=35,
    ngram_window=128,
    save_results=True,
)
```

The model and tokenizer load once before this loop.
Each page gets a fresh output directory, then a checked `result_pageNNN.md` copy.
Missing, empty, multi-block, or structurally malformed page output stops the batch before `UOCR_DONE`.
A `finally` block makes output removable even when inference fails.
The wrapper does not publish any copied Markdown until it validates the complete selected page set.

The original multi-page parameters were `image_size=1024`, `max_length=32768`,
`no_repeat_ngram_size=35`, `ngram_window=1024`, and prompt `<image>Multi page parsing.`.
That call is the historical benchmark condition, not an optional public-converter mode.

## Procedure as run and results

The five-launch dependency sequence on 2026-07-21 is preserved in [results](results.md#container-bring-up).
Unpinned Transformers failed because `is_torch_fx_available` was no longer importable.
With `transformers==4.57.1` and `pymupdf==1.27.2.2`, the bundled `torchao` failed on
`torchao.prototype.safetensors.safetensors_utils`.
Removing `torchao` resolved that launch; alternatives were not investigated.

The original successful model-load log was 14.0 s on 2026-07-21, with weights on local NVMe.
This historical value is not comparable to the 2026-10-04 load measurements because driver and image state differed.
The latter measured 36.6-44.8 s and supersede the earlier derived fixed-cost estimate.
No private-document timing or content is needed for the public reproduction.

Conditions: source-recorded image/model sizes; layer inspection belongs to the 2026-10-04 measurement setup.

| Artifact | Recorded detail |
|---|---|
| Model download | 20 files, 6.4 GB, about 2 minutes on 2026-07-21 |
| Image | About 19 GB; 162 layers, 38 non-empty |
| Largest layers | About 5.3, 1.85, 1.77, 1.56, and 1.27 GB |
| Topmost package-install layer | 446 MB |
| Estimated provisioning disk | About 26 GB for model plus image |

The model download file count and the later 15 cache metadata records describe different records; they are not interchangeable counts.
The model revision is `2a06ebf2d6f600f95fd2b99f6ccdee18a52e3b8f`.
It was recovered from the local cache metadata, not inferred from a current upstream branch.
The upstream repository had changed after the download.

## Reproduction on a reader-controlled node

Prepare a workspace containing `scripts/` and `models/Unlimited-OCR/`.
The path is reader configuration; the repository supplies no host, account, or machine directory layout.
Copy `uocr_batch.py` and `ocr_checks.py` to that workspace's `scripts/`.
Download the pinned model revision using the README's provisioning snippet.

[configs/Dockerfile](../configs/Dockerfile) expresses the recorded package recipe.
This equivalent Dockerfile has not been built or tested here.
Its base-image access, platform compatibility, and local Docker GPU passthrough must be established in the reader's environment.
The exact installed PyTorch and CUDA versions were not queried in the measurement image.
Auxiliary Python packages are unpinned because their versions were not recorded.

The intended build command is:

```sh
docker build -f configs/Dockerfile -t ocr-docs:local .
```

After exporting a configured workspace path on that node, a synthetic direct batch invocation is:

```sh
docker run --rm --gpus all --ipc=host --memory=30g --memory-swap=30g \
  -v "$DOC2MD_OCR_HOME:/ws" ocr-docs:local \
  python3 /ws/scripts/uocr_batch.py /ws/fixtures/scan10.pdf /ws/output 200
```

Stage the synthetic PDF at the shown container-relative location first; `output` must not already exist.
A direct container invocation bypasses the wrapper's host-memory guard, so use the configured wrapper for ordinary conversion.
The image banner recommends `--ulimit memlock=-1 --ulimit stack=67108864`;
the recorded runs omitted them and saw no failure attributable to that omission.
No claim is made about a different workload.

## What did not work and the rule

A latest-version install was not a compatible environment.
The vendor's vLLM recipe was not tested; this book does not claim serving-stack support.
Alphabetical image ordering misorders unpadded names, so the public script uses numeric-aware ordering.
PDF render filenames remain zero-padded.

**Rule:** pin known dependencies and the measured model revision, retain unknown versions as unknown,
and distinguish a rebuild recipe from a tested image.
The script can be exercised offline with mocked model calls; that does not validate actual inference.
