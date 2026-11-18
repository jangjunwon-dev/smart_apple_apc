# 04. 내 AI에 프로젝트 인식시키기

> 팀원마다 Claude, Codex, ChatGPT, Gemini 등 쓰는 AI가 달라도 **같은 규칙·같은 진행 상황**을 알고 답하게 만드는 방법입니다.
> 핵심 파일은 루트의 **`AGENTS.md`** 하나입니다. 나머지 파일은 모두 이것을 불러옵니다.

## 📄 저장소에 들어있는 AI용 파일

| 파일 | 자동으로 읽는 도구 | 내용 |
|---|---|---|
| `AGENTS.md` | Codex CLI/IDE, Cursor, Copilot 등 | **원본** — 프로젝트 요약, 환경, 구조, 규칙 |
| `CLAUDE.md` | Claude Code | `@AGENTS.md` import + Claude 전용 메모 |
| `GEMINI.md` | Gemini CLI | `@AGENTS.md` import |
| `.github/copilot-instructions.md` | GitHub Copilot | 핵심 요약 |
| `docs/02_roadmap.md` | (AI가 작업 전 읽도록 지시됨) | 현재 단계·할 일 |
| `docs/03_architecture.md` | (AI가 작업 전 읽도록 지시됨) | 토픽·메시지 규약 |

> ✏️ 규칙을 바꾸고 싶으면 **`AGENTS.md`만 수정**하세요. 다른 파일은 자동으로 따라갑니다.

---

## A. 터미널/IDE 코딩 AI (저장소 폴더에서 실행) — 가장 확실

저장소를 클론한 폴더(`~/apc_ws`)에서 실행하기만 하면 **자동으로** 지침 파일을 읽습니다.

### Claude Code
```bash
cd ~/apc_ws
claude
```
- `CLAUDE.md` → `AGENTS.md` 자동 로드
- 확인: `/memory` 입력 → 불러온 파일 목록에 `CLAUDE.md`, `AGENTS.md`가 보이면 성공
- 내 파트 기억시키기 (개인 설정, 저장소에 안 올라감): `~/.claude/CLAUDE.md` 에 아래 추가
  ```markdown
  # 개인 설정
  - smart_apple_apc 프로젝트에서 나는 🅐 Vision(apc_vision) 담당이다.
  ```

### Codex (CLI / VS Code 확장)
```bash
cd ~/apc_ws
codex
```
- `AGENTS.md` 자동 로드
- 내 파트 기억시키기: `~/.codex/AGENTS.md` (전역 개인 지침)에 위와 같은 한 줄 추가

### Cursor
- `~/apc_ws` 폴더를 열면 `AGENTS.md` 를 프로젝트 규칙으로 사용합니다.

### Gemini CLI
```bash
cd ~/apc_ws && gemini
```
- `GEMINI.md` → `AGENTS.md` import

---

## B. 웹 채팅 AI (claude.ai, ChatGPT 등)

웹 채팅은 저장소를 자동으로 읽지 못하므로 **프로젝트(Project) 기능**에 자료를 넣어둡니다.

### claude.ai
1. 왼쪽 **Projects → 새 프로젝트** (이름: `Smart APC`)
2. 프로젝트 지식(Knowledge)에 **GitHub 연결**로 이 저장소 추가 (권장, 최신 상태 동기화)
   - 또는 `AGENTS.md`, `docs/02_roadmap.md`, `docs/03_architecture.md` 파일 업로드
3. 프로젝트 지침(Instructions)에 붙여넣기:
   ```
   이 프로젝트는 smart_apple_apc 저장소다. AGENTS.md의 규칙을 항상 따르고,
   답하기 전에 docs/02_roadmap.md로 현재 단계를 확인해라.
   나는 [🅐 Vision / 🅑 AMR / 🅒 Sim·통합] 담당이다.
   ```

### ChatGPT
1. **프로젝트 → 새 프로젝트** 생성
2. 파일에 `AGENTS.md`, `docs/02_roadmap.md`, `docs/03_architecture.md` 업로드 (GitHub 커넥터가 있으면 연결)
3. 프로젝트 지침에 위와 같은 문장 입력

> ⚠️ 업로드 방식은 **파일이 바뀌면 다시 올려야** 합니다. 로드맵이 갱신되면 새 버전으로 교체하세요.

---

## C. 대화 시작용 프롬프트 템플릿

새 작업을 시작할 때 첫 메시지로 사용하세요.

```
smart_apple_apc 프로젝트 작업이야. 나는 [🅐 Vision] 담당.
AGENTS.md, docs/02_roadmap.md, docs/03_architecture.md 를 먼저 읽고
1) 지금 내 파트에서 다음으로 할 일
2) 그 작업을 위한 구체적인 단계와 명령어
를 알려줘. 인터페이스(apc_interfaces)는 바꾸지 마.
```

작업이 끝난 뒤:
```
방금 한 작업 기준으로 docs/02_roadmap.md 체크리스트 갱신해주고,
커밋 메시지를 규칙(feat(vision): ...)에 맞게 제안해줘.
```

---

## D. 팀 운영 팁

- **진행 상황 공유 = `docs/02_roadmap.md` 갱신 PR.** 팀원도 AI도 이 파일 하나만 보면 현재 상태를 압니다.
- AI가 Humble, Gazebo Classic(`gazebo_ros`), `ROS_LOCALHOST_ONLY` 같은 옛날 방식을 제안하면 → "AGENTS.md 환경 기준으로 다시" 라고 요청
- AI가 만든 코드도 **본인이 이해하고 설명할 수 있어야** PR에 올립니다 (리뷰 때 질문함).
