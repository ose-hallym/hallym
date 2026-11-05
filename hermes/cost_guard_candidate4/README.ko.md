# Make 비용 차단장치 후보4 — 검토·수정본 (검토용, 운영 배포본 아님)

- 작성일: 2026-11-05
- 성격: 헤르메스(스카이넷)가 보낸 후보3 검토용 ZIP(`Make_cost_guard_candidate3_SOURCE_REVIEW.zip`, SHA256 `792e532f…7d61`)을 사용자 지시로 검토하고 수정한 **후보4 소스**. Hermes 연동 전체 스위트는 이 환경에서 실행하지 못했으므로 **Hermes 환경 검증 전**이다.
- 후보3 봉인 정책(3/max3, 자동 4차 수정 금지)에 따라, 이 변경은 사용자가 지시한 후보4로 취급한다.

## 구성

| 경로 | 내용 |
|---|---|
| `source/` | 후보4 소스 15개(후보3 14개 + `cap_policy.py`). 수정 파일 9개, 미수정 6개. |
| `patches/candidate3-to-candidate4.diff` | 후보3 대비 전체 diff |
| `CHANGELOG.ko.md` | 변경 목록, 변경하지 않은 것, 긍정 경로 영향 주의사항, 검증 상태, Hermes 실행 절차 |
| `selfcheck/selfcheck_candidate4.py` | Hermes 없이 수정 동작을 확인하는 자체 검증 스크립트(httpx 0.28 필요) |
| `docs/CODE-REVIEW-candidate3-2026-11-05.ko.md` | 후보3 코드 검토 결과(발견 H1~H5, M1~M6, L) |
| `docs/SKYNET-FINAL-REPORT-candidate3.ko.md` | 후보3 원본 README(스카이넷 최종 검증보고서, 바이트 동일) |
| `docs/` 나머지, `evidence/` | 후보3 원본 문서·증거. 후보4 결과가 아니다. |
| `evidence/CANDIDATE4-SOURCE-PINS.json` | 후보4 소스 15개 SHA256과 후보3 기준 SHA |
| `MANIFEST.json` | ZIP 내 파일별 크기·SHA256(자기 자신 제외) |

## 먼저 읽을 순서

1. `CHANGELOG.ko.md` 3절 "긍정 경로에 영향을 줄 수 있는 변경" — Hermes 환경에서 가장 먼저 확인할 네 가지.
2. `CHANGELOG.ko.md` 1절 변경 목록과 `patches/` diff.
3. `docs/CODE-REVIEW-candidate3-2026-11-05.ko.md` — 변경 근거.

## 자체 검증 실행

```bash
python -m venv venv && venv/bin/pip install httpx==0.28.1
venv/bin/python -I -B selfcheck/selfcheck_candidate4.py source
```

11개 검사가 모두 PASS여야 한다. 이 스크립트는 스텁 부트스트랩과 fake transport를 쓰며, 네트워크·실제 키·Hermes 원본을 사용하지 않는다.

## 포함하지 않은 것

API 키, 인증 파일, 회사 자료, 원장, scratch, 후보3의 raw 로그. 코드의 `SYNTHETIC-ONLY-…`는 실제 키가 아니다. 경로 상수(`D:/Hermes/…`)는 후보3 그대로다.
