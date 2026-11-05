"""Complete candidate4 acceptance replay; failures and setup errors remain raw."""
import os,sys,io,json,unittest,hashlib,importlib.util
from pathlib import Path
import httpx
W=Path(os.environ['FIXTURE_ROOT']);C=Path(__file__).resolve().parent

def run(agent,g,fake,label):
 records=[]
 def run_class(cls):
  out=io.StringIO();res=unittest.TextTestRunner(stream=out,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
  rec={'tests':res.testsRun,'failures':len(res.failures),'errors':len(res.errors),'raw':out.getvalue()};print(rec['raw']);records.append(rec)
 def turn(thinking=False):
  agent.reasoning_config={'enabled':True,'effort':'high'} if thinking else {'enabled':False}
  return agent.run_conversation('Return SYNTHETIC_OK only.',system_message='Synthetic public source packet. No tools. No private data.')
 if label.startswith('processrace'):
  class ProcessRace(unittest.TestCase):
   def test_cold_process_fixed_authority_max_one(self):
    fake.CAPTURES.clear();fake.MODE='success'
    gate=g.arm('processrace',g.catalog('processrace')['proof'],agent)
    response=turn()
    self.assertLessEqual(len(fake.CAPTURES),1)
    row=g.read_ledger_row(gate._path)
    self.assertEqual(row['state'],'RESERVED_CONSUMPTION_UNKNOWN')
    (W/(label+'-race.json')).write_text(json.dumps({'captures':fake.CAPTURES,'ledger_sha256':hashlib.sha256(gate._path.read_bytes()).hexdigest(),'response':response},default=str))
  run_class(ProcessRace)
 elif label=='cold-spent':
  class Cold(unittest.TestCase):
   def test_cold_same_authorities_preserve_reservations(self):
    for name in ('success','continuation','thinking','timeout','429','500','empty','tool','concurrent'):
     with self.subTest(name=name):
      fake.CAPTURES.clear();gate=g.arm(name,g.catalog(name)['proof'],agent);before=gate._path.read_bytes()
      turn(thinking=name=='thinking');self.assertEqual(fake.CAPTURES,[]);self.assertEqual(gate._path.read_bytes(),before)
      self.assertTrue(any(e.get('reason')=='authorization already reserved or unknown consumption' for e in g.EVENTS[-8:]))
  run_class(Cold)
 else:
  import test_gate_negatives,test_lifecycle_paths
  for suffix,module in [('positive',fake),('negative',test_gate_negatives),('lifecycle',test_lifecycle_paths)]:
   os.environ['FIXTURE_LABEL']=label+'-'+suffix
   records.append(module.run(agent,g) if module is fake else module.run(agent,g,fake))
  class Contracts(unittest.TestCase):
   def setUp(self):
    fake.CAPTURES.clear();fake.MODE='success';agent.reasoning_config={'enabled':False}
   def test_auth_constructor_and_request_apis_have_zero_side_effects(self):
    seen=[]
    def callback(request):seen.append('callback');return request
    class EvilAuth(httpx.Auth):
     def auth_flow(self,request):
      seen.append('flow');yield request
    for auth in (callback,EvilAuth(),httpx.Auth(),('fake','only')):
     with self.subTest(auth=type(auth).__name__):
      for cls in (httpx.Client,httpx.AsyncClient):
       with self.assertRaisesRegex(g.Refused,'auth forbidden'):cls(auth=auth)
      with httpx.Client() as client:
       request=httpx.Request('POST',g.URL,headers={'x-goog-api-key':g.KEY},json={})
       calls=[lambda:client.send(request,auth=auth),lambda:client.post(g.URL,json={},auth=auth),lambda:client.request('POST',g.URL,json={},auth=auth),lambda:client.build_request('POST',g.URL,json={},auth=auth),lambda:client._build_auth(auth),lambda:client._build_request_auth(request,auth)]
       for call in calls:
        with self.assertRaisesRegex(g.Refused,'auth forbidden'):call()
       with self.assertRaisesRegex(g.Refused,'auth forbidden'):client.auth=auth
    for injected in (EvilAuth(),httpx.Auth()):
     with httpx.Client() as client:
      client._auth=injected
      with self.assertRaisesRegex(g.Refused,'auth forbidden'):client.post(g.URL,json={})
    with httpx.Client() as client:
     with self.assertRaisesRegex(g.Refused,'auth forbidden'):client.post('https://synthetic:only@generativelanguage.googleapis.com/',json={})
    self.assertEqual(seen,[])
    self.assertEqual(fake.CAPTURES,[])
   def test_frozen_context_and_malicious_prompt_cannot_self_authorize(self):
    catalog_path=W/'FROZEN-CATALOG.json';before=catalog_path.read_bytes()
    gate=g.arm('success',g.catalog('success')['proof'],agent)
    ledger_before=gate._path.read_bytes()
    agent.run_conversation('MALICIOUS arbitrary content is not approved.',system_message='Synthetic public source packet. No tools. No private data.')
    self.assertEqual(fake.CAPTURES,[])
    self.assertEqual(g.EVENTS[-1]['reason'],'raw final-built wire differs from frozen packet')
    self.assertEqual(before,catalog_path.read_bytes());self.assertEqual(ledger_before,gate._path.read_bytes())
   def test_non_gemini_agent_binding_refuses(self):
    old=agent.provider;g.arm('success',g.catalog('success')['proof'],agent)
    try:
     agent.provider='unapproved-non-Gemini'
     with self.assertRaisesRegex(g.Refused,'agent provider model tools changed'):
      from agent.chat_completion_helpers import _dispatch_nonstreaming_api_request
      body=json.loads(bytes.fromhex(g.catalog('success')['raw_wire']['body_hex']))
      _dispatch_nonstreaming_api_request(agent,{'model':g._CONTEXT['cases']['success']['proof']['model'],'messages':[{'role':'system','content':body['systemInstruction']['parts'][0]['text']},{'role':'user','content':'Return SYNTHETIC_OK only.'}],'max_tokens':4096},make_client=lambda *a,**kw:agent.client)
    finally:agent.provider=old
    self.assertEqual(fake.CAPTURES,[])
   def test_request_hook_rejected_before_invocation(self):
    seen=[]
    with self.assertRaisesRegex(g.Refused,'event hooks forbidden'):
     httpx.Client(event_hooks={'request':[lambda r:seen.append('side effect')]})
    client=httpx.Client();client.event_hooks['request'].append(lambda r:seen.append('side effect'))
    try:
     with self.assertRaisesRegex(g.Refused,'event hooks forbidden'):client.post(g.URL,json={})
    finally:client.close()
    self.assertEqual(seen,[])
   def test_byte_identical_relocation_preserves_spent_identity(self):
    raw=(C/'isolated_integration.py').read_bytes();p=W/'relocated_engine.py';p.write_bytes(raw)
    spec=importlib.util.spec_from_file_location('relocated_engine',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),hashlib.sha256(raw).hexdigest())
    one=g.arm('success',g.catalog('success')['proof'],agent);other=m.arm('success',m.catalog('success')['proof'],agent)
    self.assertEqual(one._path,other._path)
    request=httpx.Request('POST',g.URL,json={})
    before=one._path.read_bytes()
    with self.assertRaisesRegex(m.Refused,'already reserved'):other.reserve(request)
    self.assertEqual(one._path.read_bytes(),before)
   def test_bootstrap_rebind_and_new_real_authority_refused(self):
    import trusted_bootstrap as b
    with self.assertRaisesRegex(RuntimeError,'already bound'):b.bind('SYNTHETIC_REVIEW')
    for name in ('SYNTHETIC_UNKNOWN','AR-R2756D15D79F04F0FB6BDACEA8480C8E3'):
     with self.assertRaisesRegex(g.Refused,'unknown immutable'):g.arm(name,{},agent)
    self.assertIsNone(g.ACTIVE)
   def test_changed_root_and_namespace_do_not_refill(self):
    p=g.catalog('success')['proof'];original_namespace=p['namespace']
    p['namespace']='REVIEW' if original_namespace!='REVIEW' else 'WRITER'
    self.assertNotEqual(p['namespace'],original_namespace,'negative must actually differ')
    with self.assertRaisesRegex(g.Refused,'namespace mismatch'):g.arm('success',p,agent)
    g.arm('success',g.catalog('success')['proof'],agent)
    old=os.environ['HERMES_HOME'];os.environ['HERMES_HOME']=str(W/'new-unused-home')
    try:turn()
    finally:os.environ['HERMES_HOME']=old
    self.assertEqual(fake.CAPTURES,[]);self.assertEqual(g.EVENTS[-1]['reason'],'profile mismatch')
   def test_async_and_custom_transport_pre_io_refusal(self):
    co=httpx.AsyncClient.send(None,httpx.Request('POST',g.URL))
    with self.assertRaisesRegex(g.Refused,'async clients forbidden'):co.send(None)
    seen=[];client=httpx.Client(transport=httpx.MockTransport(lambda r:seen.append(r)))
    try:
     with self.assertRaisesRegex(g.Refused,'custom transport'):client.post(g.URL,json={})
    finally:client.close()
    self.assertEqual(seen,[])
   def test_unsupported_socket_attempt_denied_by_preimport_audit(self):
    import socket
    with self.assertRaises(PermissionError):socket.socket()
   def test_positive_raw65535_final4096_candidate1_evidence(self):
    self.assertTrue(any(e.get('decision')=='ORIGINAL_BUILDER_OBSERVED' and e['maxOutputTokens']==65535 for e in g.EVENTS))
    positives=records[0]['outcomes']
    for case in positives:
     self.assertEqual(len(case['captures']),1)
     cfg=case['captures'][0]['body']['generationConfig']
     self.assertEqual(cfg['maxOutputTokens'],4096);self.assertEqual(cfg['candidateCount'],1)
   def test_wire_and_key_rejections_are_not_profile_masked(self):
    reasons=[e.get('reason') for e in records[1]['guard_events']]
    for expected in ('raw final-built wire differs from frozen packet','unapproved method host path model key','credential environment refresh mismatch'):
     self.assertIn(expected,reasons)
   def test_relocated_copy_cannot_install_second_transport(self):
    raw=(C/'isolated_integration.py').read_bytes();p=W/'relocated_install_engine.py';p.write_bytes(raw)
    spec=importlib.util.spec_from_file_location('relocated_install_engine',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    before=httpx.HTTPTransport.handle_request
    with self.assertRaisesRegex(m.Refused,'already installed'):m.install(lambda t,r:None)
    self.assertIs(httpx.HTTPTransport.handle_request,before)
   def test_wrapper_transport_and_positional_transport_args_refused(self):
    seen=[]
    class Wrapper(httpx.BaseTransport):
     def __init__(self,inner):self._inner=inner
     def handle_request(self,request):seen.append('wrapper dispatched');return httpx.Response(200,request=request)
    client=httpx.Client(transport=Wrapper(httpx.HTTPTransport()))
    try:
     with self.assertRaisesRegex(g.Refused,'custom transport'):client.post(g.URL,json={})
    finally:client.close()
    client=httpx.Client();client._transport.handle_request=lambda request:seen.append('instance override')
    try:
     with self.assertRaisesRegex(g.Refused,'custom transport'):client.post(g.URL,json={})
    finally:client.close()
    with self.assertRaisesRegex(g.Refused,'positional transport'):httpx.HTTPTransport(True)
    self.assertEqual(seen,[]);self.assertEqual(fake.CAPTURES,[])
   def test_namespace_cumulative_budget_refuses_before_reservation(self):
    gate=g.arm('title',g.catalog('title')['proof'],agent);old=g.NAMESPACE_MAX_KRW;g.NAMESPACE_MAX_KRW=0
    try:turn()
    finally:g.NAMESPACE_MAX_KRW=old
    self.assertEqual(fake.CAPTURES,[]);self.assertEqual(g.EVENTS[-1]['reason'],'namespace cumulative budget exceeded');self.assertFalse(gate._path.exists())
    self.assertGreater(g.cumulative_krw(56),0)
   def test_cap_policy_min_and_thinking_budget_clamp(self):
    import cap_policy
    def raiser(reason):raise AssertionError(reason)
    obj={'generationConfig':{'maxOutputTokens':1024,'thinkingConfig':{'thinkingBudget':24576,'includeThoughts':False,'thinkingLevel':'high'}}}
    cap_policy.apply_cap(obj,raiser);cfg=obj['generationConfig']
    self.assertEqual((cfg['maxOutputTokens'],cfg['candidateCount'],cfg['thinkingConfig']['thinkingBudget']),(1024,1,cap_policy.THINKING_BUDGET_UPPER))
    obj={'generationConfig':{'maxOutputTokens':65535,'thinkingConfig':{'thinkingBudget':-1}}}
    cap_policy.apply_cap(obj,raiser);self.assertEqual((obj['generationConfig']['maxOutputTokens'],obj['generationConfig']['thinkingConfig']['thinkingBudget']),(4096,cap_policy.THINKING_BUDGET_UPPER))
    for bad in ({'thinkingBudget':'1'},{'unknownKey':1},{'includeThoughts':1},{'thinkingLevel':''}):
     with self.subTest(bad=bad),self.assertRaises(AssertionError):cap_policy.apply_cap({'generationConfig':{'maxOutputTokens':1,'thinkingConfig':bad}},raiser)
  run_class(Contracts)
 summary={'tests':sum(r['tests'] for r in records),'failures':sum(r['failures'] for r in records),'errors':sum(r['errors'] for r in records),'groups':records,'actual_existing_bot':'NOT_RUN','live_entry_enabled':False}
 (W/(label+'-suite.json')).write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
 return {k:v for k,v in summary.items() if k!='groups'}
