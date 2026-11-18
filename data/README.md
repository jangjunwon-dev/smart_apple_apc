# data/ — 데이터셋 폴더

> ⚠️ **실제 데이터는 GitHub에 올리지 않습니다** (용량 제한, 저장소가 무거워짐).
> 이 폴더에는 **구조와 설명서, 작은 샘플만** 커밋하고, 원본·가공 데이터는 **팀 공유 드라이브**에서 받아 각자 PC의 같은 위치에 둡니다.

## 📁 폴더 구조

```
data/
├── README.md        # 이 파일 (커밋 O)
├── sample/          # 테스트용 소량 샘플 — 사과 사진 10~20장, 총 10MB 이하 (커밋 O)
├── raw/             # 원본 데이터 그대로 (커밋 X, 공유 드라이브)
│   └── <데이터셋이름>/     예: aihub_apple_quality/
└── processed/       # 학습용으로 가공한 데이터 (커밋 X, 공유 드라이브)
    └── <버전>/            예: v1_yolo/
        ├── images/{train,val,test}/
        ├── labels/{train,val,test}/
        └── data.yaml      # YOLO 학습 설정
```

| 폴더 | 내용 | GitHub | 담당 |
|---|---|---|---|
| `sample/` | 노드·코드 테스트용 소량 이미지 | ✅ 커밋 | 🅐 조한서 |
| `raw/` | 다운로드한 원본 (수정 금지) | ❌ 공유 드라이브 | 🅐 조한서 |
| `processed/` | 전처리·라벨 변환 결과 | ❌ 공유 드라이브 | 🅐 조한서 |

## 🔗 공유 드라이브

- 위치: [Google Drive `smart_apple_apc/data`](https://drive.google.com/drive/folders/1pAv_fzKDRd6Efjm4E63q6t5o_J5rNcx2) (팀원 3명에게만 공유)
- 받은 뒤 위 구조 그대로 `~/apc_ws/data/` 아래에 풀기

## 📋 데이터셋 기록 (새 데이터를 추가하면 한 줄씩 기록)

| 이름 | 출처 (URL) | 라이선스/이용 조건 | 수량 | 내려받은 날짜 | 위치 |
|---|---|---|---|---|---|
| AI Hub 농산물 품질(QC) 이미지 — 사과(부사·양광) | [aihub dataSetSn=149](https://aihub.or.kr/aihubdata/data/view.do?currMenu=115&topMenu=100&aihubDataSe=realm&dataSetSn=149) | AI Hub 이용약관 (내국인 신청·승인, 재배포 금지) | 학습 이미지 6개 zip ≈24.3GB, 검증 6개 ≈3.7GB, 라벨 12개 ≈14MB | _(받은 날짜)_ | `raw/aihub_qc_apple/` |

## 🔄 가공 버전 기록

| 버전 | 원본 | 처리 내용 (리사이즈, 라벨 변환, 분할 비율 등) | 스크립트 | 날짜 |
|---|---|---|---|---|
| | | | | |

## ⬇️ 받는 방법 (AI Hub 사과 데이터, WSL)

**업로드 담당 (1명, 장준원)** — AI Hub → 내 PC → 공유 드라이브
```bash
# 준비: AI Hub 데이터 신청 승인 + API key 발급 (스크립트 상단 주석 참고)
# Windows에 'Google Drive 데스크톱' 설치 → 보통 G: 드라이브로 연결됨
# WSL에서 /mnt/g 가 안 보이면 (최초 1회, 재부팅 후 다시):
sudo mkdir -p /mnt/g && sudo mount -t drvfs G: /mnt/g
bash scripts/download_aihub_apple.sh --drive "/mnt/g/내 드라이브/smart_apple_apc/data/raw"
bash scripts/download_aihub_apple.sh --train --drive "/mnt/g/내 드라이브/smart_apple_apc/data/raw"   # 학습 이미지까지
```

**나머지 팀원** — 공유 드라이브 → 내 PC (AI Hub 신청 불필요)
```bash
# Google Drive 데스크톱의 '공유 문서함'에 있는 폴더를 바로가기로 '내 드라이브'에 추가한 뒤
mkdir -p ~/apc_ws/data/raw
cp -r "/mnt/g/내 드라이브/smart_apple_apc/data/raw/aihub_qc_apple" ~/apc_ws/data/raw/
```
> 압축은 `~/apc_ws/data/raw/` 안(리눅스 쪽)에서 풀기 — `/mnt/g/`에서 풀면 매우 느림

## 규칙

1. `raw/`의 원본은 **절대 직접 수정하지 않기** → 가공은 항상 스크립트로 `processed/`에 새로 만들기
2. 가공 스크립트는 `src/apc_vision/` 또는 `scripts/`에 커밋해서 **누구나 같은 결과를 재현**할 수 있게 하기
3. 공공데이터(AI Hub 등)는 이용 약관상 **재배포 금지**인 경우가 많으니 공유 범위는 팀 내부로 한정
