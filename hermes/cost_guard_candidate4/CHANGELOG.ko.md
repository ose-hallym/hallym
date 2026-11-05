# 후보4 변경 이력 — 후보3 → 후보4

- 작성일: 2026-11-05
- 근거: 사용자 지시("검증 및 수정 후 ZIP으로 이메일 전달"). 후보3은 3/max3로 봉인되어 있었고 자동 4차 수정은 금지되어 있었으므로, 이 변경은 **사용자가 지시한 후보4**이지 자동 수정이 아니다.
- 기준 후보3 엔진 SHA256: `de14ec8e4f4178892b687e96dcf6266503657653e9cd4c20295d7c83f2933bac`
- 변경 전체 diff: `patches/candidate3-to-candidate4.diff` (소스 9개 파일, 177행 추가 / 29행 삭제, 줄끝은 원본과 동일하게 유지)
- 검토 근거 문서: `docs/CODE-REVIEW-candidate3-2026-11-05.ko.md` (발견 번호 H1~H5, M1~M6, L)

## 1. 변경 목록

| 발견 | 파일 | 변경 내용 |
|---|---|---|
| H3, M3 | `source/cap_policy.py` (신규) | 승인 cap 변환을 한 함수로 통합. `maxOutputTokens`는 `min(값, 4096)`(덮어쓰기 아님), `candidateCount=1`, `thinkingConfig`는 허용 키(`includeThoughts`, `thinkingBudget`, `thinkingLevel`)만, `thinkingBudget`는 음수(동적)·초과 시 4096으로 고정. `reject`는 반드시 예외를 던져야 한다. |
| H3, M3 | `source/isolated_integration.py` `prepare()` | 인라인 cap 코드를 `apply_cap(obj, reject)` 호출로 교체. `ORIGINAL_BUILDER_OBSERVED` 이벤트에 `thinkingConfig` 기록 추가. |
| H3, M3 | `source/trusted_bootstrap.py` | 동결 패킷 생성도 동일한 `apply_cap`을 사용. 양쪽이 같은 함수를 쓰므로 final wire 해시가 어긋날 수 없다. |
| H2 | `source/isolated_integration.py` `cumulative_krw()`, `reserve()` | 네임스페이스 원장의 모든 행 `synthetic_krw` 합산. 읽을 수 없는 행은 권한 최대값(56)으로 계산(fail closed). `reserve()`가 배타적 생성 **전에** `합계 + 이번 금액 > NAMESPACE_MAX_KRW`이면 `namespace cumulative budget exceeded`로 거부. |
| H2 | `source/trusted_inputs.py`, `source/trusted_bootstrap.py` | `NAMESPACE_MAX_KRW=1000`(승인된 실제 허용액과 동일). catalog 스키마 `trusted-synthetic-context-v4`, `namespace_max_krw` 필드 추가. 엔진은 이 필드가 양의 정수가 아니면 import 자체를 거부한다. |
| H4 | `source/isolated_integration.py` `send()` | `_inner` 래퍼 허용 제거. transport는 정확히 `httpx.HTTPTransport` 타입이고, 인스턴스 속성으로 `handle_request`를 덮어쓰지 않았으며, 클래스의 `handle_request`가 이 게이트의 `handle`이어야 한다. |
| M2 | `source/isolated_integration.py` `install()` | `httpx.HTTPTransport.handle_request`·`httpx.Client.send`에 `_cost_guard_installed` 마커를 붙이고 재설치 시 확인. 바이트 동일 복사본의 `install()`도 `global transport already installed`로 거부. |
| L | `source/isolated_integration.py` `transport_init()` | 위치 인자가 하나라도 있으면 `positional transport arguments`로 거부(이전에는 `retries`를 위치 인자로 주면 kwargs 검사를 지나 `TypeError`로 우연히 막혔음). |
| M1 | `source/isolated_integration.py` `read_ledger_row()` | 배타적 생성 직후 0바이트 상태를 정상 과도 상태로 보고 최대 2초간 완전한 JSON을 기다리는 reader. 게이트 판단은 행 내용에 의존하지 않으므로 생성 primitive(`open('xb')`)는 바꾸지 않았다(싱글링크 정책과 충돌하는 하드링크 방식 회피). |
| M1 | `source/suite_v3.py` ProcessRace | 패배 프로세스가 `json.loads(read_bytes())` 대신 `g.read_ledger_row()`를 사용. |
| M4 | `source/test_gate_negatives.py` | 환경 키 교체 테스트를 미사용 `refresh` 권한으로 옮기고 거부 사유 `credential environment refresh mismatch`와 원장 행 부재를 단언. |
| M4 | `source/test_lifecycle_paths.py` | fallback 스왑 테스트를 둘로 분리. 비승인 키는 미사용 `fallback` 권한에서 `unapproved method host path model key`와 원장 부재를 단언. 승인 키는 소진된 `success` 권한에서 `already reserved`를 단언하고 "원장 차단만 증명"으로 명시. |
| M4 | `test_gate_negatives.py`, `test_lifecycle_paths.py`, `test_runtime_cases.py` | `guard_events`를 `g.EVENTS` 별칭 대신 그룹 시작 시점부터의 슬라이스로 저장. |
| H2, H4, M2, H3 | `source/suite_v3.py` Contracts | 신규 테스트 4개: 복사본 재설치 거부, 래퍼/인스턴스 덮어쓰기/위치 인자 거부, 누적 예산 거부(원장 행 미생성 확인), `cap_policy` 단위 검사. |
| M5 | `source/trusted_inputs.py` | `VALID_FROM`, `VALID_THROUGH`를 상수로 분리(값은 2026-11-01 ~ 2026-12-31 그대로. 기간 연장은 정책 결정이라 바꾸지 않음). |
| L | `source/trusted_bootstrap.py` | `bind(namespace, agent=None)`에서 agent가 없으면 `trusted agent required` RuntimeError. |
| L | `source/run_offline.py` | 런타임 자식 프로세스 cwd를 실제 사용자 홈(`C:/Users/HERMEZ`)에서 픽스처 홈으로 변경. 영수증의 `cwd`도 동일. |
| L | `source/suite_v3.py` | docstring "candidate2" → "candidate4". |

테스트 수: full-final 28 → **32**(Contracts 11 → 15). fake 전송 수는 10회로 변동 없음(신규·이동 테스트는 모두 거부 경로). cold-spent 대상 9개 권한도 그대로.

## 2. 변경하지 않은 것

- **H1 승인 모델**: 전체 wire 바이트 일치 요구는 그대로다. 이는 "검토용 재생 오라클"을 "운영용 구조 정책 + 누적 원장"으로 바꾸는 아키텍처 결정이며 사용자 승인 없이 바꾸지 않았다. 제안: `prepare()`의 130~144행 구조 검사(엔드포인트·키 헤더·필드 집합)와 `apply_cap`, `cumulative_krw`를 운영 정책 계층으로 분리하고, raw-hash 비교는 테스트 모드 플래그 뒤로 옮긴다.
- `runtime_fixture.py`, `red_fixture.py`, `assemble_red.py`, `assemble_runtime.py`, `prepare.py`, `freeze_and_accept.py`: 미변경. 생성기 산출물과 봉인 절차를 그대로 유지했다.
- `docs/`, `evidence/`의 후보3 기록: 미변경. 후보3의 검증 결과이며 후보4 결과가 아니다.
- 유효기간 값, 정책 상한(16384 / 4096 / 1 / 56 KRW): 미변경.

## 3. 긍정 경로에 영향을 줄 수 있는 변경 (Hermes 환경에서 먼저 확인할 것)

1. **`_inner` 래퍼 허용 제거(H4)**: Hermes 클라이언트의 transport가 정확히 `httpx.HTTPTransport`가 아니면 positive 테스트가 fail-closed로 실패한다. 확인: `type(agent.client._http._transport) is httpx.HTTPTransport`. 래퍼가 필요하다면 래퍼 쪽을 고쳐야지 게이트의 예외를 되살리면 안 된다.
2. **catalog 스키마 v4**: 기존 `FROZEN-CATALOG.json`(v3)과 바이트가 달라 `context catalog mismatch; no recapture/rewrite/refill`로 bind가 거부된다. 새 phase 디렉터리(새 root·namespace)에서 실행해야 한다. 기존 원장을 리셋·복사하지 않는 정책과 일치한다.
3. **거부 사유 단언 추가(M4)**: Hermes의 재시도·복구 흐름이 마지막 이벤트를 다른 사유로 덮어쓰면 실패할 수 있다. 실패 시 `guard_events` 슬라이스를 보면 원인이 바로 보인다.
4. **thinkingBudget 클램프(H3)**: 빌더가 `thinkingBudget`을 내보내면 'thinking' 패킷의 final wire 해시가 후보3과 달라진다. 동결·검증 양쪽이 같은 함수를 쓰므로 자기 일관성은 유지된다.
5. **`prepare.py`의 baseline 참조**는 후보2 시대(`runtime-integration2-C65F5EA0`, 해시 `18acc1d4…`) 그대로다. 후보4 사이클에서는 후보3 worker를 가리키도록 재설정해야 한다. 경로를 추측해 바꾸지 않았다.

## 4. 검증 상태

| 항목 | 결과 |
|---|---|
| `py_compile` (Python 3.13, 경고를 오류로 취급) | 15개 소스 전부 통과 |
| `selfcheck/selfcheck_candidate4.py` (httpx 0.28.1, 스텁 부트스트랩·에이전트, fake transport) | 11개 검사 전부 PASS. 긍정 통제, 중복 차단, `_inner` 래퍼·인스턴스 덮어쓰기·위치 인자·MockTransport 거부, min() cap, thinkingBudget 24576/-1 → 4096, 발급 측 unknown key 거부, 누적 예산 거부와 복구, 복사본 재설치 거부, 0바이트 행 관측과 `read_ledger_row` 대기·시간초과, agent 없는 bind 오류, `namespace_max_krw` 없는 컨텍스트 import 거부, 원장 행 내용 불변 |
| Hermes 연동 전체 스위트(`run_offline.py full-final / cold-spent / processraceA·B`) | **미실행**. `D:/Hermes/hermes-agent` 원본, Windows 경로, 지정 venv(Python 3.14)가 필요하다. 후보4는 Hermes 환경에서 검증되지 않았다. |
| 실제 모델 호출·과금·배포 | 없음. 코드 내 키는 `SYNTHETIC-ONLY-…` 상수뿐. |

## 5. Hermes 환경 실행 절차 (후보3 REPLAY.md 기준)

1. 새 phase 디렉터리에 `source/*.py` 15개를 복사한다(`cap_policy.py` 포함). `FINAL-PINS.json`은 넣지 않는다(`freeze_and_accept.py`가 생성).
2. `prepare.py`의 baseline 참조를 후보3 worker로 재설정한 뒤 실행한다.
3. 개발 실행(`run_offline.py positive-green DEVELOPMENT` 등)으로 3절 1·2·3항을 먼저 확인한다.
4. `freeze_and_accept.py`로 동결·수락 실행(full-final → cold-spent → processraceA·B).
5. 결과 `*-suite.json`, `COLD-PROCESS-RACE.json`, 신규 테스트 4개의 raw 로그를 보고 후보4 수락 여부를 사람이 결정한다.
