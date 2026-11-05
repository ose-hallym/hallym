"""Trusted local test controller; no agent/reviewer dispatch, no network."""
import os,sys,json,hashlib,subprocess,time
from pathlib import Path
C=Path(__file__).resolve().parent
for k in ('TMPDIR','TEMP','TMP'):assert Path(os.environ[k]).resolve().is_relative_to(C/'scratch')
label,ns=sys.argv[1:3]
if (C/'FINAL-PINS.json').exists():
 pins=json.loads((C/'FINAL-PINS.json').read_text())
 for name,sha in pins['sources'].items():
  assert hashlib.sha256((C/name).read_bytes()).hexdigest()==sha,'frozen final source mismatch '+name
assert label.replace('-','').isalnum()
assert ns in ('RED','DEVELOPMENT','WRITER','PARENT','REVIEW')
if ns in ('PARENT','REVIEW'):assert C.name=='independent-check','reserved for parent'
root=C/'scratch'/ns
root.mkdir(parents=True,exist_ok=True)
receipt=root/(label+'-command.json');assert not receipt.exists(),'no overwrite or authority refill'
home=root/'fixture-home';profile=home/'profiles/refomax';profile.mkdir(parents=True,exist_ok=True)
(home/'appdata').mkdir(exist_ok=True)
cfg='model:\n  default: gemini-3.8-flash\n  provider: gemini\n  streaming: false\nagent:\n  api_max_retries: 1\n  auto_recovery_cycles: 0\ncompression:\n  enabled: false\nsession:\n  auto_title: false\n  title_model_upgrade: false\n'
p=profile/'config.yaml'
if not p.exists():p.write_text(cfg)
else:assert p.read_text()==cfg
keep=('SYSTEMROOT','WINDIR','COMSPEC');env={k:os.environ[k] for k in keep if k in os.environ}
env.update({k:str(root) for k in ('TMPDIR','TEMP','TMP')})
env.update(HOME=str(home),USERPROFILE=str(home),LOCALAPPDATA=str(home/'appdata'),APPDATA=str(home/'appdata'),HERMES_HOME=str(profile),HERMES_PROFILE='refomax',PATH=str(Path(sys.executable).parent),PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',PYTHONUTF8='1',HERMES_DISABLE_LAZY_INSTALLS='1',GOOGLE_API_KEY='SYNTHETIC-ONLY-2108ae-NOT-A-REAL-KEY',NO_PROXY='*',TERMINAL_ENV='local',FIXTURE_LABEL=label,FIXTURE_NAMESPACE=ns,FIXTURE_ROOT=str(root))
script='red_fixture.py' if ns=='RED' else 'runtime_fixture.py'
cmd=[sys.executable,'-B','-I','-S',str(C/script)]
snap=root/(label+'-snapshot');snap.mkdir()
for p in C.glob('*.py'):(snap/p.name).write_bytes(p.read_bytes())
start=time.monotonic()
try:
 p=subprocess.run(cmd,cwd=str(home),env=env,capture_output=True,timeout=240)
 out,err,code=p.stdout,p.stderr,p.returncode
except subprocess.TimeoutExpired as e:out,err,code=e.stdout or b'',e.stderr or b'',124
(root/(label+'.out')).write_bytes(out);(root/(label+'.err')).write_bytes(err)
record={'argv':cmd,'cwd':str(home),'environment':env,'exit_code':code,'elapsed':time.monotonic()-start,'stdout_sha256':hashlib.sha256(out).hexdigest(),'stderr_sha256':hashlib.sha256(err).hexdigest(),'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in C.glob('*.py')}}
receipt.write_text(json.dumps(record,indent=2));print(json.dumps({'receipt':str(receipt),'exit':code,'stdout_bytes':len(out),'stderr_bytes':len(err)}))
raise SystemExit(code)
