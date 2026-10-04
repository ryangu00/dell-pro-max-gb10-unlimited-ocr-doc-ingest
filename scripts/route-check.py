"""Offline routing: python3 route-check.py CONVERTER FILE.pdf ..."""
import contextlib
import importlib.machinery
import importlib.util
import io
from pathlib import Path
import sys


def main():
    converter, *files = sys.argv[1:]
    loader = importlib.machinery.SourceFileLoader('converter', converter)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    module.run_ocr = lambda *args: None
    module.run_markitdown = lambda *args: None
    for path in files:
        captured = io.StringIO()
        with contextlib.redirect_stderr(captured), contextlib.redirect_stdout(io.StringIO()):
            try:
                module.main([path, '-o', str(Path(path).with_suffix('.routing-preview.md'))])
            except SystemExit as exc:
                captured.write(f'EXIT:{exc}')
        print(Path(path).name, '|', captured.getvalue().strip().replace('\n', ' | '))


if __name__ == '__main__':
    main()
