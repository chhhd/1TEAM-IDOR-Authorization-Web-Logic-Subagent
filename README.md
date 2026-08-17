# 1TEAM-IDOR-Authorization-Web-Logic-Subagent

팀원4(박나현) — IDOR / Authorization / Web Logic Subagent 담당 산출물.
독립 실행형(standalone) 버전 — 팀 공용 하네스(`dast-harness`) 없이도 그 자체로
동작하고 테스트할 수 있게 구성돼 있다.

## 이 저장소에 있는 것

| 산출물 | 위치 | 내용 |
|---|---|---|
| Subagent 정의 | `.claude/agents/access-control-agent.md` | IDOR/BOLA/수직·수평 권한상승/비즈니스 로직 우회를 다루는 access-control subagent. injection류는 명시적으로 스코프 밖 |
| 진단 절차 skill | `.claude/skills/access-control-checklist/SKILL.md` | 두 체크 계열(IDOR/BOLA/PrivEsc, Business Logic Bypass)을 Check 1~5 절차로 구조화 |
| 검증용 취약 앱 | `testapp/app.py` | IDOR(`/api/orders/<id>`), 정상 대조군(`/api/profile/<id>`), 수직 권한상승(`/admin/stats`), 비즈니스 로직 우회(`/api/coupon/redeem`) — 127.0.0.1:5055 |

## 설계 요점

- **정적 분석 우선, 동적 확인은 그 다음.** 코드 인텔리전스(정의로 이동/참조 찾기)로
  서버사이드 소유권·역할 체크가 있는지부터 확인하고, 의심되는 엔드포인트만 실제
  요청으로 재현한다.
- **CONFIRMED vs SUSPECTED을 명확히 구분한다.** 실제 우회를 관찰했을 때만
  CONFIRMED — 코드에서 체크 누락을 발견했지만 아직 재현 못 했으면 SUSPECTED.
- **두 체크 계열을 하나의 skill로 묶었다.** "서버가 실제로 권한을 검사하는가"라는
  공통 질문 위에서 객체/역할 단위(IDOR·BOLA·PrivEsc)와 워크플로 단위(Business
  Logic)를 다루므로 컨텍스트를 재사용할 수 있다.
- **파괴적/상태변경 probe는 먼저 알린다.** 쿠폰 반복사용 같은 비즈니스 로직
  테스트는 실제 상태를 바꾸므로, 보내기 전에 무엇을 왜 보내는지 밝힌다.

## 실제로 검증됨

`testapp/app.py`를 실제로 띄우고 이 agent 정의를 그대로 구동해 4개 발견 사항을
전부 라이브 요청으로 확정한 바 있다.

| 판정 | 종류 | 엔드포인트 |
|---|---|---|
| CONFIRMED | IDOR | `GET /api/orders/<id>` — alice 토큰으로 bob의 주문 조회 성공 |
| CONFIRMED | Vertical-PrivEsc | `GET /admin/stats` — `X-Admin: true` 헤더만 붙이면 일반 user role도 통계 조회 가능 (서버가 세션 role이 아니라 클라이언트가 보낸 헤더를 신뢰) |
| CONFIRMED | Business-Logic-Bypass | `POST /api/coupon/redeem` — 같은 쿠폰을 3번 연속 리딤해도 매번 성공 (일회성 강제 없음) |
| Not vulnerable (negative control) | — | `GET /api/profile/<id>` — 소유권 + role 오버라이드 체크가 정상 작동, 모든 걸 취약점으로 몰아가지 않음을 보여줌 |

## 실행

```bash
python3 testapp/app.py &     # 127.0.0.1:5055
```

토큰: `alice-token`(id=1, user), `bob-token`(id=2, user), `admin-token`(id=3, admin).
예: `curl -H "Authorization: Bearer alice-token" http://127.0.0.1:5055/api/orders/102`

## 다른 저장소와의 관계

이 저장소는 dast-harness 정렬(팀 공용 계약 — `AgentFinding`/`Evidence`/`Probe`,
`AgentHttpClient`) **이전의 독립 실행형 버전**을 담고 있다. dast-harness에 맞춰
조정되고 recon-agent/injection-agent와 나란히 통합된 최신 버전은
[`SECURITY-1TEAM-Orchestrator-chain`](https://github.com/chhhd/SECURITY-1TEAM-Orchestrator-chain)에
있다. 이 저장소는 access-control-agent 단독으로도 동작을 확인할 수 있는
자기완결형 데모/참고용으로 유지한다.

## 알아둘 것

- `testapp/`은 의도적으로 취약하게 만든 연습용 앱이다. `127.0.0.1` 바인딩을
  벗어나거나 실제 배포 환경에 올리지 않는다.
- 이 세션 환경(SDK/VS Code 확장)에서는 `.claude/agents/*.md`가 Agent tool의
  invokable subagent 목록에 자동 등록되지 않아, 위 검증은 `general-purpose`
  에이전트에 이 정의 전체를 주입해서 진행했다. 파일 자체는 표준 Claude Code
  세션에서 `/agents`로 정상 등록되는 유효한 정의다.
