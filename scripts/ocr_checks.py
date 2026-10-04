"""Offline page coverage and HTML table-shape checks; no claim of text accuracy."""
import re
from html import unescape


def page_blocks(body):
    return [p.strip() for p in re.split(r'^\s*<PAGE>\s*$', body, flags=re.M) if p.strip()]


def require_pages(body, expected):
    got = len(page_blocks(body))
    if got != expected:
        raise ValueError(f'OCR page coverage {got}/{expected} - refusing partial output')


def check_tables(body, schema=None):
    """Check balanced table tags, attributes and rectangular span-expanded rows.

    A known-layout schema can additionally require table/data-row/column counts
    and header text/spans. Without one, a consistently missing column is unknown.
    """
    tables = re.findall(r'<table\b[^>]*>(.*?)</table\s*>', body, flags=re.S | re.I)
    if len(tables) != len(re.findall(r'<table\b', body, flags=re.I)):
        raise ValueError('table shape: unclosed table')
    if schema and len(tables) != schema['tables_per_page']:
        raise ValueError('table shape: unexpected table count')
    for table in tables:
        tags = re.findall(r'<[^>]+>', table)
        stack = []
        for tag in tags:
            if tag.count('"') % 2 or tag.count("'") % 2:
                raise ValueError('table shape: malformed attribute quotes')
            m = re.match(r'<(/?)(tr|td|th)\b', tag, re.I)
            if m:
                name = m[2].lower()
                if m[1]:
                    if not stack or stack.pop() != name:
                        raise ValueError('table shape: unbalanced row or cell')
                else:
                    stack.append(name)
        if stack:
            raise ValueError('table shape: unclosed row or cell')
        rows = re.findall(r'<tr\b[^>]*>(.*?)</tr\s*>', table, flags=re.S | re.I)
        if not rows:
            raise ValueError('table shape: no rows')
        occupied, widths, headers, data_rows = {}, [], [], 0
        for i, row in enumerate(rows):
            cells = list(re.finditer(r'<(td|th)\b([^>]*)>(.*?)</\1\s*>', row, flags=re.S | re.I))
            if not cells:
                raise ValueError('table shape: empty row')
            col = 0
            data_rows += any(c[1].lower() == 'td' for c in cells)
            for cell in cells:
                while (i, col) in occupied:
                    col += 1
                spans = {}
                for attr in ('colspan', 'rowspan'):
                    m = re.search(r'\b'+attr+r'\s*=\s*(?:"(\d+)"|\'(\d+)\'|(\d+)(?=\s|$))', cell[2], re.I)
                    if re.search(r'\b'+attr+r'\b', cell[2], re.I) and not m:
                        raise ValueError('table shape: invalid span')
                    spans[attr] = int(next(g for g in m.groups() if g is not None)) if m else 1
                    if spans[attr] < 1:
                        raise ValueError('table shape: nonpositive span')
                if spans['rowspan'] > len(rows) - i:
                    raise ValueError('table shape: rowspan beyond table')
                for dr in range(spans['rowspan']):
                    for dc in range(spans['colspan']):
                        key = (i+dr, col+dc)
                        if key in occupied:
                            raise ValueError('table shape: overlapping spans')
                        occupied[key] = True
                text = re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]+>', ' ', cell[3]))).strip()
                if cell[1].lower() == 'th':
                    headers.append({'text': text, **spans})
                col += spans['colspan']
            columns = [c for r, c in occupied if r == i]
            width = max(columns) + 1
            if len(columns) != width:
                raise ValueError('table shape: missing cell')
            widths.append(width)
        if len(set(widths)) != 1:
            raise ValueError('table shape: inconsistent row widths')
        if schema:
            if widths[0] != schema['columns'] or data_rows != schema['data_rows']:
                raise ValueError('table shape: unexpected columns or data rows')
            for header in schema['headers']:
                if header not in headers:
                    raise ValueError('table shape: missing header or wrong span')
