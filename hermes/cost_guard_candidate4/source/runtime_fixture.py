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
sys.setprofile(trace)
import threading
threading.setprofile(trace)
result={'status':'SETUP_RUNNING','actual_existing_bot':'NOT_RUN','vendor_charge':'NOT_RUN','audit_is_OS_sandbox':False}
try:
 import httpx
 saved_send=httpx.Client.send
 def startup_deny(*args,**kw):raise IsolationDenied('preflight forbids every send')
 httpx.Client.send=startup_deny
 import run_agent
 result['full_module_import']=True
 agent=run_agent.AIAgent(api_key=os.environ['GOOGLE_API_KEY'],base_url='https://generativelanguage.googleapis.com/v1beta',provider='gemini',model='gemini-3.8-flash',enabled_toolsets=[],disabled_toolsets=['all'],max_tokens=4096,max_iterations=1,reasoning_config={'enabled':False},credential_pool=None,fallback_model={},skip_context_files=True,skip_memory=True,skip_background_review=True,load_soul_identity=False,save_trajectories=False,quiet_mode=True,cwd=str(W/'fixture-home'),side_agent=True)
 result['actual_constructor']=True
 import trusted_bootstrap
 context=trusted_bootstrap.bind(os.environ['FIXTURE_NAMESPACE'],agent)
 result['catalog_sha256']=context['catalog_sha256']
 if LABEL=='context-red':
  old=json.loads((C/'baseline-source/CATALOG-WRITER_FULL.json').read_text())['cases']['success']['raw_wire_sha256']
  new=context['cases']['success']['raw_wire_sha256']
  result['wire_red']={'old':old,'context_built':new,'provenance':'trusted builders before arm, not outgoing capture'}
  assert new==old,'intended RED: old-root packet cannot authorize changed context'
 else:
  httpx.Client.send=saved_send
  import isolated_integration as g
  import test_runtime_cases as cases
  g.install(cases.FakeTransport().handle)
  if LABEL=='positive-green':
   gate=g.arm('success',g.catalog('success')['proof'],agent)
   response=agent.run_conversation('Return SYNTHETIC_OK only.',system_message='Synthetic public source packet. No tools. No private data.')
   result['positive']={'response':response,'captures':cases.CAPTURES}
   assert len(cases.CAPTURES)==1 and 'SYNTHETIC_OK' in str(response)
   result['status']='GREEN'
  else:
   import suite_v3
   result['suite']=suite_v3.run(agent,g,cases,LABEL)
   result['status']='GREEN' if result['suite']['failures']==0 and result['suite']['errors']==0 else 'FAIL_INCOMPLETE'
except AssertionError as exc:
 result.update(status='ASSERTION_FAILURE',exception=str(exc),traceback=''.join(traceback.format_exception(exc)))
except BaseException as exc:
 result.update(status='SETUP_BLOCKED',exception_type=type(exc).__name__,exception=str(exc),traceback=''.join(traceback.format_exception(exc)))
finally:
 sys.setprofile(None);threading.setprofile(None)
 result['audit_denials']=EVENTS;result['source_pins']=PINS
 result['executed_functions']=[{'source':a,'qualname':b,'line':c} for a,b,c in sorted(EXECUTED)]
 result['read_paths']=sorted(READS)
 result['source_postcheck']={k:hashlib.sha256(Path(v['original']).read_bytes()).hexdigest()==v['sha256'] for k,v in PINS.items()}
 result['guard_events']=getattr(locals().get('g'),'EVENTS',[])
 result['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in C.glob('*.py')}
 with (W/(LABEL+'-result.json')).open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2,default=str)
 print(json.dumps({k:v for k,v in result.items() if k in ('status','exception','suite','wire_red')},default=str))
raise SystemExit(0 if result['status']=='GREEN' else 2)
