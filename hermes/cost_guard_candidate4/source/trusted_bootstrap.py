"""Trusted preflight builds fixed content, never consumes outgoing observations."""
import os,json,hashlib,copy,stat
from pathlib import Path
from trusted_inputs import ROOTS,USER,SYSTEM,KEY,MODEL,URL,CASES,PREFIX,VALID_FROM,VALID_THROUGH,NAMESPACE_MAX_KRW
from cap_policy import apply_cap,MAX_OUTPUT_TOKENS,CANDIDATE_COUNT
_BOUND=None
def _issuance_reject(reason):raise RuntimeError('trusted issuance cap policy: '+reason)

def canonical(obj):return json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def wire(r):return {'method':r.method,'url':str(r.url),'headers':sorted(r.headers.multi_items()),'body_hex':r.content.hex()}
def digest(obj):return hashlib.sha256(canonical(obj)).hexdigest()
def safe(path):
 for p in [path,*path.parents]:
  if p.exists():
   st=p.lstat()
   if getattr(st,'st_file_attributes',0)&0x400 or (stat.S_ISREG(st.st_mode) and st.st_nlink!=1):raise RuntimeError('unsafe context shape')

def bind(namespace,agent=None):
 global _BOUND
 if _BOUND is not None:raise RuntimeError('bootstrap already bound; no rebind')
 if namespace not in ROOTS:raise RuntimeError('unissued namespace')
 if agent is None:raise RuntimeError('trusted agent required')
 root=ROOTS[namespace].resolve();home=root/'fixture-home/profiles/refomax';ledger=root/'ledger'
 for key in ('TMPDIR','TEMP','TMP','FIXTURE_ROOT'):
  if Path(os.environ[key]).resolve()!=root:raise RuntimeError('bootstrap root mismatch '+key)
 if Path(os.environ['HERMES_HOME']).resolve()!=home or os.environ['HERMES_PROFILE']!='refomax':raise RuntimeError('bootstrap profile mismatch')
 if agent.provider!='gemini' or agent.model!=MODEL or agent.tools or agent.client.api_key!=KEY:raise RuntimeError('untrusted agent construction')
 safe(root)
 from agent.gemini_native_adapter import build_gemini_request,gemini_accepts_parameters_json_schema
 import httpx
 # No run_conversation, send, transport callback or user-supplied prompt participates.
 system=agent._build_system_prompt(SYSTEM)
 messages=[{'role':'system','content':system},{'role':'user','content':USER}]
 packets={};old_reason=agent.reasoning_config
 for kind,reason in [('plain',{'enabled':False}),('thinking',{'enabled':True,'effort':'high'})]:
  agent.reasoning_config=reason
  kw=agent._build_api_kwargs(copy.deepcopy(messages),tools_for_api=[])
  extra=kw.get('extra_body') or {}
  payload=build_gemini_request(messages=kw['messages'],tools=kw.get('tools'),tool_choice=kw.get('tool_choice'),temperature=kw.get('temperature'),max_tokens=kw.get('max_tokens'),top_p=kw.get('top_p'),stop=kw.get('stop'),thinking_config=extra.get('thinking_config') or extra.get('thinkingConfig'),response_format=kw.get('response_format') or extra.get('response_format'),model=MODEL,tools_as_json_schema=gemini_accepts_parameters_json_schema(agent.client.base_url))
  request=agent.client._http.build_request('POST',URL,json=payload,headers=agent.client._headers())
  raw=wire(request)
  capped=apply_cap(copy.deepcopy(payload),_issuance_reject)
  body=json.dumps(capped,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
  request._content=body;request.stream=httpx.ByteStream(body);request.headers['content-length']=str(len(body))
  packets[kind]={'raw_wire':raw,'final_wire':wire(request),'trusted_api_kwargs':kw}
 agent.reasoning_config=old_reason
 cases={}
 for name in CASES:
  pkt=packets['thinking' if name=='thinking' else 'plain'];aid=PREFIX+namespace+'_'+name
  proof={'synthetic':True,'authorization_id':aid,'namespace':namespace,'root':str(root),'profile_home':str(home),'ledger':str(ledger),'profile':'refomax','provider':'gemini','model':MODEL,'fakekey':KEY,'credential_id':'2108ae','credential_source':'GOOGLE_API_KEY','project':'SYNTHETIC-PAID-PROJECT-NOT-REAL','project_authority':'SYNTHETIC-ONLY','raw_wire_sha256':digest(pkt['raw_wire']),'wire_sha256':digest(pkt['final_wire']),'input_upper':16384,'output_plus_thinking_upper':MAX_OUTPUT_TOKENS,'candidates':CANDIDATE_COUNT,'max_requests':1,'max_krw':56,'input_usd_million':'0.75','output_usd_million':'3.75','all_in_krw_per_usd':'2000','fx_tax_fees_rounding':'SYNTHETIC-ALL-IN-CEIL-NO-FIXED-FEES','vendor_semantics':'SYNTHETIC-COMBINED-OUTPUT-THINKING-ONE-CANDIDATE','token_proof':'SYNTHETIC-ASSUMED-UPPER-BOUND-NOT-VENDOR-TOKEN-PROOF','valid_from':VALID_FROM,'valid_through':VALID_THROUGH,'purpose':'main','trusted_input_sha256':digest({'user':USER,'system':SYSTEM})}
  cases[name]={'authorization_id':aid,'raw_wire_sha256':proof['raw_wire_sha256'],'raw_wire':pkt['raw_wire'],'final_wire':pkt['final_wire'],'proof':proof}
 cat={'schema':'trusted-synthetic-context-v4','namespace_max_krw':NAMESPACE_MAX_KRW,'namespace':namespace,'root':str(root),'profile_home':str(home),'ledger':str(ledger),'cases':cases,'live_entry_enabled':False}
 raw=canonical(cat);path=root/'FROZEN-CATALOG.json';safe(path)
 if path.exists():
  if path.read_bytes()!=raw:raise RuntimeError('context catalog mismatch; no recapture/rewrite/refill')
 else:
  with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 provenance={'producer':'trusted fixed-input original system/API/native builders + HTTPX.build_request; no send','outgoing_capture_used':False,'namespace':namespace,'catalog_sha256':hashlib.sha256(raw).hexdigest(),'trusted_input_sha256':digest({'user':USER,'system':SYSTEM}),'packets':packets}
 pp=root/'EXPECTED-PROVENANCE.json'
 if not pp.exists():
  with pp.open('xb') as f:f.write(canonical(provenance))
 cat['catalog_sha256']=hashlib.sha256(raw).hexdigest()
 _BOUND=canonical(cat)
 return current()

def current():
 if _BOUND is None:raise RuntimeError('trusted preflight not completed')
 return json.loads(_BOUND)
