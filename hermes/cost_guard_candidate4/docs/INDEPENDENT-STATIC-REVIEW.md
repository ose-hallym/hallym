# Independent final-SHA review notes

## Scope / disposition

Candidate `de14ec8e4f4178892b687e96dcf6266503657653e9cd4c20295d7c83f2933bac`, cumulative3/max3/no automatic4. No candidate source corrections, production config edits, new reviewer agents, authority issuance or ledger resets. Security and logic PASS only for the stated trusted-controller synthetic boundary; mandatory integration remains INCOMPLETE. Parent alone owns acceptance/freeze/next scope.

## Trust separation

- `trusted_inputs.py:3-12` fixes the namespace roots, user/system text, fake key/model and finite case names. `runtime_fixture.py:150-178` installs the audit hook before mirrored Hermes import, refuses all startup sends, constructs an actual full AIAgent with context/memory/tool restrictions, calls `trusted_bootstrap.bind`, and imports/arms the enforcement only afterward.
- `trusted_bootstrap.py:28-60` independently calls original system/API/native builders and HTTPX.build_request on fixed inputs. No transport capture or run_conversation output feeds issuance. Whole raw and capped method/URL/header multivalues/body bytes are frozen using exclusive create. A cold process requires exact catalog equality. This is trusted Python test issuance, not cryptographic authorization against a malicious controller.
- `isolated_integration.py:80-108,128-158` preserves exact integer checks (bool/float refused), whole proof equality, expiry at arm and send, raw wire equality, and complete capped wire equality. No generated-path/content-length stripping. Unknown/arbitrary prompt inputs cannot become approved merely by being observed. The independent full conversation positive and malicious-prompt negative reached the relevant wire checks; neither was credited from an unrelated profile refusal.
- `verify_source` uses actual dispatch code identity, the owning agent object and current call stack. Source hash pinning is supplied by the frozen launcher/review checks, not by a cryptographic mechanism inside this function. Arbitrary hostile Python monkeypatching, native extensions and OS all-egress isolation are outside the proven scope.

## Auth / hooks / reservation

- `install` rejects nonempty callable/Auth/tuple auth before constructor, property builder, build_request, send and request-auth execution. Per-request auth values and URL credentials are refused; request hooks are checked before HTTPX invokes them. Default no-auth key-header main runtime is a positive control.
- Complete wire verification precedes `reserve`; exclusive `xb` creation, flush and fsync precede fake transport invocation. A successful/error/timeout response does not refund or delete `RESERVED_CONSUMPTION_UNKNOWN`. New Gate instances and byte-identical relocated modules share the fixed authority path. Two cold processes produced exactly one fake send and identical ledger bytes. Locks/shape checks are not an adversarial-filesystem OS sandbox.
- Continuation, timeout,429,500,empty and tool responses do not yield a second fake send. Hermes retry/rebuild attempts still occur. This is not a no-retry-control-flow implementation.
- Thinking builder output65535 is capped to final4096/candidate1. Conditional input16384/output+thinking4096 assumptions and fake rate/FX metadata are not vendor token/project/cost proofs.

## Required lifecycle gaps and supplementary attempt

The frozen main fixture has `credential_pool=None` and `fallback_model={}`. Runtime traces include recovery/fallback entry functions, but no `_recover_auth_failure`, `_recover_rate_limit` or actual `_swap_credential` path. A function-entry trace that returns for no pool/chain does not close automatic rotation/fallback coverage. Existing environment substitution and `_swap_fallback_clients` primitive are retained as narrow tests; approved-key primitive uses an already spent authority. No new fake provider/credential chain or config mutation was improvised to call these complete.

Two new reviewer-only diagnostic entries ran the exact unchanged runtime fixture/engine/bootstrap, replacing only the suite-selection dependency and supplying an in-memory FakeSessionDB:

1. Original `maybe_auto_title -> auto_title_session` on a real thread -> `generate_title -> call_llm` reached `unapproved source / auxiliary or direct client`. Thread completed; only derived synthetic titles were stored in the fake DB. Zero fake send/reservation. This improves on a bare call_llm task label, but does not establish automatic title triggering from the main conversation or a complete successful auxiliary lifecycle.
2. Original `conversation_compression.compress_context(force=True) -> ContextCompressor.compress -> _generate_summary/_call_summary_llm` ran. HTTPX streaming-invariant refusal occurred before the deeper source/wire/ledger check. Deterministic fallback produced26 messages from30 synthetic messages. Zero fake send/reservation. Do not credit the masked deeper boundary or automatic pressure-trigger lifecycle as tested.

Supplementary execution imported12 original `.py` files absent from the authoritative pre-review protected5079 set (full list in `SUPPLEMENTARY-PROVENANCE-GAPS.json`). The unchanged MirrorLoader hashed their bytes before compile and postchecked them, but that is not pre-review pin provenance. No retroactive pre-pin claim or lifecycle completion is made. Mandatory full-final/cold/race imports have no such gap. Further lifecycle execution stopped.

## Assertion / evidence accounting

All14 copied FINAL-PINS sources and18 total copied input files were exact bytes. No source or assertion edit occurred in this review. The three business test modules are byte-identical to the preserved baseline. Writer suite_v2->v3 changes are disclosed in the retained diff: auth/prompt/non-Gemini and process-race additions; genuinely different namespace plus inequality assertion; cold-thinking request reconstruction. Existing assertions were not removed to obtain this review's green results.

Raw mandatory results: full-final28/0/0; cold-spent1/0/0; raceA1/0/0; raceB1/0/0. These are31 executions of30 unique test methods, not31 unique tests. Successful subtests are not enumerated by raw unittest logs;105 is a static loop expansion from completed unchanged methods, not an independently instrumented raw subtest count. Two entry diagnostics are separate, not additional passing unit tests. Never sum aliased guard-event arrays across group reports.

## Setup warnings / corrections to reviewer evidence tooling only

- A read-only display diagnostic exited1 because isolated Python ignored PYTHONIOENCODING and used cp949 for a Unicode em dash. No runtime test was rerun; later evidence printers explicitly reconfigure stdout UTF-8.
- Initial aggregation incorrectly compared `\\?\D:\...` and `D:\...` path spellings as distinct. The exact failed aggregator snapshot and complete terminal output are retained. `os.path.samefile` proved the alias; aggregation now compares actual `(st_dev,st_ino)` plus exact hash. No identifier, source pin or file was repaired.
- That correction exposed the genuine12 supplementary pre-pin gaps. The raw failed check remains in `scratch/analysis-final.err`. The final aggregator reports them INCOMPLETE instead of asserting all sources were pre-pinned. This is a report correction, not a candidate/test correction or hidden replay.
- Full-final80 audit denials, then52/52/52 in cold/races, and54 in entry diagnostics are retained. Unawaited coroutine and failed event-loop cleanup warnings remain raw in mandatory stderr. They are neither successful socket/private access nor unit-test failures silently erased.
- Read-only HTTPX `_client.py` was observed hardlink6 and hash `c43f941baefe58c91e96d00039e1868fe719d91453026d7db1647194563bff8d`; protected metadata exempts it from artifact singlelink enforcement. Worker/reviewer artifacts still require regular singlelink nonreparse shape.

## Boundary

No real model, private-content read, socket/network operation completion, payment, deployment or actual existing bot execution is claimed. `actualmodel=0`, `private_reads=0`, `spend=0`, `actualbot=NOT_RUN`, live=false. Real KRW1000 authority remains unconsumed. Python audit is not OS isolation. Missing external project/token/vendor FX proof prevents any real-bill claim. No fourth candidate or writer edit requested.
