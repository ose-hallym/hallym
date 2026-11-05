import os,sys,json,hashlib,stat
from pathlib import Path
W=Path(__file__).resolve().parent
Q=W.parent
B=Q.parent/'runtime-integration2-C65F5EA0'/'worker'
for k in ('TMPDIR','TEMP','TMP'):assert Path(os.environ[k]).resolve()==W/'scratch'
(W/'scratch').mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def safe(p):
 for n in [p,*p.parents]:
  s=n.lstat();assert not getattr(s,'st_file_attributes',0)&0x400
 s=p.lstat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1
rows=json.loads((Q/'PROTECTED-BEFORE.json').read_text());assert len(rows)==3745
for r in rows:
 p=Path(r['path']);safe(p);assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],str(p)
checks=[]
for rel,pin,count in [('runtime-integration2-C65F5EA0/worker','04ce7188dc0c485ffadfaeb7768b611a806059750bdb63696401c4e3bbaf6d33',620),('runtime-integration2-C65F5EA0/independent-check','46ad46e4d8f6e290ea2b3a5b33ef1bb53308d9ef100e3e364d2f49ea532cae16',579),('wire-diagnostic-544ABFE9/worker','46c23d3bdc90f03ba43f829bc9d25320b763569955d34ebb8c43c4abf2b442a9',549)]:
 root=Q.parent/rel;m=root/'MANIFEST.json';assert sha(m)==pin
 data=json.loads(m.read_text());entries=data['files'];assert len(entries)==count
 actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=m}
 assert actual=={r['path'] for r in entries}
 for r in entries:
  p=root/r['path'];safe(p);assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
 checks.append({'root':str(root),'count':count,'sha256':pin})
(W/'PROTECTED-PRECHECK.json').write_text(json.dumps({'count':len(rows),'all_match':True,'manifests':checks},indent=2))
(W/'baseline-source').mkdir()
for f in ['isolated_integration.py','trusted_bootstrap.py','runtime_fixture.py','suite_v2.py','test_runtime_cases.py','test_gate_negatives.py','test_lifecycle_paths.py','CATALOG-WRITER_FULL.json']:
 (W/'baseline-source'/f).write_bytes((B/f).read_bytes())
for f in ['startup-input-pins.json','FROZEN-FIXTURES.json']:
 (W/'baseline-source'/f).write_bytes((B/'baseline-source'/f).read_bytes())
assert sha(W/'baseline-source/isolated_integration.py')=='18acc1d4e3d025d56c3b586b9e7cc2f27f5533d3d89eccb97f2ddb866da8ebc3'
print(json.dumps({'protected':len(rows),'status':'PASS','python':sys.executable,'old_ledger_writes':0}))
