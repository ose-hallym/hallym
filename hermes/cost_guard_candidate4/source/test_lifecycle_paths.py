"""Final source-path checks: restart/unknown, real fallback primitive, real auxiliary API."""
import json
import os
import io
import unittest
from pathlib import Path

W = Path(os.environ['FIXTURE_ROOT'])

def run(agent, g, fake):
    notes = []
    events_start = len(g.EVENTS)
    class Lifecycle(unittest.TestCase):
        def setUp(self):
            fake.CAPTURES.clear()
            fake.MODE = 'success'
            agent.reasoning_config = {'enabled':False}
        def turn(self):
            return agent.run_conversation('Return SYNTHETIC_OK only.', system_message='Synthetic public source packet. No tools. No private data.')
        def test_immutable_gate_cannot_choose_new_ledger_path(self):
            gate = g.arm('success', g.catalog('success')['proof'], agent)
            with self.assertRaises(g.Refused):
                gate._path = W / 'scratch' / 'attempted-new-ledger.json'
        def test_expired_armed_proof_rechecked_at_send(self):
            g.arm('success', g.catalog('success')['proof'], agent)
            original = g.date
            class SyntheticFutureDate(original):
                @classmethod
                def today(cls):
                    return cls(2100, 1, 1)
            g.date = SyntheticFutureDate
            try:
                response = self.turn()
            finally:
                g.date = original
            self.assertEqual(fake.CAPTURES, [])
            self.assertIn('stale proof', g.EVENTS[-1]['reason'])
            notes.append({'case':'synthetic-future-expiry', 'response':response})
        def test_unknown_reservations_survive_cold_process(self):
            for name in ('timeout','429','500','empty','tool','concurrent'):
                with self.subTest(authorization=name):
                    gate = g.arm(name, g.catalog(name)['proof'], agent)
                    before = gate._path.read_bytes()
                    result = self.turn()
                    self.assertEqual(fake.CAPTURES, [])
                    self.assertEqual(before, gate._path.read_bytes())
                    self.assertIn('already reserved', g.EVENTS[-1]['reason'])
                    notes.append({'case':'cold-unknown-' + name, 'response': result})
        def test_real_fallback_client_swap_cannot_send(self):
            from agent.client_lifecycle import _swap_fallback_clients
            from agent.gemini_native_adapter import GeminiNativeClient
            # Unapproved key on the unused 'fallback' authority: the refusal must be the key/wire check, with no ledger row.
            gate = g.arm('fallback', g.catalog('fallback')['proof'], agent)
            _swap_fallback_clients(agent, GeminiNativeClient(api_key='SYNTHETIC-FREE-33fdf0'), 'gemini', 'gemini-3.8-flash',
                                   'https://generativelanguage.googleapis.com/v1beta', 'chat_completions')
            result = self.turn()
            self.assertEqual(fake.CAPTURES, [])
            self.assertEqual(g.EVENTS[-1]['reason'], 'unapproved method host path model key')
            self.assertFalse(gate._path.exists())
            notes.append({'case':'actual-fallback-primitive', 'key_is_approved_fake':False, 'response':result})
            # Approved key on the spent 'success' authority proves only the ledger block, and is labelled as such.
            g.arm('success', g.catalog('success')['proof'], agent)
            _swap_fallback_clients(agent, GeminiNativeClient(api_key=g.KEY), 'gemini', 'gemini-3.8-flash',
                                   'https://generativelanguage.googleapis.com/v1beta', 'chat_completions')
            result = self.turn()
            self.assertEqual(fake.CAPTURES, [])
            self.assertIn('already reserved', g.EVENTS[-1]['reason'])
            notes.append({'case':'actual-fallback-primitive', 'key_is_approved_fake':True, 'evidence':'ledger block only', 'response':result})
            # Restore only the synthetic fixture, never a real route.
            _swap_fallback_clients(agent, GeminiNativeClient(api_key=g.KEY), 'gemini', 'gemini-3.8-flash',
                                   'https://generativelanguage.googleapis.com/v1beta', 'chat_completions')
        def test_real_auxiliary_call_api_cannot_send(self):
            from agent.auxiliary_client import call_llm
            g.arm('success', g.catalog('success')['proof'], agent)
            for task in ('title_generation', 'compression'):
                with self.subTest(task=task):
                    before = len(g.EVENTS)
                    error = None
                    try:
                        call_llm(task=task, provider='gemini', model='gemini-3.8-flash',
                                 base_url='https://generativelanguage.googleapis.com/v1beta', api_key=g.KEY,
                                 messages=[{'role':'user','content':'Synthetic forbidden auxiliary request'}],
                                 max_tokens=4096, reasoning_config={'enabled':False}, timeout=1.0, stream=False)
                    except Exception as exc:
                        error = str(exc)
                    self.assertEqual(fake.CAPTURES, [])
                    reached = g.EVENTS[before:]
                    self.assertTrue(any(e.get('decision')=='REFUSE' for e in reached),
                                    'auxiliary must actually reach boundary, not fail setup')
                    notes.append({'case':'actual-call_llm-' + task, 'error':error, 'guard_events':reached})
    output = io.StringIO()
    suite = (unittest.TestSuite([Lifecycle('test_immutable_gate_cannot_choose_new_ledger_path'),
                                Lifecycle('test_expired_armed_proof_rechecked_at_send')])
             if os.environ['FIXTURE_LABEL'].startswith('runtime-final-') else unittest.defaultTestLoader.loadTestsFromTestCase(Lifecycle))
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    record = {'tests':result.testsRun, 'failures':len(result.failures), 'errors':len(result.errors),
              'raw':output.getvalue(), 'outcomes':notes, 'guard_events':list(g.EVENTS[events_start:]),
              'actual_run_conversation': True, 'actual_existing_bot':'NOT_RUN', 'vendor_charge':'NOT_RUN',
              'limits':['fallback swap primitive exercised, not provider-selection automatic fallback chain',
                        'real auxiliary call_llm task entry exercised, not full title background thread or context compression lifecycle']}
    (W/'scratch'/(os.environ['FIXTURE_LABEL']+'.json')).write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(output.getvalue())
    return record
