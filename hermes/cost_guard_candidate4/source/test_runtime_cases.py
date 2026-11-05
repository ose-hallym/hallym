"""Actual AIAgent safety assertions. Source RED is expected to fail assertions."""
import json
import os
import traceback
import unittest
from pathlib import Path
import httpx

W = Path(os.environ['FIXTURE_ROOT'])
CAPTURES = []
MODE = 'success'

class FakeTransport:
    """Substitute only the final HTTPTransport I/O; serialization stays real."""
    def handle(self, transport, request):
        url = str(request.url)
        if url != 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent':
            raise RuntimeError('unapproved fake endpoint: ' + url)
        body = json.loads(request.content)
        CAPTURES.append({'method': request.method, 'url': url, 'headers': list(request.headers.multi_items()),
                         'body': body, 'wire_hex': request.content.hex(),
                         'httpcore_retries': transport._pool._retries,
                         'stack': traceback.format_stack()})
        candidate = {'content': {'role': 'model', 'parts': [{'text': 'SYNTHETIC_OK'}]}, 'finishReason': 'STOP', 'index': 0}
        if MODE == 'timeout':
            raise httpx.ReadTimeout('SYNTHETIC unknown consumption', request=request)
        if MODE in ('429', '500'):
            return httpx.Response(int(MODE), json={'error':{'message':'SYNTHETIC provider failure'}}, request=request)
        if MODE == 'empty':
            candidate['content']['parts'] = [{'text':''}]
        if MODE == 'tool':
            candidate['content']['parts'] = [{'functionCall':{'name':'SYNTHETIC_FORBIDDEN_TOOL','args':{}}}]
        if MODE == 'continuation' and len(CAPTURES) == 1:
            candidate.update(finishReason='CONTINUATION', continuationToken='SYNTHETIC_CONTINUATION_ONLY')
        return httpx.Response(200, json={'candidates': [candidate], 'usageMetadata': {
            'promptTokenCount': 10, 'candidatesTokenCount': 4, 'totalTokenCount': 14}}, request=request)

def run(agent, integration=None):
    global MODE
    import io
    import threading
    fake = FakeTransport()
    events_start = len(integration.EVENTS) if integration is not None else 0
    original = httpx.HTTPTransport.handle_request
    if integration is None:
        httpx.HTTPTransport.handle_request = lambda self, request: fake.handle(self, request)
    trace = __import__('sys').gettrace()
    threading.settrace(trace)
    outcomes = []
    class Cases(unittest.TestCase):
        def setUp(self):
            CAPTURES.clear()
            self.assertEqual(agent.tools, [], 'constructor did not enforce no tools')
            if integration is not None:
                name = {'test_continuation_one_post': 'continuation', 'test_success_real_runtime': 'success',
                        'test_thinking_cap': 'thinking'}[self._testMethodName]
                integration.arm(name, integration.catalog(name)['proof'], agent)
        def test_success_real_runtime(self):
            global MODE
            MODE = 'success'
            agent.reasoning_config = {'enabled': False}
            response = agent.run_conversation('Return SYNTHETIC_OK only.', system_message='Synthetic public source packet. No tools. No private data.')
            outcomes.append({'case': self.id(), 'response': response, 'captures': list(CAPTURES)})
            self.assertEqual(len(CAPTURES), 1)
            self.assertIn('SYNTHETIC_OK', str(response))
        def test_thinking_cap(self):
            global MODE
            MODE = 'success'
            agent.reasoning_config = {'enabled': True, 'effort': 'high'}
            response = agent.run_conversation('Return SYNTHETIC_OK only.', system_message='Synthetic public source packet. No tools. No private data.')
            outcomes.append({'case': self.id(), 'response': response, 'captures': list(CAPTURES)})
            self.assertEqual(len(CAPTURES), 1)
            self.assertLessEqual(CAPTURES[0]['body']['generationConfig']['maxOutputTokens'], 4096)
        def test_continuation_one_post(self):
            global MODE
            MODE = 'continuation'
            agent.reasoning_config = {'enabled': False}
            response = agent.run_conversation('Return SYNTHETIC_OK only.', system_message='Synthetic public source packet. No tools. No private data.')
            outcomes.append({'case': self.id(), 'response': response, 'captures': list(CAPTURES)})
            self.assertEqual(len(CAPTURES), 1)
    stream = io.StringIO()
    try:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    finally:
        if integration is None:
            httpx.HTTPTransport.handle_request = original
        threading.settrace(None)
    record = {'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'raw': stream.getvalue(), 'outcomes': outcomes,
              'runtime_monkeypatches': ['httpx.HTTPTransport.handle_request final I/O => synthetic response', 'socket.gethostname => synthetic host'],
              'actual_run_conversation': bool(outcomes), 'actual_existing_bot': 'NOT_RUN', 'vendor_charge': 'NOT_RUN'}
    if integration is not None:
        record['guard_events'] = list(integration.EVENTS[events_start:])
        record['runtime_monkeypatches'] += ['httpx.Client.__init__', 'httpx.HTTPTransport.__init__',
                                           'httpx.Client.send', 'httpx.AsyncClient.send',
                                           'global gated httpx.HTTPTransport.handle_request']
    (W / 'scratch' / (os.environ['FIXTURE_LABEL'] + '.json')).write_text(json.dumps(record, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    print(stream.getvalue())
    return record
