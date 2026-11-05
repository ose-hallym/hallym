# Candidate3 동결 결과 — 전체 수명주기 검증 미완료

## 판정
- 승인된 추가 후보 1개를 구현·동결했다. 누적 **3/max3**, 자동 네 번째 후보 없음.
- 최종 후보 SHA256: `de14ec8e4f4178892b687e96dcf6266503657653e9cd4c20295d7c83f2933bac`.
- 최종 동일 소스의 full-final **28 PASS / 0 FAIL / 0 ERROR**, cold-spent 1 PASS, 별도 cold-process 2개 각각 1 PASS. 합계 **31 method executions**. 실패했던 부분만 반복하여 만든 합격이 아니다.
- 그러나 **전체 credential refresh/automatic fallback 및 title/compression lifecycle은 INCOMPLETE**다. 기존 환경 키 교체·실제 client-swap primitive·auxiliary `call_llm` 진입만 실행했다. 따라서 테스트 GREEN을 전체 요구사항 충족 또는 채택으로 표시하지 않았다.
- `candidate_accepted=false`, 부모의 fresh independent review 1회 대기. 이 작업자는 리뷰어를 실행하지 않았다. 최종 동결 이후 후보·bootstrap·테스트는 수정하지 않았다.

## 구현 및 실행 증거
- 고정 synthetic user/system content와 사전 배정된 context에서 원본 AIAgent constructor, system/API/native builders 및 HTTPX `build_request`로 예상 전체 raw/capped wire를 **arm 전에 별도로 생성·동결**한다. outgoing 관측값은 issuer 입력이 아니다. context의 시스템 경로·content-length를 제거하지 않는다.
- `trusted_inputs.py`의 DEVELOPMENT/WRITER/PARENT/REVIEW, 총 64개 disjoint test authority를 배정했다. 각 ID의 root/ledger 경로는 고정이다. PARENT/REVIEW는 부모 영역 경로만 선언했고 생성·실행하지 않았다.
- 새 namespace는 synthetic test allocation일 뿐 실제 bot identity, vendor token/cost proof가 아니다. 원본 ledger를 reset/copy-as-unused하지 않았다.
- 원본 HTTPX auth callback의 메모리 list 부작용을 실제 실행으로 RED 재현: 2개 최소 테스트에서 **2 assertion failures / 0 setup errors**. 하나는 auth effect, 하나는 동일 namespace를 음성으로 잘못 취급한 기존 harness contract다.
- 생성 context wire와 old-root wire의 불일치도 assertion RED로 보존했다. 이는 새로운 context의 비교이며 과거 rejected bytes를 복원한 주장이 아니다.
- 최종 후보는 auth callable/Auth flow/tuple을 constructor, request/send/build 관련 경로에서 실행 전에 거부한다. event_hooks 거부를 유지했다. 최종 auth 및 hook 부작용 0 assertion PASS. no-auth fakekey-header positive는 통과했다.
- 실제 전체 AIAgent constructor → `run_conversation` → native Gemini builder → HTTPX final request → fake transport에서 정상 응답 `SYNTHETIC_OK`, 요청 1회를 확인했다. thinking 원본65535 → final4096/candidate1도 확인했다.
- continuation은 첫 fake send 이후 실제 추가 요청을 raw-wire mismatch로 거부했다. 이 case는 정상 완료 응답이 아니라 의도된 차단 오류 응답이다.
- timeout/429/500/empty/tool 각각 최초 전송 뒤 reservation이 `RESERVED_CONSUMPTION_UNKNOWN`으로 남고 두 번째 fake send는 없었다. **Hermes 자체의 client rebuild/retry 시도는 존재한다**. 재시도 control flow를 제거했다거나 시도 자체가 0이라고 주장하지 않는다.
- final 실행의 synthetic fake send는 총10회: full suite9 + 별도 process race1. 8-thread native-dispatch helper 경쟁에서는1회, 두 cold process 같은 authority에서는 합계1회. 동시 full-conversation loop 검증으로 확대하지 않는다.

## 보존·격리·잔여 사항
- 보호대상 **3745개**의 사전/사후 bytes/hash·regular/singlelink/nonreparse 검사 일치. 추가 사전 pin520개(원본 Hermes519 + read-only HTTPX source1)도 hash 일치. 최종 import 원본 Hermes538개 모두 postcheck 일치하고 사전 보호/pin 집합 밖 runtime source는 없다.
- HTTPX 설치 source `_client.py`는 원래 hardlink6이다. 실제 runtime은 기존 `_client.cpython-314.pyc`를 읽었다. 이 의존성의 read-only source hash 검사와 worker manifest의 strict singlelink 검사를 혼동하지 않았다. 집계기의 과도한 singlelink assertion 실패는 `POSTPROCESS-ISSUE.json`에 보존했고, 후보나 테스트를 수정·재실행하지 않았다.
- startup audit denial, coroutine 미대기 경고, socket self-pipe 생성 거부 후 event-loop cleanup 경고를 그대로 보존했다. full-final audit denial115개. 외부 I/O 성공의 증거가 아니라 허용 전 거부 기록이다.
- 모든 런타임은 audit 설치 후 원본 Hermes `.py`를 byte-identical mirror로 import했다. 외부 모델/네트워크·socket 작업 완료, 실제 private 내용 읽기, 지출, 배포는0이다. Python audit는 OS sandbox가 아니며 hostile global monkeypatch/native/OS 우회 방지는 미입증이다.
- original policy input16384/output+thinking4096, rates0.75/3.75USD/M의 조건부 금액은 **USD0.027648**. fake FX2000의 올림56KRW는 synthetic-only다. 실제 project/token/vendor FX proof는 없다.
- 실제 `hallym_refomax_bot` 실행 아님. 실제 1000KRW authority 미소모, DATA6 source accepted 범위 재개방 없음, live entry/deployment false.

재현 및 부모 리뷰 인터페이스는 `REPLAY.md`, 항목별 경계는 `COVERAGE.md`, 기계 판정은 `RESULT.json`, raw 명령/환경/stdout/stderr/exit/snapshot은 `scratch/`에 있다. 이 상태에서 멈춘다. 후보4 또는 잔여 lifecycle 구현을 자동으로 시작하지 않는다.
