"""Additional gate contracts, including a test-first arming invalidation regression."""
import os
import io
import json
import unittest
import threading
import copy
from pathlib import Path
import httpx

W = Path(os.environ['FIXTURE_ROOT'])

def run(agent, g, fixtures):
    outcomes = []
    events_start = len(g.EVENTS)
    captures = fixtures.CAPTURES
    def turn(mode):
        fixtures.MODE = mode
        agent.reasoning_config = {'enabled': False}
        response = agent.run_conversation('Return SYNTHETIC_OK only.', system_message='Synthetic public source packet. No tools. No private data.')
        outcomes.append({'case': mode, 'response': response, 'captures': copy.deepcopy(captures)})
        return response
    class Negatives(unittest.TestCase):
        def setUp(self):
            captures.clear()
        def test_missing_proof_disarms_previous_authority(self):
            g.arm('timeout', g.catalog('timeout')['proof'], agent)
            with self.assertRaises(g.Refused):
                g.arm('timeout', None, agent)
            self.assertIsNone(g.ACTIVE, 'failed arming must not retain earlier unused authority')
            turn('success')
            self.assertEqual(captures, [])
        def test_authority_exact_types_and_missing_fields(self):
            original = g.catalog('success')['proof']
            for field in ('input_upper', 'output_plus_thinking_upper', 'candidates', 'max_requests', 'max_krw'):
                for value in (True, False, float(original[field]), str(original[field])):
                    with self.subTest(field=field, value=value):
                        proof = dict(original, **{field: value})
                        with self.assertRaises(g.Refused):
                            g.arm('success', proof, agent)
            for field in original:
                with self.subTest(missing=field):
                    proof = dict(original)
                    del proof[field]
                    with self.assertRaises(g.Refused):
                        g.arm('success', proof, agent)
            for field, value in (('valid_through', '2000-01-01'), ('wire_sha256', '0'*64), ('model', 'other'),
                                 ('credential_id', '33fdf0'), ('profile', 'default'), ('all_in_krw_per_usd', 'NaN'),
                                 ('project', ''), ('synthetic', 1), ('purpose', 'title')):
                with self.subTest(field=field):
                    with self.assertRaises(g.Refused):
                        g.arm('success', dict(original, **{field: value}), agent)
            with self.assertRaises(g.Refused):
                g.loads('{"authorization_id":"one","authorization_id":"two"}')
        def test_recreated_gate_restart_unknown_refuses(self):
            # Earlier runtime-green process already reserved this immutable ID.
            gate = g.arm('success', g.catalog('success')['proof'], agent)
            before = gate._path.read_bytes()
            turn('success')
            self.assertEqual(captures, [])
            self.assertEqual(before, gate._path.read_bytes())
            self.assertIn('already reserved', g.EVENTS[-1]['reason'])
        def test_client_redirect_proxy_retry_stream_invariants(self):
            for kwargs in ({'follow_redirects': True}, {'proxy': 'http://synthetic.invalid'}, {'trust_env': True}):
                with self.subTest(kwargs=kwargs), self.assertRaises(g.Refused):
                    httpx.Client(**kwargs)
            for retries in (1, True, 0.0):
                with self.subTest(retries=retries), self.assertRaises(g.Refused):
                    httpx.HTTPTransport(retries=retries)
            client = httpx.Client()
            self.assertIs(client.follow_redirects, False)
            self.assertIs(client._trust_env, False)
            self.assertEqual(client._transport._pool._retries, 0)
            with self.assertRaises(g.Refused):
                client.send(httpx.Request('POST', g.URL), stream=True)
            client.close()
        def test_auxiliary_direct_recreated_client_refusal(self):
            from agent.gemini_native_adapter import GeminiNativeClient
            g.arm('success', g.catalog('success')['proof'], agent)
            for purpose in ('title', 'compression', 'auxiliary', 'fallback'):
                with self.subTest(purpose=purpose):
                    client = GeminiNativeClient(api_key=g.KEY)
                    with self.assertRaisesRegex(g.Refused, 'unapproved source'):
                        client.chat.completions.create(model='gemini-3.8-flash', messages=[{'role':'user','content':purpose}], max_tokens=4096)
                    client.close()
            self.assertEqual(captures, [])
        def test_final_wire_mutations_refused_on_actual_runtime(self):
            # Intercept only test mutation immediately before the real Client.send.
            old_send = httpx.Client.send
            mutations = [
                ('host', lambda r: setattr(r, 'url', httpx.URL('https://synthetic.invalid/v1beta/models/gemini-3.8-flash:generateContent'))),
                ('path', lambda r: setattr(r, 'url', httpx.URL(g.URL + '/other'))),
                ('key', lambda r: r.headers.__setitem__('x-goog-api-key', 'SYNTHETIC-FREE-33fdf0')),
                ('header', lambda r: r.headers.__setitem__('x-extra-billing', 'unapproved')),
            ]
            for key, value in (('tools', [{}]), ('cachedContent', 'synthetic'), ('store', True), ('contents', []),
                               ('grounding', {}), ('search', {}), ('continuationToken', 'synthetic')):
                def mutate(r, key=key, value=value):
                    obj = json.loads(r.content)
                    obj[key] = value
                    r._content = json.dumps(obj).encode()
                    r.stream = httpx.ByteStream(r._content)
                    r.headers['content-length'] = str(len(r.content))
                mutations.append((key, mutate))
            def candidate_mutation(r):
                obj = json.loads(r.content)
                obj['generationConfig']['candidateCount'] = 2
                r._content = json.dumps(obj).encode()
                r.stream = httpx.ByteStream(r._content)
                r.headers['content-length'] = str(len(r.content))
            mutations.append(('candidate2', candidate_mutation))
            for label, mutate in mutations:
                with self.subTest(mutation=label):
                    g.arm('success', g.catalog('success')['proof'], agent)
                    def altered(client, request, **kw):
                        mutate(request)
                        return old_send(client, request, **kw)
                    httpx.Client.send = altered
                    try:
                        turn('success')
                    finally:
                        httpx.Client.send = old_send
                    self.assertEqual(captures, [])
                    self.assertNotIn('already reserved', g.EVENTS[-1]['reason'])
        def test_environment_refresh_fake_key_refuses(self):
            # Unused 'refresh' authority: the refusal must come from the credential check, not from a spent ledger row.
            gate = g.arm('refresh', g.catalog('refresh')['proof'], agent)
            old = os.environ['GOOGLE_API_KEY']
            os.environ['GOOGLE_API_KEY'] = 'SYNTHETIC-FREE-33fdf0'
            try:
                turn('success')
            finally:
                os.environ['GOOGLE_API_KEY'] = old
            self.assertEqual(captures, [])
            self.assertEqual(g.EVENTS[-1]['reason'], 'credential environment refresh mismatch')
            self.assertFalse(gate._path.exists(), 'no reservation may be written for a refused request')
        def test_unknown_errors_and_empty_tool_each_no_second_send(self):
            for mode in ('timeout', '429', '500', 'empty', 'tool'):
                with self.subTest(mode=mode):
                    captures.clear()
                    gate = g.arm(mode, g.catalog(mode)['proof'], agent)
                    turn(mode)
                    self.assertEqual(len(captures), 1, mode)
                    before = gate._path.read_bytes()
                    turn(mode)
                    self.assertEqual(len(captures), 1, mode)
                    self.assertEqual(before, gate._path.read_bytes())
        def test_concurrent_native_runtime_dispatch_single_reservation(self):
            from agent.chat_completion_helpers import _dispatch_nonstreaming_api_request
            from agent.gemini_native_adapter import GeminiNativeClient
            fixtures.MODE = 'success'
            gate = g.arm('concurrent', g.catalog('concurrent')['proof'], agent)
            body = json.loads(bytes.fromhex(g.catalog('concurrent')['final_wire']['body_hex']))
            kwargs = {'model':'gemini-3.8-flash', 'messages':[
                {'role':'system','content':body['systemInstruction']['parts'][0]['text']},
                {'role':'user','content':body['contents'][0]['parts'][0]['text']}],
                'max_tokens':4096, 'extra_body':{'thinking_config':{'includeThoughts':False,'thinkingLevel':'low'}}}
            barrier = threading.Barrier(8)
            results = []
            def send():
                client = GeminiNativeClient(api_key=g.KEY)
                try:
                    barrier.wait()
                    _dispatch_nonstreaming_api_request(agent, copy.deepcopy(kwargs), make_client=lambda *a, **k:client)
                    results.append('sent')
                except g.Refused:
                    results.append('refused')
                finally:
                    client.close()
            threads = [threading.Thread(target=send) for _ in range(8)]
            for t in threads: t.start()
            for t in threads: t.join(20)
            self.assertFalse(any(t.is_alive() for t in threads))
            self.assertEqual(results.count('sent'), 1)
            self.assertEqual(results.count('refused'), 7)
            self.assertEqual(len(captures), 1)
            outcomes.append({'case':'concurrent', 'results':results, 'captures':copy.deepcopy(captures)})
    suite = (unittest.TestSuite([Negatives('test_missing_proof_disarms_previous_authority')])
             if os.environ['FIXTURE_LABEL'] == 'runtime-negative-red' else unittest.defaultTestLoader.loadTestsFromTestCase(Negatives))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    record = {'tests':result.testsRun, 'failures':len(result.failures), 'errors':len(result.errors),
              'raw':stream.getvalue(), 'outcomes':outcomes, 'guard_events':list(g.EVENTS[events_start:]),
              'actual_run_conversation':bool(outcomes), 'actual_existing_bot':'NOT_RUN', 'vendor_charge':'NOT_RUN',
              'additional_test_monkeypatches':['httpx.Client.send mutation wrapper per negative', 'GOOGLE_API_KEY synthetic replacement'],
              'concurrency_scope':'real native dispatch helper + Gemini builder and HTTPX clients, not concurrent full conversation loops'}
    (W / 'scratch' / (os.environ['FIXTURE_LABEL'] + '.json')).write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(stream.getvalue())
    return record
