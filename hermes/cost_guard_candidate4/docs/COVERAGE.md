# Coverage — final pins only

`full-final` is 28/0/0; cold-spent1/0/0; cold-process race2/0/0. Raw GREEN is not mandatory-complete acceptance. Candidate accepted false.

| Criterion | Evidence / scope | Verdict |
|---|---|---|
| Constructor + run_conversation + native Gemini + HTTPX positive | Final actual full runtime, success SYNTHETIC_OK, one fake send | PASS |
| Context-correct expected request before arm | Fixed trusted content → original builders → build_request only; exclusive frozen catalog | PASS synthetic scope |
| Whole raw/capped wire | `POSITIVE-WIRE-PROVENANCE.json`, hashes and exact JSON/body bytes equal; HTTPX normalized header multivalue convention, not TCP/TLS framing/raw header casing | PASS stated convention |
| thinking65535→4096/candidate1 | Actual original builder event and final captures | PASS |
| Continuation | Initial send1, subsequent actual native continuation denied by full raw hash; final response intentionally failed | PASS no second send |
| timeout/429/500/empty/tool | One fake send each, unknown immutable reservation, second send denied | PASS at outgoing boundary |
| No retry attempts whatsoever | Runtime actually retries/rebuilds on timeout/empty; denied before fake I/O | NOT IMPLEMENTED; only no second transmission proven |
| Missing/exact integer types/all proof fields | Full immutable canonical proof comparison, missing-field/type/malformed mutations, duplicate JSON, synthetic date expiry | PASS tested fields |
| Full all-in real cost/token/project/FX proof | Only fixed synthetic metadata; input bound assumed for fixture, not vendor token count | ABSENT, live disabled |
| Key/header/body/tool/search/cache/store mutations | Valid full runtime control precedes negatives; expected method/key/raw-wire denial reasons checked | PASS tested requests |
| Arbitrary prompt self-authorization | Different runtime user prompt denied; frozen catalog and spent ledger unchanged | PASS |
| Genuine namespace-negative | Explicit other namespace chosen; assert inequality; old same-value raw failure preserved | PASS corrected contract |
| Rebind / real authorization ID / alternate home | Bootstrap bound once, unknown IDs refused, new home profile mismatch, immutable gate._path | PASS |
| Byte-identical relocation | Same source imported from alternate code file, same ledger path, spent refusal | PASS |
| Auth callbacks/flows pre-admission | Real baseline memory side-effect RED; final constructor/request/send/build/property/internal auth paths deny, effects0 | PASS |
| Event hooks | Constructor and appended request hook denied, effects0 | PASS |
| Bare no-auth built-in fakekey header | Actual main conversation positive with default HTTPX Auth path | PASS |
| Async/custom/recreated clients | Async send refused, custom handler not invoked, direct native auxiliary source refused | PASS tested seams |
| Non-Gemini | Actual native dispatcher with changed provider denied before send | PASS binding test, not every SDK/native transport |
| Helper thread concurrency | 8 threads call original native dispatcher; one send/seven refused | PASS helper scope; concurrent full conversations untested |
| Separate cold processes sameauthority | Two fixed-root cold runtimes, aggregate send1, identical ledger bytes | PASS |
| Cold spent rearm | All9 earlier authorities rearmed but cannot reserve/send; no ledger refill | PASS |
| Environment key refresh | Fake environment key replacement denied | PASS narrow substitution |
| Full credential refresh / automatic fallback | Actual client-swap primitive and calls only; not automatic credential/provider lifecycle | **INCOMPLETE** |
| Full title/compression lifecycle | Real auxiliary call_llm task API/direct clients, not title thread/full compressor lifecycle | **INCOMPLETE** |
| Audit before runtime import | Source-only mirror finder, synthetic profile, no sockets/processes allowed inside fixture | PASS audited paths |
| Startup/cleanup | Warnings and denied socket/DNS/open attempts retained, not counted as test passes | PRESERVED |
| Unsupported global/native/OS escape | Trusted Python control plane is a precondition; audit is not an OS sandbox | UNPROVEN |
| Protected3745 + added sources | Pre/post exact pins, old ledgers unchanged | PASS |

No code or test edits after final freeze. No automatic fourth candidate and no writer-dispatched review. Parent must not treat primitive coverage as completion of the mandatory lifecycle rows.
