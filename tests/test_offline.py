"""Offline assertions. PDF parsing, SSH/SCP, Docker and model inference are mocked."""
import contextlib
import csv
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import random
import runpy
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))


def load(name, filename):
    loader = importlib.machinery.SourceFileLoader(name, str(ROOT/'scripts'/filename))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


converter = load('converter', 'doc2md')
batch = load('batch', 'uocr_batch.py')
score = load('score', 'ocr-score.py')
corpus = load('corpus', 'make-ocr-bench-corpus.py')
folder = load('folder', 'doc2md-batch.py')
seam = load('seam', 'normalize-markdown.py')
from ocr_checks import check_tables, require_pages
SCHEMA = json.loads((ROOT/'configs/benchmark-table.json').read_text())
TRUTH = json.loads((ROOT/'fixtures/truth.json').read_text())
GOOD = (ROOT/'fixtures/perfect.md').read_text()


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root/'synthetic.pdf'
        self.src.write_text('synthetic placeholder; parser is mocked')
        self.out = self.root/'output.md'


class FakeRect:
    width, height = 595, 842
    def __add__(self, other): return self


class FakePage:
    rect = FakeRect()
    def insert_htmlbox(self, *args): pass
    def insert_text(self, *args): pass
    def insert_image(self, *args, **kwargs): pass
    def get_text(self): return ""
    def get_pixmap(self, **kwargs):
        return types.SimpleNamespace(save=lambda path: Path(path).write_text("synthetic mocked pixels"))


class FakePDF:
    needs_pass = False
    def __init__(self, records): self.pages, self.records = [], records
    def new_page(self, **kwargs):
        page = FakePage(); self.pages.append(page); return page
    def insert_pdf(self, doc, from_page, to_page): self.pages.extend(doc.pages[from_page:to_page+1])
    def save(self, path):
        self.records[str(path)] = self
        Path(path).write_text("synthetic mocked PDF")
    def __len__(self): return len(self.pages)
    def __iter__(self): return iter(self.pages)
    def __getitem__(self, i): return self.pages[i]
    def __enter__(self): return self
    def __exit__(self, *args): pass


class Generators(Sandbox):
    def fake_pdf_module(self):
        records = {}
        module = types.SimpleNamespace(open=lambda path=None: records[str(path)] if path else FakePDF(records),
                                       Matrix=lambda *args: args)
        return module, records

    def test_routing_generator_control_flow_with_rendering_mocked(self):
        module, records = self.fake_pdf_module()
        previous = Path.cwd()
        try:
            os.chdir(self.root)
            with patch.dict(sys.modules, {'pymupdf':module}), contextlib.redirect_stdout(io.StringIO()):
                runpy.run_path(str(ROOT/'scripts/make-synthetic-corpus.py'),run_name='__main__')
        finally:
            os.chdir(previous)
        self.assertEqual({Path(k).name:len(v) for k,v in records.items()},
                         {'digital10.pdf':10,'scanned10.pdf':10,'mixed9.pdf':9,'slides400.pdf':8,
                          'band_just_above.pdf':6,'titlepage_dense.pdf':8,'blank1.pdf':1})
        self.assertEqual((self.root/'broken.pdf').read_text(),'not a pdf')

    def test_benchmark_generator_control_flow_with_rendering_mocked(self):
        module, records = self.fake_pdf_module()
        class Image:
            def save(self, path, *args, **kwargs):
                if hasattr(path,'write'): path.write(b'synthetic mocked JPEG')
                else: Path(path).write_text('synthetic mocked pixels')
        pil=types.SimpleNamespace(Image=types.SimpleNamespace(open=lambda path:Image()))
        with patch.dict(sys.modules, {'pymupdf':module,'PIL':pil}), patch.object(corpus,'render',return_value=Image()), contextlib.redirect_stdout(io.StringIO()):
            corpus.random.seed(20261004)
            corpus.main(str(self.root/'benchmark'))
        self.assertEqual(sorted(len(v) for v in records.values()),[1,3,10,40])
        truth=json.loads((self.root/'benchmark/truth.json').read_text())
        self.assertEqual(len(truth),40)
        self.assertEqual(truth[0],TRUTH[0])

    def test_route_check_cli_uses_stub_engines(self):
        module, records=self.fake_pdf_module()
        pdf=FakePDF(records); pdf.new_page(); records[str(self.src)]=pdf
        argv=['route-check.py',str(ROOT/'scripts/doc2md'),str(self.src)]
        with patch.dict(sys.modules,{'pymupdf':module}), patch.object(sys,'argv',argv), patch.object(subprocess,'run',side_effect=AssertionError('external command attempted')), contextlib.redirect_stdout(io.StringIO()) as output:
            runpy.run_path(str(ROOT/'scripts/route-check.py'),run_name='__main__')
        self.assertIn('engine=ocr',output.getvalue())
        self.assertFalse(list(self.root.glob('*.routing-preview.md')))


class Routing(Sandbox):
    def test_all_recorded_boundaries(self):
        for avg, low, engine, warn in [(0,0,'ocr',False),(199,199,'ocr',False),
                (200,200,'ocr',True),(599,300,'ocr',True),(600,600,'markitdown',False),
                (600,49,'ocr',True),(600,50,'markitdown',False),(5000,0,'ocr',True),
                (5000,49,'ocr',True),(5000,50,'markitdown',False)]:
            with self.subTest(avg=avg, low=low):
                actual = converter.density_route(avg,low)
                self.assertEqual((actual[0],actual[2]),(engine,warn))

    def test_mixed_tail_and_sampling_cap(self):
        class PDF:
            needs_pass = False
            def __init__(self, counts): self.counts = counts
            def __len__(self): return len(self.counts)
            def __getitem__(self, i): return types.SimpleNamespace(get_text=lambda: 'x'*self.counts[i])
            def __enter__(self): return self
            def __exit__(self, *args): pass
        fake = types.SimpleNamespace(open=lambda p: PDF([2000]*8+[0]))
        with patch.dict(sys.modules, {'pymupdf': fake}):
            avg, low, total = converter.pdf_text_density(self.src)
        self.assertEqual((low,total),(0,9))
        self.assertEqual(converter.density_route(avg,low)[0],'ocr')
        fake.open = lambda p: PDF([2000]*100+[0])
        with patch.dict(sys.modules, {'pymupdf': fake}):
            avg, low, total = converter.pdf_text_density(self.src)
        self.assertEqual((avg,low,total),(2000,2000,101))

    def test_missing_password_and_broken_inputs(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            converter.main([str(self.root/'absent.pdf')])
        self.assertEqual(error.exception.code,1)
        fake = types.SimpleNamespace(open=Mock(side_effect=ValueError('damaged')))
        with patch.dict(sys.modules, {'pymupdf':fake}), self.assertRaisesRegex(ValueError,'cannot open PDF'):
            converter.pdf_text_density(self.src)
        doc = Mock()
        doc.__enter__ = Mock(return_value=types.SimpleNamespace(needs_pass=True))
        doc.__exit__ = Mock(return_value=False)
        fake.open = Mock(return_value=doc)
        with patch.dict(sys.modules, {'pymupdf':fake}), self.assertRaisesRegex(ValueError,'password-protected'):
            converter.pdf_text_density(self.src)

    def test_image_aliases_and_argument_guard(self):
        for ext in ('.tif','.gif'):
            src=self.src.with_suffix(ext); src.write_text('synthetic')
            with patch.object(converter,'run_ocr') as ocr, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                converter.main([str(src),'-o',str(self.out)])
                ocr.assert_called_once()
        for cap in ('0','-1'):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                converter.main([str(self.src),'--max-pages',cap])
            self.assertEqual(error.exception.code,2)


class LocalSafety(Sandbox):
    def test_empty_and_failing_text_engine(self):
        for rc, body, message in [(0,' \n','empty output'),(1,'text','markitdown failed')]:
            with patch.object(subprocess,'run', return_value=subprocess.CompletedProcess([],rc,body,'failure')):
                with self.assertRaisesRegex(ValueError,message):
                    converter.run_markitdown(str(self.src),str(self.out))
            self.assertFalse(self.out.exists())

    def test_input_alias_and_existing_output_preserved(self):
        alias = self.root/'alias.pdf'; os.link(self.src,alias)
        for out in (self.src, alias):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                converter.main([str(self.src),'-o',str(out)])
        self.out.write_text('preserve')
        with self.assertRaisesRegex(ValueError,'refusing overwrite'):
            converter.atomic_write(self.out,'replacement')
        self.assertEqual(self.out.read_text(),'preserve')
        self.assertFalse(list(self.root.glob('.doc2md-*')))

    def test_atomic_publish(self):
        converter.atomic_write(self.out,'synthetic content')
        self.assertEqual(self.out.read_text(),'synthetic content')
        self.assertFalse(list(self.root.glob('.doc2md-*')))


class Remote(Sandbox):
    def invoke(self, count=3, missing=False, bad_shape=False, rc=0, sentinel=True, memory='115', copy_fail=False):
        calls=[]
        def fake_run(args, **kwargs):
            calls.append(args)
            stdout=''; code=0
            if args[0]=='ssh':
                command=args[-1]
                if 'MemAvailable' in command: stdout=memory
                if command.startswith('docker '):
                    code=rc; stdout='UOCR_DONE\n' if sentinel else 'no completion\n'
            elif args[0]=='scp' and ':/' in args[-2]:
                if copy_fail: code=1
                else:
                    for i in range(1,(count if missing else count+1)):
                        text=GOOD.replace('colspan="3"','colspan="2"') if bad_shape else GOOD
                        Path(args[-1],f'result_page{i:03d}.md').write_text(text)
            return subprocess.CompletedProcess(args,code,stdout,'simulated error' if code else '')
        env={'DOC2MD_OCR_HOST':'localhost','DOC2MD_OCR_HOME':'/workspace','DOC2MD_MIN_AVAIL_GIB':'32'}
        with patch.dict(os.environ,env), patch.object(converter,'pdf_text_density',return_value=(0,0,count)), patch.object(subprocess,'run',side_effect=fake_run):
            converter.run_ocr(str(self.src),str(self.out),200,SCHEMA)
        return calls

    def test_success_controlled_names_and_cleanup(self):
        self.src=self.root/"synthetic ' ; document.pdf"; self.src.write_text('synthetic')
        calls=self.invoke()
        self.assertEqual(self.out.read_text().count('<PAGE>'),3)
        commands=[a[-1] for a in calls if a[0]=='ssh']
        self.assertTrue(any('--memory=30g' in s for s in commands))
        self.assertTrue(commands[-1].startswith('rm -rf '))
        self.assertTrue(all(self.src.name not in s for s in commands))
        self.assertFalse(list(self.root.glob('.doc2md-*')))

    def test_missing_page_is_failure_even_with_zero_exit(self):
        with self.assertRaisesRegex(ValueError,'page coverage 2/3'):
            self.invoke(missing=True)
        self.assertFalse(self.out.exists())
        self.assertFalse(list(self.root.glob('.doc2md-*')))

    def test_table_shape_fails_after_complete_coverage(self):
        with self.assertRaisesRegex(ValueError,'table shape'):
            self.invoke(bad_shape=True)
        self.assertFalse(self.out.exists())

    def test_return_code_and_sentinel_are_both_required(self):
        for rc,sentinel in [(1,True),(0,False)]:
            with self.subTest(rc=rc), self.assertRaisesRegex(ValueError,'OCR run failed'):
                self.invoke(rc=rc,sentinel=sentinel)
        self.assertFalse(self.out.exists())

    def test_memory_copy_and_config_refusals(self):
        with self.assertRaisesRegex(ValueError,'24 GiB < 32 GiB'):
            self.invoke(memory='24')
        with self.assertRaisesRegex(ValueError,'cannot read'):
            self.invoke(memory='unknown')
        with self.assertRaisesRegex(ValueError,'no result'):
            self.invoke(copy_fail=True)
        with patch.dict(os.environ,{},clear=True), self.assertRaisesRegex(ValueError,'set DOC2MD'):
            converter.remote_config()


class Container(Sandbox):
    def test_model_load_once_page_order_and_settings(self):
        inputs=self.root/'images'; inputs.mkdir()
        for n in (10,2,1): (inputs/f'page{n}.png').write_text('synthetic mock image')
        seen=[]
        def infer(token, **kwargs):
            seen.append(kwargs)
            Path(kwargs['output_path'],'result.md').write_text(GOOD)
        model=types.SimpleNamespace(infer=infer)
        loader=Mock(return_value=(object(),model))
        with contextlib.redirect_stdout(io.StringIO()) as logs, patch.object(subprocess,'run'):
            batch.convert(inputs,self.root/'results',loader=loader)
        loader.assert_called_once()
        self.assertEqual([Path(c['image_file']).name for c in seen],['page1.png','page2.png','page10.png'])
        self.assertTrue(all(c['image_size']==640 and c['crop_mode'] and c['ngram_window']==128 for c in seen))
        self.assertIn('UOCR_DONE',logs.getvalue())

    def test_empty_page_prevents_sentinel(self):
        image=self.root/'scan.png'; image.write_text('synthetic')
        model=types.SimpleNamespace(infer=lambda *args,**kw: None)
        with patch.object(subprocess,'run') as chmod, contextlib.redirect_stdout(io.StringIO()) as logs:
            with self.assertRaisesRegex(ValueError,'missing page'):
                batch.convert(image,self.root/'results',loader=lambda:(None,model))
        self.assertNotIn('UOCR_DONE',logs.getvalue())
        chmod.assert_called_once()


class Quality(unittest.TestCase):
    def test_truth_generation_is_deterministic(self):
        corpus.random.seed(20261004)
        first=corpus.make_page(1)
        corpus.random.seed(20261004)
        self.assertEqual(first,corpus.make_page(1))
        self.assertEqual(first,TRUTH[0])
        self.assertEqual(len(first['rows']),14)
        self.assertTrue(all(len(row)==6 for row in first['rows']))

    def test_perfect_score(self):
        result=score.score_page(TRUTH[0],GOOD)
        self.assertEqual((result['prose_cer'],result['table_cer']),(0,0))
        self.assertEqual((result['rows_exact'],result['cells_value_found']),(14,84))
        self.assertTrue(result['header_ok'])
        check_tables(GOOD,SCHEMA)

    def test_damage_not_hidden_by_page_count(self):
        extra=GOOD.replace('</td></tr>','</td><td></td></tr>')
        malformed=GOOD.replace('colspan="2"',"colspan='2\"")
        missing_column=GOOD.replace('colspan="2"','colspan="1"')
        for damaged in (extra,malformed,missing_column):
            require_pages(damaged,1)
            with self.assertRaisesRegex(ValueError,'table shape'):
                check_tables(damaged,SCHEMA)
        result=score.score_page(TRUTH[0],extra)
        self.assertEqual(result['cells_value_found'],84)
        self.assertEqual(result['rows_exact'],0)

    def test_consistent_missing_column_needs_schema(self):
        body='<table><tr><th>Site</th></tr><tr><td>Alder</td></tr></table>'
        check_tables(body)
        with self.assertRaisesRegex(ValueError,'table shape'):
            check_tables(body,SCHEMA)

    def test_missing_and_empty_page_blocks(self):
        for body in ('', '<PAGE>\n', '<PAGE>\nsynthetic'):
            with self.assertRaisesRegex(ValueError,'page coverage'):
                require_pages(body,40)
        require_pages('first\n<PAGE>\nsecond',2)
        require_pages('<PAGE>\nfirst\n<PAGE>\nsecond',2)
        self.assertEqual(score.cer('abc','axc'),1/3)


class ReportsAndSeam(Sandbox):
    def test_directory_report_selftest(self):
        with contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
            folder.selftest()
        self.assertIn('selftest OK',output.getvalue())
        with self.assertRaisesRegex(ValueError,'outside input'):
            folder.run(str(self.root),str(self.root/'nested'))

    def test_failed_lookup_and_dryrun_do_not_write(self):
        store=Mock()
        store.exists.side_effect=RuntimeError('lookup unavailable')
        with self.assertRaisesRegex(RuntimeError,'lookup unavailable'):
            seam.ingest(store,'synthetic','Quarterly: #1\nsecond',GOOD)
        store.create.assert_not_called()
        store.exists.side_effect=None; store.exists.return_value=True
        self.assertEqual(seam.ingest(store,'synthetic','title',GOOD,dry_run=True),'would refuse existing target')
        store.create.assert_not_called()

    def test_readback_and_normalization(self):
        store=Mock(); store.exists.return_value=False; store.read.return_value='wrong'
        with self.assertRaisesRegex(ValueError,'readback'):
            seam.ingest(store,'synthetic','title',GOOD)
        text=seam.prepare_page('Quarterly: #1\nsecond',GOOD+'\x0c![](images/page_0_0.jpg)')
        self.assertIn('"Quarterly: #1\\nsecond"',text)
        self.assertIn('<table',text)
        self.assertIn('[image crop omitted]',text)
        self.assertNotIn('\x0c',text)

    def test_aggregator_with_synthetic_raw_logs(self):
        raw=self.root/'raw'; run=raw/'sample'; (run/'raw').mkdir(parents=True)
        output=run/'runs/sample/out/p001'; output.mkdir(parents=True)
        meta={'label':'sample','pdf':'scan1.pdf','mode':'single_each','rc':0,'wall_s':57.74,'t0':'0','t1':'1'}
        (run/'meta.json').write_text(json.dumps(meta))
        (run/'raw/sample.mem').write_text('0 122368819\n1 107059609\n')
        (run/'raw/sample.stats').write_text('0 6.75GiB / 30GiB\n')
        (run/'raw/sample.stdout').write_text('[load] 44.0s\n[ocr] 1 pages 9.3s\nUOCR_DONE\n')
        (output/'result.md').write_text(GOOD)
        result=subprocess.run([sys.executable,str(ROOT/'scripts/ocr-aggregate.py'),str(raw),str(ROOT/'fixtures/truth.json'),str(ROOT/'scripts/ocr-score.py')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        row=json.loads(result.stdout)[0]
        self.assertEqual(row['score']['cells_value_found'],84)
        self.assertEqual(row['docker_stats_peak_gib'],6.75)
        self.assertEqual(row['load_s'],44.0)
        self.assertTrue(row['sentinel'])


if __name__=='__main__':
    unittest.main()
