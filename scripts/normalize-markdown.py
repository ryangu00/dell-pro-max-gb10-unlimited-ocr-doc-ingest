"""Small downstream example: preserve HTML tables, remove unshipped crop links.

Not an accuracy repair. Blank spreadsheet cells and header loss need a policy
that this normalizer deliberately does not guess.
"""
import argparse
import json
from pathlib import Path
import re


def normalize(body):
    body = body.replace('\x0c', '\n<PAGE>\n')
    return re.sub(r'!\[\]\(images/[^)]*\)', '[image crop omitted]', body)


def prepare_page(title, body):
    if not body.strip():
        raise ValueError('empty converted body')
    return '---\ntitle: '+json.dumps(title, ensure_ascii=True)+'\n---\n'+normalize(body)


def ingest(store, key, title, body, dry_run=False):
    """Example store contract: lookup errors propagate; writes are exclusive."""
    page = prepare_page(title, body)
    existing = store.exists(key)
    if existing:
        if dry_run:
            return 'would refuse existing target'
        raise ValueError('target exists - refusing overwrite')
    if dry_run:
        return 'would create target; write and readback not exercised'
    store.create(key, page)
    if store.read(key) != page:
        raise ValueError('stored page failed readback')
    return 'verified'


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input')
    p.add_argument('output')
    p.add_argument('--title', required=True)
    a = p.parse_args()
    body = prepare_page(a.title, Path(a.input).read_text())
    with open(a.output, 'x') as stream:
        stream.write(body)
