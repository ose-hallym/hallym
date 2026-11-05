import os
from pathlib import Path
C=Path(__file__).resolve().parent
for k in ('TMPDIR','TEMP','TMP'):assert Path(os.environ[k]).resolve()==C/'scratch'
prefix=(C/'baseline-source/runtime_fixture.py').read_text().split("result={'status':'SETUP_RUNNING'")[0]
# Thread profiling, not expensive line tracing; keep all executed source pins.
prefix=prefix.replace('sys.settrace(trace)','sys.setprofile(trace)')
tail='''import threading
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
'''
(C/'runtime_fixture.py').write_text(prefix+tail)
