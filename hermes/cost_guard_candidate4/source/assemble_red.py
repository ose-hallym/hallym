# Harness assembly only: unchanged original audit prefix, explicit test tail.
import os
from pathlib import Path
W=Path(__file__).resolve().parent
for k in ('TMPDIR','TEMP','TMP'):assert Path(os.environ[k]).resolve()==W/'scratch'
prefix=(W/'baseline-source/runtime_fixture.py').read_text().split("result={'status':'SETUP_RUNNING'")[0]
tail='''import types,unittest,io
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
'''
(W/'red_fixture.py').write_text(prefix+tail)
