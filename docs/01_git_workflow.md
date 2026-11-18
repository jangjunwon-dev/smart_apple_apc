# 01. Git 협업 규칙

> 3명이 짧은 기간에 파트별로 나눠 개발하므로 **규칙은 최소한, 대신 꼭 지킨다.**

## 1. 브랜치 전략 (GitHub Flow)

```
main  ─────●────────●────────●───────▶   (항상 빌드되는 상태 유지)
            \      /  \      /
feat/vision-yolo ●─●   feat/amr-nav2 ●─●
```

- `main` 에 **직접 push 금지** → 반드시 PR
- 작업 브랜치 이름: `종류/파트-내용`

| 종류 | 예시 |
|---|---|
| `feat/` 새 기능 | `feat/vision-yolo-detect`, `feat/amr-nav2-client`, `feat/sim-conveyor` |
| `fix/` 버그 | `fix/amr-queue-overflow` |
| `docs/` 문서 | `docs/update-roadmap` |
| `chore/` 설정·스크립트 | `chore/ci-cache` |

## 2. 하루 작업 루틴

```bash
# 시작할 때
git switch main
git pull                                   # 최신 main 받기
git switch -c feat/vision-yolo-detect      # 새 브랜치 (이미 있으면 git switch 브랜치명)
git rebase main                            # 기존 브랜치면 main 최신 반영

# 작업 중 (자주, 작게)
git add -p                                 # 바뀐 부분 확인하며 추가
git commit -m "feat(vision): YOLO 사과 검출 추론 추가"

# 끝낼 때
git push -u origin feat/vision-yolo-detect
gh pr create --fill                        # 또는 GitHub 웹에서 PR 생성
```

## 3. 커밋 메시지 규칙

```
<종류>(<범위>): <한 줄 요약>

(선택) 왜 바꿨는지 / 참고 이슈 #12
```

- 종류: `feat` `fix` `docs` `refactor` `test` `chore`
- 범위: `vision` `amr` `sim` `bringup` `interfaces` `docs` `scripts`
- 예: `fix(amr): 큐가 비었을 때 IDLE 상태로 안 돌아가는 문제 수정`

## 4. PR 규칙

1. PR 템플릿 체크리스트 채우기 (빌드·테스트 확인)
2. **리뷰어 1명 이상 승인** 후 머지 — 다른 파트 패키지를 건드렸으면 그 파트 담당자 필수
3. 머지 방식: **Squash and merge** (main 기록을 깔끔하게)
4. 머지 후 브랜치 삭제
5. `apc_interfaces` 변경 PR은 **3명 모두 승인**

## 5. 절대 커밋하지 않는 것 (`.gitignore` 처리됨)

- `build/`, `install/`, `log/`, `.venv/`
- 데이터셋 `data/*`, 모델 가중치 `models/*.pt` → **팀 공유 드라이브** 사용, 경로만 문서에 기록
- 개인 설정, API 키, `.env`

## 6. 충돌(conflict)이 났을 때

```bash
git switch feat/내브랜치
git fetch origin
git rebase origin/main          # 충돌 파일 수정
git add <수정한파일>
git rebase --continue
git push --force-with-lease     # 내 브랜치에만! main 에는 절대 금지
```

> 모르겠으면 혼자 해결하지 말고 팀 채팅에 스크린샷 → 같이 보기.

## 7. GitHub 저장소 설정 (관리자 1회)

- Settings → Branches → `main` 보호 규칙: *Require a pull request before merging*, *Require approvals: 1*, *Require status checks (CI)*
- Settings → Collaborators → 팀원 2명 초대 (Write 권한)
- Issues 라벨: `vision` `amr` `sim` `interface-change` `bug` `help-wanted`
