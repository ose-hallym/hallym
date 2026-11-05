"""Single offline integration candidate. NO LIVE TRANSPORT OR LAUNCH ENTRY.
The only accepted authorities are a finite, hash-pinned synthetic fixture catalog.
Existing bot credentials, project proof and the real cost authorization are never accepted.

Candidate4 (user-directed revision of candidate3, 2026-11-05): shared cap policy with thinkingBudget clamp,
namespace cumulative KRW ledger, exact built-in transport only (no `_inner` wrapper), global install marker,
positional transport arguments refused, and a wait-for-complete ledger row reader for cross-process tests.
"""
import os
import sys
import json
import time
import hashlib
import threading
import stat
from datetime import date
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
import httpx

import trusted_bootstrap
from cap_policy import apply_cap, MAX_OUTPUT_TOKENS, CANDIDATE_COUNT
_CONTEXT = trusted_bootstrap.current()
LEDGER = Path(_CONTEXT['ledger'])
PROFILE_HOME = Path(_CONTEXT['profile_home'])
if type(_CONTEXT.get('namespace_max_krw')) is not int or _CONTEXT['namespace_max_krw'] <= 0:
    raise RuntimeError('trusted context lacks a positive integer namespace_max_krw')
NAMESPACE_MAX_KRW = _CONTEXT['namespace_max_krw']
KEY = 'SYNTHETIC-ONLY-2108ae-NOT-A-REAL-KEY'
URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent'
LOCK = threading.RLock()
ACTIVE = None
EVENTS = []
INSTALLED = False

class Refused(RuntimeError):
    pass

def reject(reason):
    EVENTS.append({'decision': 'REFUSE', 'reason': reason})
    raise Refused(reason)

def unique_pairs(items):
    result = {}
    for k, v in items:
        if k in result:
            reject('duplicate JSON key')
        result[k] = v
    return result

def loads(raw):
    return json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=lambda x: reject('nonfinite JSON'))

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

_CATALOG_BYTES = canonical(_CONTEXT['cases'])

def catalog(name):
    value = loads(_CATALOG_BYTES).get(name)
    if value is None:
        reject('unknown immutable synthetic authorization')
    return value

def shape(path):
    for node in [path, *path.parents]:
        try:
            st = node.lstat()
        except FileNotFoundError:
            continue
        if getattr(st, 'st_file_attributes', 0) & 0x400:
            reject('reparse ledger ancestor')
        if stat.S_ISREG(st.st_mode) and st.st_nlink != 1:
            reject('hardlinked ledger')

def wire(request):
    return {'method': request.method, 'url': str(request.url),
            'headers': sorted(request.headers.multi_items()), 'body_hex': request.content.hex()}

def digest(request):
    return hashlib.sha256(canonical(wire(request))).hexdigest()

def cumulative_krw(unreadable_row_krw):
    """Sum synthetic_krw over every reservation row of this namespace ledger.

    Unreadable or partially written rows count at the per-authority maximum (fail closed). Cross-process
    admission is serialized only by the exclusive row create, so two processes may each pass this check
    once; the overshoot is bounded by one row per concurrently admitted process and never refunded.
    """
    total = Decimal(0)
    if not LEDGER.is_dir():
        return total
    for p in LEDGER.iterdir():
        if not (p.is_file() and p.suffix == '.json' and len(p.stem) == 64):
            continue
        try:
            total += Decimal(str(json.loads(p.read_bytes())['synthetic_krw']))
        except Exception:
            total += Decimal(unreadable_row_krw)
    return total

def read_ledger_row(path, wait=2.0):
    """Read a reservation row that another process may still be writing.

    The exclusive create precedes the write, so a 0-byte file is a legitimate transient state rather than
    corruption; wait briefly for complete JSON. The gate itself never depends on row content.
    """
    deadline = time.monotonic() + wait
    while True:
        raw = path.read_bytes()
        if raw:
            try:
                return loads(raw)
            except ValueError:
                pass
        if time.monotonic() >= deadline:
            raise RuntimeError('ledger row incomplete after wait: ' + str(path))
        time.sleep(0.01)

class Gate:
    def __setattr__(self, name, value):
        if getattr(self, '_sealed', False):
            reject('immutable authorization gate: ' + name)
        object.__setattr__(self, name, value)

    def __init__(self, name, proof, agent):
        frozen = catalog(name)
        if proof is None or type(proof) is not dict:
            reject('missing validated budget proof')
        for k in ('input_upper', 'output_plus_thinking_upper', 'candidates', 'max_requests', 'max_krw'):
            if type(proof.get(k)) is not int:
                reject('authority integer type: ' + k)
        if proof.get('namespace') != _CONTEXT['namespace']:
            reject('authority namespace mismatch')
        if proof.get('synthetic') is not True:
            reject('live entry disabled')
        if canonical(proof) != canonical(frozen['proof']):
            reject('proof does not equal frozen validated synthetic authority')
        if not date.fromisoformat(proof['valid_from']) <= date.today() <= date.fromisoformat(proof['valid_through']):
            reject('stale proof')
        if (proof['input_upper'], proof['output_plus_thinking_upper'], proof['candidates'], proof['max_requests']) != (16384, MAX_OUTPUT_TOKENS, CANDIDATE_COUNT, 1):
            reject('immutable policy limits')
        usd = (Decimal(proof['input_upper']) * Decimal(proof['input_usd_million']) +
               Decimal(proof['output_plus_thinking_upper']) * Decimal(proof['output_usd_million'])) / Decimal(1000000)
        krw = (usd * Decimal(proof['all_in_krw_per_usd'])).to_integral_value(rounding=ROUND_CEILING)
        if krw > proof['max_krw']:
            reject('budget exceeded')
        self._name, self._agent = name, agent
        self._authority = frozen['authorization_id']
        self._record = canonical(frozen)
        self.conditional_usd, self.synthetic_krw = str(usd), str(krw)
        self._max_krw = proof['max_krw']
        # No path argument, environment override or fresh filename can replenish this ID.
        self._path = LEDGER / (hashlib.sha256(self._authority.encode()).hexdigest() + '.json')
        self._sealed = True

    def verify_source(self):
        module = sys.modules.get('agent.chat_completion_helpers')
        code = getattr(getattr(module, '_dispatch_nonstreaming_api_request', None), '__code__', None)
        frame = sys._getframe()
        matched = False
        while frame:
            if code is not None and frame.f_code is code and frame.f_locals.get('agent') is self._agent:
                matched = True
            frame = frame.f_back
        if not matched:
            reject('unapproved source / auxiliary or direct client')
        if self._agent.provider != 'gemini' or self._agent.model != 'gemini-3.8-flash' or self._agent.tools:
            reject('agent provider model tools changed')
        if os.environ.get('HERMES_PROFILE') != 'refomax' or Path(os.environ['HERMES_HOME']).resolve() != PROFILE_HOME:
            reject('profile mismatch')
        if os.environ.get('GOOGLE_API_KEY') != KEY:
            reject('credential environment refresh mismatch')

    def prepare(self, request):
        self.verify_source()
        if request.method != 'POST' or str(request.url) != URL or request.headers.get('x-goog-api-key') != KEY:
            reject('unapproved method host path model key')
        if len(request.content) > 65536:
            reject('wire bytes ceiling (not token proof)')
        rec = loads(self._record)
        if not date.fromisoformat(rec['proof']['valid_from']) <= date.today() <= date.fromisoformat(rec['proof']['valid_through']):
            reject('stale proof at final outgoing boundary')
        if digest(request) != rec['raw_wire_sha256']:
            reject('raw final-built wire differs from frozen packet')
        obj = loads(request.content)
        if set(obj) != {'contents', 'systemInstruction', 'generationConfig'}:
            reject('tools cache storage search continuation or extra fields')
        cfg = obj['generationConfig']
        if type(cfg.get('maxOutputTokens')) is not int:
            reject('cap exact integer')
        EVENTS.append({'decision': 'ORIGINAL_BUILDER_OBSERVED', 'maxOutputTokens': cfg['maxOutputTokens'], 'thinkingConfig': cfg.get('thinkingConfig'), 'raw_wire_sha256': digest(request), 'actual_raw_wire': wire(request)})
        # After the actual Gemini builder; the shared approved cap transformation is the only mutation.
        apply_cap(obj, reject)
        body = json.dumps(obj, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
        request._content = body
        request.stream = httpx.ByteStream(body)
        request.headers['content-length'] = str(len(body))
        if digest(request) != rec['proof']['wire_sha256']:
            reject('final wire hash / complete token proof mismatch')
        EVENTS.append({'decision': 'FINAL_WIRE_VALIDATED', 'catalog_sha256': _CONTEXT['catalog_sha256'],
                       'raw_wire_sha256': rec['raw_wire_sha256'], 'wire_sha256': digest(request),
                       'actual_final_wire': wire(request), 'authority': self._authority})
        return request

    def reserve(self, request):
        with LOCK:
            shape(LEDGER)
            LEDGER.mkdir(parents=True, exist_ok=True)
            shape(self._path)
            if cumulative_krw(self._max_krw) + Decimal(self.synthetic_krw) > Decimal(NAMESPACE_MAX_KRW):
                reject('namespace cumulative budget exceeded')
            row = {'authorization_id': self._authority, 'state': 'RESERVED_CONSUMPTION_UNKNOWN',
                   'wire_sha256': digest(request), 'synthetic_only': True,
                   'conditional_usd': self.conditional_usd, 'synthetic_krw': self.synthetic_krw,
                   'refund_allowed': False}
            try:
                with self._path.open('xb') as f:
                    f.write(canonical(row))
                    f.flush()
                    os.fsync(f.fileno())
            except FileExistsError:
                reject('authorization already reserved or unknown consumption')
            # Reservation remains unchanged on response, timeout, 429, 5xx or parsing failure.
            EVENTS.append({'decision': 'RESERVED_BEFORE_FAKE_SEND', 'authorization_id': self._authority,
                           'wire_sha256': row['wire_sha256']})

def arm(name, proof, agent):
    global ACTIVE
    with LOCK:
        ACTIVE = None
        ACTIVE = Gate(name, proof, agent)
        return ACTIVE

def install(fake_handler):
    global INSTALLED
    # The module flag alone is per-module: a byte-identical relocated copy has its own. Mark the httpx objects.
    if INSTALLED or getattr(httpx.HTTPTransport.handle_request, '_cost_guard_installed', False) or getattr(httpx.Client.send, '_cost_guard_installed', False):
        reject('global transport already installed')
    INSTALLED = True
    original_client_init = httpx.Client.__init__
    original_async_init = httpx.AsyncClient.__init__
    original_send = httpx.Client.send
    original_build_auth = httpx.Client._build_auth
    original_request_auth = httpx.Client._build_request_auth
    original_build_request = httpx.Client.build_request
    original_transport_init = httpx.HTTPTransport.__init__
    from httpx._client import USE_CLIENT_DEFAULT
    def no_auth(value, allow_default=False):
        if value is not None and not (allow_default and value is USE_CLIENT_DEFAULT):
            reject('auth forbidden before invocation')
    def build_auth(self, auth):
        no_auth(auth)
        return original_build_auth(self, None)
    def request_auth(self, request, auth=USE_CLIENT_DEFAULT):
        no_auth(auth, True)
        if self._auth is not None:
            reject('auth forbidden before invocation')
        if request.url.username or request.url.password:
            reject('auth forbidden before invocation')
        return original_request_auth(self, request, auth)
    def build_request(self, *args, **kwargs):
        if 'auth' in kwargs:
            no_auth(kwargs.pop('auth'))
        if getattr(self, '_auth', None) is not None:
            reject('auth forbidden before invocation')
        return original_build_request(self, *args, **kwargs)
    def async_init(self, *args, **kwargs):
        no_auth(kwargs.get('auth'))
        if any((kwargs.get('event_hooks') or {}).values()):
            reject('event hooks forbidden before invocation')
        original_async_init(self, *args, **kwargs)
    def client_init(self, *args, **kwargs):
        no_auth(kwargs.get('auth'))
        if any((kwargs.get('event_hooks') or {}).values()):
            reject('event hooks forbidden before invocation')
        if kwargs.get('follow_redirects', False) is not False or kwargs.get('proxy') is not None:
            reject('redirects or proxy requested')
        if kwargs.get('trust_env', False) is not False:
            reject('environment proxy routing requested')
        kwargs.update(follow_redirects=False, trust_env=False)
        original_client_init(self, *args, **kwargs)
    def transport_init(self, *args, **kwargs):
        if args:
            reject('positional transport arguments')
        if type(kwargs.get('retries', 0)) is not int or kwargs.get('retries', 0) != 0 or kwargs.get('proxy') is not None:
            reject('transport retry or proxy requested')
        kwargs.update(retries=0, trust_env=False)
        original_transport_init(self, *args, **kwargs)
    def send(self, request, **kwargs):
        no_auth(kwargs.get('auth', USE_CLIENT_DEFAULT), True)
        if self._auth is not None:
            reject('auth forbidden before invocation')
        if any(self.event_hooks.values()):
            reject('event hooks forbidden before invocation')
        if self.follow_redirects is not False or self._trust_env is not False or kwargs.get('follow_redirects') is True or kwargs.get('stream', False) is not False:
            reject('underlying client redirect proxy streaming invariant')
        # Only the exact built-in transport whose class-level handle_request is this gate may dispatch.
        # Candidate3 admitted any wrapper exposing `_inner`; httpx calls the wrapper's own handle_request,
        # so a non-delegating wrapper bypassed prepare/reserve entirely.
        for transport in [self._transport, *(self._mounts or {}).values()]:
            if transport is None:
                continue
            if (type(transport) is not httpx.HTTPTransport or 'handle_request' in vars(transport)
                    or type(transport).handle_request is not handle or transport._pool._retries != 0):
                reject('custom transport, wrapper or retry pool')
        return original_send(self, request, **kwargs)
    def handle(transport, request):
        if transport._pool._retries != 0:
            reject('nonzero underlying retries')
        with LOCK:
            gate = ACTIVE
            if gate is None:
                reject('missing budget proof / unarmed global gate')
            gate.prepare(request)
            gate.reserve(request)
        return fake_handler(transport, request)
    async def async_send(*args, **kwargs):
        reject('async clients forbidden')
    httpx.Client.__init__ = client_init
    httpx.AsyncClient.__init__ = async_init
    httpx.Client._build_auth = build_auth
    httpx.Client._build_request_auth = request_auth
    httpx.Client.build_request = build_request
    httpx.HTTPTransport.__init__ = transport_init
    handle._cost_guard_installed = True
    send._cost_guard_installed = True
    httpx.Client.send = send
    httpx.HTTPTransport.handle_request = handle
    httpx.AsyncClient.send = async_send
