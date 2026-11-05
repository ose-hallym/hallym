"""Prerequisite test: full Hermes import/constructor/run, NOT an AST replay.

An import failure is SETUP_BLOCKED, never the cost-guard behavioral RED.
Run only through run_isolated.py (clean environment, -I -S, no .pth execution).
"""
import sys
import os
import json
import hashlib
import stat
import traceback
import importlib.abc
import importlib.util
from pathlib import Path

C = Path(__file__).resolve().parent
W = Path(os.environ['FIXTURE_ROOT']).resolve()
S = Path('D:/Hermes/hermes-agent').resolve()
M = W / 'scratch' / 'source-mirror'
for key in ('TMPDIR', 'TEMP', 'TMP'):
    assert Path(os.environ[key]).resolve() == W
assert Path(os.environ['HERMES_HOME']).resolve().is_relative_to(W)
assert os.environ.get('GOOGLE_API_KEY') == 'SYNTHETIC-ONLY-2108ae-NOT-A-REAL-KEY'
sys.dont_write_bytecode = True
# Explicit dependency location only: never execute editable .pth/sitecustomize.
DEPS = Path(sys.prefix) / 'Lib' / 'site-packages'
sys.path.append(str(DEPS))
READ_ROOTS = [Path(sys.base_prefix).resolve(), DEPS.resolve()]
PINS = {}
EVENTS = []
EXECUTED = set()
READS = set()

class IsolationDenied(PermissionError):
    """Ordinary OS denial: callers may handle it, but the operation never occurs.

    The prior BaseException stop-on-first-observation variant is preserved in
    startup snapshots. The allowed file/socket/process sets are unchanged.
    """
    pass

def contained(path, root):
    return path == root or path.is_relative_to(root)

def safe_shape(path):
    # Reject reparse ancestors and hardlinks before read/write. Missing leaf OK.
    for part in [path, *path.parents]:
        try:
            st = part.lstat()
        except FileNotFoundError:
            continue
        if getattr(st, 'st_file_attributes', 0) & 0x400:
            raise IsolationDenied('reparse path: ' + str(part))
        if stat.S_ISREG(st.st_mode) and st.st_nlink != 1:
            raise IsolationDenied('non-singlelink: ' + str(part))

def deny(event, path):
    EVENTS.append({'event': event, 'path': str(path), 'action': 'DENIED_BEFORE_OPERATION'})
    raise IsolationDenied(event + ': ' + str(path))

def check_write(event, name):
    p = Path(os.fsdecode(name)).absolute()
    safe_shape(p)
    if not contained(p.resolve(), W):
        deny(event, p)

def audit(event, args):
    if event.startswith('socket.') or event in ('subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn', 'os.spawn', 'os.fork'):
        deny(event, 'NO_SOCKET_OR_PROCESS_ALLOWED')
    if event == 'open':
        name, mode, flags = args
        if isinstance(name, int):
            if name not in (0, 1, 2):
                deny(event, 'unexpected fd')
            return
        p = Path(os.fsdecode(name)).absolute()
        write = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if write:
            check_write(event, p)
            return
        safe_shape(p)
        p = p.resolve()
        if contained(p, W) or contained(p, C) or any(contained(p, root) for root in READ_ROOTS):
            READS.add(str(p))
            return
        if contained(p, S) and p.suffix == '.py' and not any(x in p.parts for x in ('profiles', '.git', '.hermes')):
            READS.add(str(p))
            return
        deny(event, p)
    if event in ('os.mkdir', 'os.rmdir', 'os.remove', 'os.truncate', 'os.chmod', 'os.utime'):
        check_write(event, args[0])
    if event in ('os.rename', 'os.replace', 'os.link', 'os.symlink'):
        check_write(event, args[0])
        check_write(event, args[1])
    if event in ('os.listdir', 'os.scandir'):
        name = args[0]
        if isinstance(name, int):
            deny(event, 'directory fd')
        p = Path(name or os.getcwd()).resolve()
        if not (contained(p, W) or contained(p, C) or contained(p, S) or any(contained(p, root) for root in READ_ROOTS)):
            deny(event, p)

class MirrorLoader(importlib.abc.Loader):
    def __init__(self, name, original, mirrored, package):
        self.name, self.original, self.mirrored, self.package = name, original, mirrored, package
    def create_module(self, spec):
        return None
    def exec_module(self, module):
        raw = self.original.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        rel = self.original.relative_to(S).as_posix()
        expected = BASE_PINS.get(rel)
        if expected is not None and expected['sha256'] != sha:
            raise IsolationDenied('source changed: ' + rel)
        PINS[rel] = {'sha256': sha, 'bytes': len(raw), 'original': str(self.original), 'mirror': str(self.mirrored)}
        self.mirrored.parent.mkdir(parents=True, exist_ok=True)
        self.mirrored.write_bytes(raw)
        module.__file__ = str(self.mirrored)
        module.__cached__ = None
        if self.package:
            module.__path__ = [str(self.mirrored.parent)]
        exec(compile(raw, str(self.mirrored), 'exec'), module.__dict__)

class MirrorFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        rel = Path(*fullname.split('.'))
        for candidate, package in ((rel / '__init__.py', True), (rel.with_suffix('.py'), False)):
            original = S / candidate
            if original.is_file():
                mirrored = M / candidate
                loader = MirrorLoader(fullname, original, mirrored, package)
                return importlib.util.spec_from_file_location(fullname, mirrored, loader=loader,
                    submodule_search_locations=[str(mirrored.parent)] if package else None)
        return None

def trace(frame, event, arg):
    if event == 'call':
        filename = frame.f_code.co_filename
        if filename.startswith(str(M)):
            EXECUTED.add((str(Path(filename).relative_to(M)).replace('\\', '/'), frame.f_code.co_qualname, frame.f_code.co_firstlineno))
    return trace


BASE_PINS = json.loads((C/'baseline-source/startup-input-pins.json').read_text())
LABEL=os.environ['FIXTURE_LABEL']
import socket
socket.gethostname=lambda:'SYNTHETIC-OFFLINE-HOST'
M.mkdir(parents=True,exist_ok=True)
(W/'scratch').mkdir(exist_ok=True)
sys.addaudithook(audit)
sys.meta_path.insert(0,MirrorFinder())
sys.path.insert(0,str(C))
sys.settrace(trace)
import types,unittest,io
ctx=json.loads((C/'baseline-source/CATALOG-WRITER_FULL.json').read_text())
sys.modules['trusted_bootstrap']=types.SimpleNamespace(current=lambda:{'ledger':str(W/'never-ledger'),'profile_home':str(W/'fixture-home/profiles/refomax'),'namespace':'WRITER_FULL','cases':ctx['cases']})
spec=importlib.util.spec_from_file_location('baseline_engine',C/'baseline-source/isolated_integration.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
g.install(lambda *a: (_ for _ in ()).throw(AssertionError('no fake send allowed')))
import httpx
seen=[]
class Red(unittest.TestCase):
 def test_auth_callback_must_not_execute(self):
  def auth(request):seen.append('actual_HTTPX_auth_side_effect');return request
  with httpx.Client(auth=auth) as client:
   with self.assertRaises(g.Refused):client.post(g.URL,json={})
  self.assertEqual(seen,[],'auth executed before gate: intended RED')
 def test_original_same_namespace_negative(self):
  proof=g.catalog('success')['proof'];proof['namespace']='WRITER_FULL'
  self.assertEqual(proof['namespace'],g._CONTEXT['namespace'])
  with self.assertRaisesRegex(g.Refused,'namespace mismatch'):g.arm('success',proof,object())
stream=io.StringIO();res=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Red))
print(stream.getvalue())
(W/'red-result.json').write_text(json.dumps({'tests':res.testsRun,'failures':len(res.failures),'errors':len(res.errors),'auth_side_effects':seen,'raw':stream.getvalue(),'baseline_sha256':hashlib.sha256((C/'baseline-source/isolated_integration.py').read_bytes()).hexdigest(),'audit_denials':EVENTS},indent=2))
raise SystemExit(1 if res.failures or res.errors else 0)
