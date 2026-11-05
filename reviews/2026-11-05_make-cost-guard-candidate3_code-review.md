# Make 비용 차단장치 후보3 — 코드 검토 결과

- 검토일: 2026-11-05
- 검토 대상 메일: `[Hermez-업무요약] Make 비용 차단장치 후보3 소스 ZIP·최종 검증보고서 — 통합 검증 미완료` (2026-11-05 02:31 UTC, 발신 스카이넷)
- 첨부: `Make_cost_guard_candidate3_SOURCE_REVIEW.zip` (56,796 bytes), `최종검증보고서.md` (4,720 bytes)
- 읽은 범위: ZIP 내 24개 파일 전부(소스 14, 문서 6, 증거 3, MANIFEST) 약 1,950행과 첨부 보고서. 전수 정독.

## 0. 결론

보고서의 자기평가 **"합성 환경 보안·논리 PASS / 전체 통합 INCOMPLETE / 운영 승인 아님"** 은 코드와 일치하며 과장이 없다. 테스트 수(28+1+2), fake 전송 수(10), 비용 산식(56 KRW), 비밀 미포함, 해시 무결성은 모두 재검증되었다.

다만 보고서가 말하지 않는 구조적 사실이 하나 있다. 이 게이트는 **사전에 바이트 단위로 동결한 요청만 통과시키는 재생(replay) 오라클**이다. 실제 대화는 매번 사용자 입력이 달라지므로 단 한 건도 통과할 수 없다. 남은 통합 항목(credential rotation, title/compression)보다 **승인 모델 자체**가 운영 전환의 핵심 과제이며, 이 점을 다음 단계(두 봇 교차검증) 전에 결정해야 한다.

운영 전환을 전제로 한다면 수정이 필요한 코드 결함은 H3(thinkingBudget 미통제), H4(`_inner` 래퍼 전송 우회), M1(원장 파일 비원자적 기록) 세 가지다. 후보3은 봉인(3/max3, 자동 4차 수정 없음) 상태이므로 수정 여부는 사람이 결정해야 한다.

## 1. 무결성·정적 검증 결과

| 항목 | 결과 |
|---|---|
| ZIP SHA256 (메일 명시 `792e532f…7d61`) | 일치 |
| MANIFEST.json 23개 멤버 집합·크기·SHA256 | 전부 일치, 누락·초과 없음 |
| evidence/FINAL-PINS.json 소스 14개 SHA256 | 전부 일치, 후보 SHA `de14ec8e…3bac` 일치 |
| README.ko.md == 첨부 최종검증보고서.md | 바이트 동일 (SHA `9d65666a…b9e9`) |
| py_compile (Python 3.13, 경고를 오류로 취급) | 14개 전부 통과 |
| 비밀·키 포함 여부 | 실제 키 없음. 코드 내 키는 `SYNTHETIC-ONLY-…` 상수뿐. 단, 경로에 Windows 사용자명(`C:/Users/HERMEZ`)이 노출됨 |

실행 검증은 하지 않았다. 이유: 스위트는 `D:/Hermes/hermes-agent` 원본 소스, Windows 경로, 지정 venv(Python 3.14)에 묶여 있어 이 환경에서 재현 불가. 또한 ZIP 코드를 직접 실행하는 작은 확인 하네스를 작성했으나 세션의 외부 코드 실행 권한 정책에 의해 차단되었다. 아래 발견은 모두 코드 정독으로 확정 가능한 수준이다.

## 2. 주요 발견 (심각도 순)

### H1. 승인 모델이 운영 트래픽에 일반화되지 않음 (설계)
- `source/isolated_integration.py:137` — `digest(request) != rec['raw_wire_sha256']` 이면 거부. 메서드·URL·전체 헤더·본문 16진수 전체의 해시가 동결 패킷과 같아야 한다.
- 동결 패킷은 `trusted_bootstrap.py:29-42`에서 고정 문구(`USER='Return SYNTHETIC_OK only.'`)로 생성된다. 사용자 입력이 바뀌면 본문이 바뀌고, 모든 요청이 `raw final-built wire differs from frozen packet` 으로 거부된다.
- 또한 `send()`(`isolated_integration.py:245`)는 `stream=True`를 전부 거부한다. Hermes 압축기가 스트리밍을 쓰기 때문에 compression 검증이 "앞선 streaming 차단에 걸렸다"는 보고서 문구가 여기서 나온다. 운영에서는 비스트리밍 모드가 전제 조건이 된다.
- 권고: 구조 정책(엔드포인트·키 헤더·모델·허용 필드 집합·`maxOutputTokens`·`candidateCount`·`thinkingBudget` 상한·본문 바이트 상한)과 예산 원장을 분리하고, 바이트 일치는 테스트 오라클로만 유지한다. `prepare()`의 130-144행은 이미 구조 검사를 하고 있어 분리가 어렵지 않다.

### H2. 누적 예산 상한 부재 (설계)
- 권한 1개 = 요청 1회 = 상한 56 KRW (`Gate.__init__` 97-101행). 권한 간 합산 원장은 없다.
- `trusted_inputs.py` 기준 16 케이스 × 4 네임스페이스 = 64 권한. 이론 상한 3,584 KRW로, 승인된 실제 허용액 1,000 KRW를 넘는다. 합성이라 실제 소비는 0이지만, 설계에 총액 통제 장치가 없다는 뜻이다.
- 권고: 네임스페이스별 누적 KRW 원장을 두고 `reserve()`에서 합산 후 거부.

### H3. `thinkingConfig` 가 검사·제한되지 않음 (코드)
- `prepare()` 140-154행은 본문 최상위 키 집합만 검사하고 `generationConfig.maxOutputTokens=4096`, `candidateCount=1`만 덮어쓴다. `thinkingConfig.thinkingBudget`, `includeThoughts` 는 그대로 전송된다.
- 공급자가 thinking 토큰을 `maxOutputTokens`와 별도로 제한·과금한다면 4096 상한은 비용 상한이 아니다. 보고서도 "thinking 포함 출력 상한 의미" 를 미검증으로 인정하고 있으나, 이는 코드로 닫을 수 있는 구멍이다.
- 권고: `thinkingBudget` 상한(또는 제거)을 cap 변환에 포함하고 동결 패킷(`trusted_bootstrap.py:39`)도 동일하게 생성.

### H4. `_inner` 래퍼 전송이 게이트를 우회할 수 있음 (코드)
- `send()` 248-253행: `inner = getattr(transport, '_inner', transport)` 후 `type(inner) is httpx.HTTPTransport` 면 통과.
- httpx는 `_send_single_request`에서 **래퍼 객체 자신의** `handle_request`를 호출한다. 패치된 것은 `httpx.HTTPTransport.handle_request`(274행)뿐이므로, 래퍼가 `_inner`에 위임하지 않고 직접 I/O 하면 `prepare/reserve` 없이 전송된다.
- 픽스처에서는 audit hook이 소켓을 막아 무해하지만, 운영에는 audit hook이 없다. 테스트는 `MockTransport`(suite_v3.py:123)만 다루고 `_inner` 래퍼 케이스는 없다.
- 권고: `_inner` 예외를 제거하거나, 래퍼의 `handle_request` 가 패치된 `handle` 과 동일 함수인지 확인.

### H5. 게이트 범위가 httpx 동기 클라이언트에 한정됨 (범위)
- 패치 대상은 `httpx.Client`, `httpx.HTTPTransport`, `httpx.AsyncClient.send` 뿐(267-275행). `AsyncHTTPTransport.handle_async_request` 직접 호출, `requests`/`urllib`/`aiohttp`/gRPC 등은 범위 밖이다.
- "fake send 외 전송 0" 은 audit hook(`runtime_fixture.py:67-69`)이 모든 소켓을 거부해서 성립한 것이지 게이트 자체의 보장이 아니다. 보고서의 "Python audit는 OS 격리 증명이 아님" 과 같은 맥락이나, 운영 배포 시 게이트만으로는 egress 통제가 되지 않는다는 점을 설계 문서에 명시해야 한다.

### M1. 원장 파일 생성과 기록이 원자적이지 않음 (코드)
- `reserve()` 170-173행: `open('xb')` 로 생성한 뒤 `write/flush/fsync`. 생성과 flush 사이에 0바이트 파일이 관측된다.
- 게이트 자체(`FileExistsError` → 거부)는 안전하다. 그러나 `suite_v3.py:22` ProcessRace 는 패배한 프로세스에서 `json.loads(gate._path.read_bytes())` 를 읽으므로, 승자가 아직 기록 전이면 `JSONDecodeError` → 테스트 ERROR. 경쟁 테스트가 1회 통과한 것은 창이 작다는 뜻이지 없다는 뜻이 아니다.
- 권고: 임시 파일에 기록 후 배타적 이동(`os.link` 또는 Windows `MoveFileEx` 비대체 모드), 또는 reader 가 빈 파일을 `RESERVED_CONSUMPTION_UNKNOWN` 으로 취급.

### M2. `INSTALLED` 일회성 가드가 전역이 아님 (코드)
- `install()` 187-191행의 `INSTALLED` 는 모듈 전역이다. 테스트가 이미 쓰는 방식(`suite_v3.py:95-96`, 바이트 동일 복사본 로드)으로 두 번째 복사본에서 `install()` 을 호출하면 `httpx.HTTPTransport.handle_request` 가 교체되어 fake_handler 를 바꿀 수 있고, 원래 모듈의 `ACTIVE` 게이트는 도달 불가가 된다.
- 원장 경로가 같아 이중 지출은 막히지만, `global transport already installed` 메시지는 사실과 다르다.
- 권고: httpx 함수 객체에 마커 속성을 붙여 전역으로 확인.

### M3. cap 이 `min()` 이 아니라 덮어쓰기 (코드, 잠재)
- 147행 `cfg['maxOutputTokens'] = 4096`. 빌더가 1024를 보냈어도 4096으로 **상향**된다.
- 지금은 raw-hash 일치 요구(H1) 때문에 실질 영향이 없다. H1을 해결하며 raw-hash 를 완화하는 순간 결함이 된다.
- 권고: `min(cfg.get('maxOutputTokens', 4096), 4096)`.

### M4. 증명력이 약한 테스트
- `test_lifecycle_paths.py:48-61` fallback 스왑(승인 키 쪽): `success` 권한이 이미 소진되어 원장만으로 `captures == []` 가 된다. 게이트가 없어도 통과한다. 보고서가 "approved-key primitive uses an already spent authority" 로 인정한 부분.
- `test_gate_negatives.py:124-132` 환경 키 교체: 거부 사유를 단언하지 않는다. 역시 원장만으로 통과 가능. `suite_v3.py:138-141` 이 사유 존재를 전역에서 확인하지만 어느 테스트가 냈는지는 구분하지 않는다.
- `guard_events: g.EVENTS` 별칭(`test_gate_negatives.py:179`, `test_runtime_cases.py:95`): 각 그룹 JSON 이 누적 전체 이벤트를 담는다. 정적검토 문서도 "aliased arrays 합산 금지" 로 인지하고 있다. 슬라이스를 저장해야 한다.
- 순서 의존: `test_byte_identical_relocation…`, `test_recreated_gate…`, `test_unknown_reservations…` 는 앞 그룹이 권한을 소진했음을 전제한다. 단독 실행 시 실패.
- 권고: 미사용 권한으로 재실행하고 `g.EVENTS[-1]['reason']` 을 단언.

### M5. 유효기간 하드코딩 (운영 리스크)
- `trusted_bootstrap.py:47` `valid_through: '2026-12-31'`. 2027-01-01 부터 `Gate.__init__` 93-94행이 모든 arm 을 `stale proof` 로 거부해 전체 스위트가 "정상적으로" RED 가 된다.
- 봉인 버전으로 두 봇 교차검증을 진행할 계획이면 일정을 그 전으로 잡거나 기간을 매개변수화해야 한다.

### M6. 검증된 Hermes 는 축소 구성
- `run_offline.py:19` 가 쓰는 `config.yaml` 은 `streaming: false`, `compression.enabled: false`, `auto_title: false`, `auto_recovery_cycles: 0` 이다. "lifecycle INCOMPLETE" 의 직접 원인이다.
- `runtime_fixture.py:164` 는 `skip_context_files/skip_memory/skip_background_review/load_soul_identity=False` 로 생성하고, audit(86행)는 Hermes 디렉터리에서 `.py` 외 파일 읽기를 거부한다. 보고서의 audit denial 수가 writer 115건, reviewer 80건으로 다른데 차이 원인 설명이 없다.
- 권고: 운영 구성과의 차이를 표로 명시하고, 차단된 읽기가 기능 저하(예외 삼킴)를 일으켰는지 확인.

### L. 낮은 심각도·품질
- `trusted_bootstrap.bind(namespace, agent=None)`: 기본값 `None` 이면 24행에서 `AttributeError`. `Refused/RuntimeError` 가 아닌 예외.
- 오래된 설명: `red_fixture.py` docstring 의 `run_isolated.py` 는 존재하지 않음(실제 런처는 `run_offline.py`). `suite_v3.py` docstring 은 "candidate2".
- `suite_v3.py:55` 가 테스트하는 `build_request(auth=…)` 는 httpx 0.28.1 시그니처에 없는 매개변수다. 존재하지 않는 API 면을 테스트하고 있다.
- `transport_init`(235행)은 kwargs 만 검사한다. `HTTPTransport.__init__` 의 `retries` 는 위치 인자로도 전달 가능하며, 이 경우 `Refused` 가 아니라 `kwargs.update` 충돌로 인한 `TypeError` 로 우연히 차단된다. 실질 방어는 `send/handle` 의 `_pool._retries` 검사다.
- httpx 비공개 속성 의존: `_auth, _mounts, _transport, _trust_env, _pool._retries, _build_auth, _build_request_auth, _content, httpx._client.USE_CLIENT_DEFAULT`. `_client.py` 해시 고정은 적절하나 업그레이드 시 전면 재검증 필요.
- 경로·사용자명 하드코딩(`D:/Hermes/…`, `C:/Users/HERMEZ`). `run_offline.py:32` 의 `cwd='C:/Users/HERMEZ'`(실제 홈)는 의도가 불명확하다. 에이전트에는 별도 `cwd` 를 주므로 픽스처 루트로 바꾸는 편이 안전하다.
- 코드 스타일 혼재: 1칸 들여쓰기·세미콜론 압축(`trusted_bootstrap, suite_v3, run_offline, freeze_and_accept`) 과 PEP8(`isolated_integration, test_*`). 검토 비용을 높인다.
- `runtime_fixture.py` 와 `red_fixture.py` 의 1-150행이 동일(생성기 산출물). 봉인 산출물이라 수용 가능.
- 보호 파일 수 3,745(writer) 와 5,079(parent) 는 범위가 달라 모순은 아니나 보고서에 한 줄 설명이 필요하다.

## 3. 보고서 주장 대조

| 주장 | 검증 방법 | 결과 |
|---|---|---|
| full-final 28 / cold-spent 1 / race 2 = 31회 실행, 고유 30 | 테스트 메서드 수 계수: positive 3 + negative 9 + lifecycle 5 + contracts 11 = 28 | 일치 |
| fake 전송 10회 | positive 3 + timeout/429/500/empty/tool 5 + concurrent 1 + race 1 | 일치 |
| 인증 콜백·request hook 사전 차단 | `install()` 200-246행 | 일치 (httpx 범위 내) |
| 65535 → 4096 / candidate 1 | `prepare()` 145-154행 | 일치 |
| 중복 전송 차단 | `reserve()` `open('xb')` | 일치 (M1 유의) |
| 조건부 비용 USD 0.027648 → 56 KRW | (16384×0.75 + 4096×3.75)/1e6 × 2000 = 55.296 → 올림 56 | 일치 |
| 시스템 지시문 경로·본문 길이 미제외 | `wire()` 가 헤더·본문 전체 해시 | 일치 |
| 비밀·인증 파일 미포함 | 전수 확인 | 일치 (사용자명 경로 노출만 있음) |
| 보호 파일 3,745/5,079 불변 | ZIP 에 scratch·원본 증거 없음 | 검증 불가 |

## 4. 권고 순서

1. 교차검증 전 결정: H3, H4, M1 을 후보3 봉인 상태로 둘지, 사람이 승인한 후보4 로 수정할지.
2. 운영 전환 로드맵 확정: 바이트 일치 오라클 → 구조 정책 + 누적 원장(H1, H2). 이 결정 없이는 credential rotation / title / compression 통합을 마쳐도 운영에 쓸 수 없다.
3. 테스트 보강(M4): 미사용 권한으로 fallback·환경 키 재검증, 거부 사유 단언, 그룹별 이벤트 슬라이스 저장.
4. 유효기간·경로 매개변수화(M5, L).
5. 운영 구성 대비표 작성(M6) 및 audit denial 수 차이(115 vs 80) 설명.
