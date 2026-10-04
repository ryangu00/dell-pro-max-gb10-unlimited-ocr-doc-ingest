"""Container-side OCR: load once, infer each page, require every result.

Usage: python3 uocr_batch.py INPUT OUTPUT [MAX_PAGES]
MODEL_DIR selects the local model mount. No download occurs here.
"""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from ocr_checks import check_tables, require_pages

IMG_EXT = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif', '.gif')


def natural_key(path):
    return [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', str(path))]


def pdf_to_images(pdf_path, out_dir, dpi=300, cap=200):
    import pymupdf
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    with pymupdf.open(pdf_path) as doc:
        if doc.needs_pass:
            raise ValueError('PDF is password-protected')
        for i in range(min(len(doc), cap)):
            path = out_dir / f'page{i+1:03d}.png'
            doc[i].get_pixmap(matrix=pymupdf.Matrix(dpi/72, dpi/72)).save(str(path))
            paths.append(str(path))
    return paths


def load_model():
    import torch
    from transformers import AutoModel, AutoTokenizer
    model_dir = os.environ.get('MODEL_DIR', '/ws/models/Unlimited-OCR')
    tok = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True, local_files_only=True)
    model = AutoModel.from_pretrained(model_dir, trust_remote_code=True, local_files_only=True,
                                     use_safetensors=True, torch_dtype=torch.bfloat16).eval().cuda()
    return tok, model


def convert(inp, out, max_pages=200, loader=load_model):
    if max_pages < 1:
        raise ValueError('max_pages must be >= 1')
    inp, out = Path(inp), Path(out)
    # A fresh output directory prevents a stale result from counting as recovery.
    out.mkdir(parents=True, exist_ok=False)
    try:
        if inp.is_dir():
            images = sorted((str(p) for p in inp.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXT), key=natural_key)[:max_pages]
        elif inp.suffix.lower() == '.pdf':
            images = pdf_to_images(str(inp), out/'pages', cap=max_pages)
        else:
            images = [str(inp)] if inp.is_file() else []
        if not images:
            raise ValueError('NO_INPUT_IMAGES')
        start = time.monotonic()
        tok, model = loader()
        print(f'[load] {time.monotonic()-start:.1f}s', flush=True)
        start = time.monotonic()
        recovered = []
        for i, image in enumerate(images, 1):
            page_out = out / f'p{i:03d}'
            page_out.mkdir()
            model.infer(tok, prompt='<image>document parsing.', image_file=image,
                        output_path=str(page_out), base_size=1024, image_size=640,
                        crop_mode=True, max_length=32768, no_repeat_ngram_size=35,
                        ngram_window=128, save_results=True)
            result = page_out / 'result.md'
            if not result.is_file() or not result.read_text().strip():
                raise ValueError(f'OCR page coverage {len(recovered)}/{len(images)} - missing page {i}')
            body = result.read_text()
            require_pages(body, 1)
            check_tables(body)
            shutil.copyfile(result, out/f'result_page{i:03d}.md')
            recovered.append(body)
        require_pages('\n<PAGE>\n'.join(recovered), len(images))
        print(f'[ocr] {len(recovered)} pages {time.monotonic()-start:.1f}s', flush=True)
    finally:
        # Container output must remain removable by the caller, even on failure.
        subprocess.run(['chmod', '-R', 'a+rwX', str(out)], check=False)
    print('UOCR_DONE', flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input')
    p.add_argument('output')
    p.add_argument('max_pages', type=int, nargs='?', default=200)
    a = p.parse_args()
    try:
        convert(a.input, a.output, a.max_pages)
    except (OSError, ValueError) as exc:
        p.exit(1, str(exc)+'\n')


if __name__ == '__main__':
    main()
