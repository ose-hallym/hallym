"""Candidate4 self-check: exercises the revised gate with a stub bootstrap/agent and a fake transport.

Usage:  python -I selfcheck_candidate4.py <path to source/>
No Hermes source, no network, no real key. This does NOT replace the Hermes-bound suite (run_offline.py);
it only shows that each candidate4 change behaves as described, in isolation, on httpx 0.28.
"""
import sys, os, json, hashlib, copy, types, tempfile, importlib.util, pathlib, threading, time
SRC = pathlib.Path(sys.argv[1]).resolve(); TMP = pathlib.Path(tempfile.mkdtemp(prefix='cg4_'))
import httpx
sys.path.insert(0, str(SRC))
import cap_policy
KEY='SYNTHETIC-ONLY-2108ae-NOT-A-REAL-KEY'; MODEL='gemini-3.8-flash'
URL='https://generativelanguage.googleapis.com/v1beta/models/'+MODEL+':generateContent'
home=TMP/'home'; home.mkdir(); ledger=TMP/'ledger'
os.environ.update(HERMES_PROFILE='refomax', HERMES_HOME=str(home), GOOGLE_API_KEY=KEY)
def canonical(o): return json.dumps(o,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def wire(r): return {'method':r.method,'url':str(r.url),'headers':sorted(r.headers.multi_items()),'body_hex':r.content.hex()}
def digest(o): return hashlib.sha256(canonical(o)).hexdigest()
def payload(max_out=65535, thinking=None):
    gc={'maxOutputTokens':max_out,'temperature':0.0}
    if thinking is not None: gc['thinkingConfig']=thinking
    return {'contents':[{'role':'user','parts':[{'text':'Return SYNTHETIC_OK only.'}]}],
            'systemInstruction':{'parts':[{'text':'Synthetic packet.'}]},'generationConfig':gc}
pre=httpx.Client(trust_env=False)   # original httpx, built before install (issuance side)
def issuance_reject(reason): raise RuntimeError('issuance: '+reason)
def freeze(name, pl):
    req=pre.build_request('POST',URL,json=pl,headers={'x-goog-api-key':KEY}); raw=wire(req)
    capped=cap_policy.apply_cap(copy.deepcopy(pl), issuance_reject)
    body=json.dumps(capped,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
    req._content=body; req.stream=httpx.ByteStream(body); req.headers['content-length']=str(len(body))
    proof={'synthetic':True,'authorization_id':'H_'+name,'namespace':'HARNESS','valid_from':'2000-01-01','valid_through':'2999-12-31',
           'input_upper':16384,'output_plus_thinking_upper':4096,'candidates':1,'max_requests':1,'max_krw':56,
           'input_usd_million':'0.75','output_usd_million':'3.75','all_in_krw_per_usd':'2000','raw_wire_sha256':digest(raw),'wire_sha256':digest(wire(req))}
    return {'authorization_id':'H_'+name,'raw_wire_sha256':digest(raw),'raw_wire':raw,'final_wire':wire(req),'proof':proof}
CASES={n:freeze(n,payload()) for n in ('a','b','c','d','e')}
CASES['low']=freeze('low',payload(1024))
CASES['think']=freeze('think',payload(65535,{'includeThoughts':True,'thinkingBudget':24576,'thinkingLevel':'high'}))
CASES['dyn']=freeze('dyn',payload(65535,{'thinkingBudget':-1}))
ctx={'ledger':str(ledger),'profile_home':str(home),'namespace':'HARNESS','catalog_sha256':'harness','namespace_max_krw':1000,'cases':CASES}
boot=types.SimpleNamespace(current=lambda:json.loads(json.dumps(ctx))); sys.modules['trusted_bootstrap']=boot
pkg=types.ModuleType('agent'); pkg.__path__=[]; helpers=types.ModuleType('agent.chat_completion_helpers')
def _dispatch_nonstreaming_api_request(agent, kwargs, make_client=None):
    return agent.client._http.post(URL,json=kwargs['payload'],headers={'x-goog-api-key':agent.client.api_key})
helpers._dispatch_nonstreaming_api_request=_dispatch_nonstreaming_api_request
sys.modules['agent']=pkg; sys.modules['agent.chat_completion_helpers']=helpers
import isolated_integration as g
CAPTURES=[]
def fake(transport, request):
    CAPTURES.append(json.loads(request.content)); return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':'SYNTHETIC_OK'}]}}]},request=request)
g.install(fake)
class Client: api_key=KEY
class Agent: provider='gemini'; model=MODEL; tools=[]
agent=Agent(); agent.client=Client(); agent.client._http=httpx.Client()   # built after install
def dispatch(pl): return _dispatch_nonstreaming_api_request(agent,{'payload':pl})
def refused(fn):
    try: fn(); return None
    except g.Refused as e: return str(e)
def row_path(aid): return ledger/(hashlib.sha256(aid.encode()).hexdigest()+'.json')
R=[]; FAIL=0
def rep(tag, ok, detail):
    global FAIL; FAIL += (not ok); R.append((tag,'PASS' if ok else 'FAIL',detail)); print(f'[{"PASS" if ok else "FAIL"}] {tag}\n       {detail}')

g.arm('a',g.catalog('a')['proof'],agent); r=dispatch(payload()); gc=CAPTURES[-1]['generationConfig']
rep('C1 positive control: frozen packet admitted once, 65535->4096, candidateCount 1, row written',
    r.status_code==200 and len(CAPTURES)==1 and gc['maxOutputTokens']==4096 and gc['candidateCount']==1 and row_path('H_a').exists(),
    f'status={r.status_code} sends={len(CAPTURES)} cfg={gc}')
msg=refused(lambda:dispatch(payload()))
rep('C2 second send on same authority refused by ledger', msg is not None and 'already reserved' in msg and len(CAPTURES)==1, f'reason={msg!r}')

WRAP=[]
class Wrapper(httpx.BaseTransport):
    def __init__(self, inner): self._inner=inner
    def handle_request(self, request): WRAP.append(1); return httpx.Response(200,json={'bypassed':True},request=request)
g.arm('b',g.catalog('b')['proof'],agent)
wc=httpx.Client(transport=Wrapper(httpx.HTTPTransport())); m1=refused(lambda:wc.post(URL,json=payload(),headers={'x-goog-api-key':KEY})); wc.close()
oc=httpx.Client(); oc._transport.handle_request=lambda request:WRAP.append(2); m2=refused(lambda:oc.post(URL,json=payload(),headers={'x-goog-api-key':KEY})); oc.close()
try: httpx.HTTPTransport(True); m3='constructed'
except g.Refused as e: m3=str(e)
mc=httpx.Client(transport=httpx.MockTransport(lambda r:WRAP.append(3))); m4=refused(lambda:mc.post(URL,json={})); mc.close()
rep('C3 (H4) _inner wrapper, instance-level handle_request override, positional HTTPTransport args and MockTransport all refused before I/O',
    all(m and 'custom transport' in m for m in (m1,m2,m4)) and 'positional transport' in m3 and WRAP==[] and not row_path('H_b').exists(),
    f'wrapper={m1!r} override={m2!r} positional={m3!r} mock={m4!r} wrapper_calls={WRAP}')

g.arm('low',g.catalog('low')['proof'],agent); dispatch(payload(1024))
rep('C4 (M3) cap is min(): builder 1024 stays 1024 on wire', CAPTURES[-1]['generationConfig']['maxOutputTokens']==1024, f"on-wire maxOutputTokens={CAPTURES[-1]['generationConfig']['maxOutputTokens']}")

g.arm('think',g.catalog('think')['proof'],agent); dispatch(payload(65535,{'includeThoughts':True,'thinkingBudget':24576,'thinkingLevel':'high'}))
tc1=CAPTURES[-1]['generationConfig']['thinkingConfig']
g.arm('dyn',g.catalog('dyn')['proof'],agent); dispatch(payload(65535,{'thinkingBudget':-1}))
tc2=CAPTURES[-1]['generationConfig']['thinkingConfig']
try: freeze('bad',payload(65535,{'unknownKey':1})); m5='issued'
except RuntimeError as e: m5=str(e)
rep('C5 (H3) thinkingBudget 24576 -> 4096 and -1 (dynamic) -> 4096 on wire; issuance refuses unknown thinkingConfig keys',
    tc1=={'includeThoughts':True,'thinkingBudget':4096,'thinkingLevel':'high'} and tc2=={'thinkingBudget':4096} and 'unapproved shape' in m5,
    f'think={tc1} dyn={tc2} bad_issue={m5!r}')

gate=g.arm('c',g.catalog('c')['proof'],agent); old=g.NAMESPACE_MAX_KRW; g.NAMESPACE_MAX_KRW=0
try: m6=refused(lambda:dispatch(payload()))
finally: g.NAMESPACE_MAX_KRW=old
spent=g.cumulative_krw(56); n_before=len(CAPTURES); dispatch(payload())
rep('C6 (H2) namespace cumulative budget refuses before any row is written; restored cap admits again',
    m6 is not None and 'cumulative budget' in m6 and spent>0 and len(CAPTURES)==n_before+1 and row_path('H_c').exists(),
    f'reason={m6!r} cumulative_before={spent} KRW sends_after={len(CAPTURES)}')

p=TMP/'relocated_engine.py'; p.write_bytes((SRC/'isolated_integration.py').read_bytes())
spec=importlib.util.spec_from_file_location('relocated_engine',p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
before=httpx.HTTPTransport.handle_request; m7=None
try: m.install(lambda t,r:None)
except m.Refused as e: m7=str(e)
rep('C7 (M2) byte-identical relocated copy cannot install a second transport; original handler retained',
    m7 is not None and 'already installed' in m7 and httpx.HTTPTransport.handle_request is before, f'reason={m7!r}')

observed=[]; orig_open=pathlib.Path.open
def spy(self, mode='r', *a, **k):
    f=orig_open(self, mode, *a, **k)
    if 'x' in mode: observed.append(self.stat().st_size)
    return f
pathlib.Path.open=spy
try: g.arm('d',g.catalog('d')['proof'],agent); dispatch(payload())
finally: pathlib.Path.open=orig_open
slow=TMP/'slow-row.json'; slow.write_bytes(b'')
threading.Thread(target=lambda:(time.sleep(0.3), slow.write_bytes(canonical({'state':'RESERVED_CONSUMPTION_UNKNOWN','synthetic_krw':'56'})))).start()
t0=time.monotonic(); row=g.read_ledger_row(slow); dt=time.monotonic()-t0
(TMP/'never.json').write_bytes(b'')
try: g.read_ledger_row(TMP/'never.json', wait=0.0); m8='returned'
except RuntimeError as e: m8=str(e)
rep('C8 (M1) 0-byte row is observable right after exclusive create; read_ledger_row waits for complete JSON and times out on a stuck row',
    observed==[0] and row['state']=='RESERVED_CONSUMPTION_UNKNOWN' and 0.25<dt<2.0 and 'incomplete after wait' in m8,
    f'size_after_create={observed} waited={dt:.2f}s row={row} stuck={m8!r}')

sys.modules.pop('trusted_bootstrap'); import trusted_bootstrap as tb
try: tb.bind('WRITER', None); m9='bound'
except RuntimeError as e: m9=str(e)
sys.modules['trusted_bootstrap']=boot
rep('C9 (L) bind() without a trusted agent fails with a clear RuntimeError', 'trusted agent required' in m9, f'error={m9!r}')

boot.current=lambda:{k:v for k,v in json.loads(json.dumps(ctx)).items() if k!='namespace_max_krw'}
spec2=importlib.util.spec_from_file_location('engine_no_cap',TMP/'relocated_engine.py'); m2mod=importlib.util.module_from_spec(spec2)
try: spec2.loader.exec_module(m2mod); m10='imported'
except RuntimeError as e: m10=str(e)
boot.current=lambda:json.loads(json.dumps(ctx))
rep('C10 engine refuses to import from a context without namespace_max_krw (fail closed)', 'namespace_max_krw' in m10, f'error={m10!r}')

gate=g.arm('e',g.catalog('e')['proof'],agent); dispatch(payload())
row=json.loads(gate._path.read_bytes())
rep('C11 ledger row content and sealed gate unchanged by the revision', row['state']=='RESERVED_CONSUMPTION_UNKNOWN' and row['refund_allowed'] is False and refused(lambda:setattr(gate,'_path',TMP/'x.json')) is not None, f'row={row}')
print('\nRESULT:', 'ALL PASS' if FAIL==0 else f'{FAIL} FAILED', '| checks:', len(R), '| fake sends:', len(CAPTURES))
sys.exit(1 if FAIL else 0)
