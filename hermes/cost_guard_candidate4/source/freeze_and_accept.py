"""One final freeze and one predetermined acceptance pass; no candidate repair."""
import os,sys,json,hashlib,subprocess,concurrent.futures,stat
from pathlib import Path
C=Path(__file__).resolve().parent
for k in ('TMPDIR','TEMP','TMP'):assert Path(os.environ[k]).resolve()==C/'scratch'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(name,obj):
 with (C/name).open('x',encoding='utf-8') as f:json.dump(obj,f,indent=2)
assert not (C/'FINAL-PINS.json').exists(),'final freeze never replaced'
from trusted_inputs import ROOTS,CASES,PREFIX
allocations={ns:{'root':str(root),'ledger':str(root/'ledger'),'authority_ids':[PREFIX+ns+'_'+case for case in CASES]} for ns,root in ROOTS.items()}
ids=[x for v in allocations.values() for x in v['authority_ids']];assert len(set(ids))==len(ids)
put('ISSUED-ALLOCATIONS.json',{'synthetic_only':True,'live_entry_enabled':False,'allocations':allocations,'authority_count':len(ids),'same_authority_can_change_root':False})
# Additional original Hermes imports pinned before final runtime; source code only.
source_pins={}
for p in [C/'scratch/DEVELOPMENT/context-red-result.json',C/'scratch/DEVELOPMENT/positive-green-result.json']:
 data=json.loads(p.read_text(encoding='utf-8'))
 for rel,row in data['source_pins'].items():source_pins[rel]=row
originals=[]
for rel,row in sorted(source_pins.items()):
 p=Path(row['original']);st=p.lstat();assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and not getattr(st,'st_file_attributes',0)&0x400
 assert sha(p)==row['sha256'];originals.append({'path':str(p),'bytes':st.st_size,'sha256':row['sha256']})
httpx_path=Path(sys.prefix)/'Lib/site-packages/httpx/_client.py'
originals.append({'path':str(httpx_path),'bytes':httpx_path.stat().st_size,'sha256':sha(httpx_path)})
put('ADDED-SOURCE-PINS.json',originals)
files={p.name:sha(p) for p in C.glob('*.py')}
put('FINAL-PINS.json',{'candidate_sha256':files['isolated_integration.py'],'sources':files,'allocations_sha256':sha(C/'ISSUED-ALLOCATIONS.json'),'original_sources_sha256':sha(C/'ADDED-SOURCE-PINS.json'),'scope':'one additional candidate3/max3/no automatic fourth','accepted':False})
print(json.dumps({'frozen_candidate':files['isolated_integration.py'],'source_files':len(files),'additional_originals':len(originals)}),flush=True)
results=[]
def launch(label):
 cmd=[sys.executable,'-B',str(C/'run_offline.py'),label,'WRITER']
 p=subprocess.run(cmd,cwd='C:/Users/HERMEZ',env=dict(os.environ),capture_output=True,timeout=270)
 (C/'scratch'/('controller-'+label+'.out')).write_bytes(p.stdout)
 (C/'scratch'/('controller-'+label+'.err')).write_bytes(p.stderr)
 return {'label':label,'argv':cmd,'exit':p.returncode}
r=launch('full-final');results.append(r);print(json.dumps(r),flush=True)
if r['exit']==0:
 r=launch('cold-spent');results.append(r);print(json.dumps(r),flush=True)
 if r['exit']==0:
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:race=list(ex.map(launch,['processraceA','processraceB']))
  results.extend(race)
  if all(r['exit']==0 for r in race):
   rows=[json.loads((C/'scratch/WRITER'/(name+'-race.json')).read_text()) for name in ('processraceA','processraceB')]
   result={'total_fake_sends':sum(len(r['captures']) for r in rows),'ledger_sha256s':[r['ledger_sha256'] for r in rows]}
   result['pass']=result['total_fake_sends']==1 and len(set(result['ledger_sha256s']))==1
   put('COLD-PROCESS-RACE.json',result)
for name,pin in files.items():assert sha(C/name)==pin
put('FINAL-EXECUTIONS.json',{'runs':results,'same_final_source':True,'scope':'predetermined full/cold/race; stop on failure; no repaired subsets'})
print(json.dumps({'runs':results,'same_final_source':True}))
raise SystemExit(0 if all(r['exit']==0 for r in results) else 2)
