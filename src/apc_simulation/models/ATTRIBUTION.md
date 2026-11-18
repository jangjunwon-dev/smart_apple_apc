# Gazebo 모델 출처 (ATTRIBUTION)

`apc_world_v2_preview.sdf` 와 사과 스포너(`apple_model:=ycb`)에서 쓰는 모델·텍스처입니다. 외부 모델은 모두 **Gazebo Fuel** 에서 받았고,
라이선스는 Fuel API(`https://fuel.gazebosim.org/1.0/<owner>/models/<name>`)의 `license_name` 으로 확인했습니다
(확인일 2026-11-18). CC-BY 4.0 모델은 아래처럼 출처를 표기해야 합니다.

| 폴더 | 원본 이름 (버전) | 제작자 / 업로더 | 라이선스 | 원본 URL | 변경 사항 |
|---|---|---|---|---|---|
| `euro_pallet` | Euro pallet (v3) | Gérald Lelong / OpenRobotics | CC0 1.0 | https://fuel.gazebosim.org/1.0/OpenRobotics/models/Euro%20pallet | 메시 URI 를 `model://euro_pallet/...` 로 변경, 썸네일 제외 |
| `Pallet_Rack` | Pallet_Rack (v1) | Cole Biesemeyer / OpenRobotics | CC-BY 4.0 | https://fuel.gazebosim.org/1.0/OpenRobotics/models/Pallet_Rack | 없음 |
| `Pallet_Jack` | Pallet_Jack (v1) | Cole Biesemeyer / OpenRobotics | CC-BY 4.0 | https://fuel.gazebosim.org/1.0/OpenRobotics/models/Pallet_Jack | 없음 |
| `Forklift` | Forklift (v1) | Cole Biesemeyer / OpenRobotics | CC-BY 4.0 | https://fuel.gazebosim.org/1.0/OpenRobotics/models/Forklift | 없음 |
| `ycb_apple` | 013_apple (YCB Object and Model Set, google_16k) — AI Habitat 변환본 `textured.glb.orig` | 원본 3D 스캔: YCB Benchmarks (B. Calli et al., https://www.ycbbenchmarks.com/) / GLB 변환: Meta AI Habitat (`ai-habitat/ycb`) | CC-BY 4.0 (원본 `LICENSE.txt` 동봉, 확인일 2026-11-18) | https://huggingface.co/datasets/ai-habitat/ycb/tree/main/meshes/013_apple/google_16k | `scripts/prep_ycb_apple.py` 로 변환: 수평 중심 원점·수평 반지름 1·바닥 z=-1 로 정규화(축 유지, +z 위), 텍스처 4096 PNG → 1024 JPG(품질 90), GLB 재패킹. 반지름별 크기 조절(scale)·무작위 yaw 는 스포너가 적용 |
| `apc_apple_crate` | (자체 제작) | Smart APC 팀 | 이 저장소 라이선스를 따름 | – | 단순 도형으로 직접 제작한 노란 사과 상자 |
| `apc_preview_assets/meshes` | (자체 생성) | Smart APC 팀 | 이 저장소 라이선스를 따름 | – | `scripts/gen_preview_world.py` 가 만드는 바닥·벽·철골·저장고 OBJ |

## 텍스처 (`apc_preview_assets/materials/textures/`)

모두 **ambientCG** 의 1K-JPG 판을 받아 필요한 맵만 넣었습니다. ambientCG 의 모든 에셋은 **CC0 1.0** 입니다
(라이선스 페이지 https://docs.ambientcg.com/license/ 에서 "CC0 1.0 Universal" 확인, 확인일 2026-11-18).
CC0 이라 출처 표기 의무는 없지만 추적을 위해 기록합니다.

| 파일 | 원본 에셋 | 라이선스 | 원본 URL | 용도 / 변경 사항 |
|---|---|---|---|---|
| `Concrete034_1K-JPG_{Color,NormalGL,Roughness}.jpg` | Concrete 034 | CC0 1.0 | https://ambientcg.com/view?id=Concrete034 | 초록 에폭시 바닥. 파일 변경 없음 (SDF `diffuse` 초록색을 곱해 색 표현) |
| `CorrugatedSteel007A_1K-JPG_Color_white.jpg` | Corrugated Steel 007 A | CC0 1.0 | https://ambientcg.com/view?id=CorrugatedSteel007A | 흰 샌드위치 패널 벽. 원본 Color(하늘색)를 흑백 변환 후 평균 밝기 158 → 228 로 보정 (PIL) |
| `CorrugatedSteel007A_1K-JPG_{NormalGL,Roughness}.jpg` | Corrugated Steel 007 A | CC0 1.0 | https://ambientcg.com/view?id=CorrugatedSteel007A | 흰 샌드위치 패널 벽 (골판 요철). 변경 없음 |
| `Plastic010_1K-JPG_{NormalGL,Roughness}.jpg` | Plastic 010 | CC0 1.0 | https://ambientcg.com/view?id=Plastic010 | 저온저장고 단열 패널. 변경 없음 |

- CC-BY 4.0: https://creativecommons.org/licenses/by/4.0/ / CC0 1.0: https://creativecommons.org/publicdomain/zero/1.0/
- 비상업(NC)·변경금지(ND) 라이선스 모델(예: MovAi `pallet`, `shelf`, `Warehouse`)은 쓰지 않습니다.
- 새 모델을 추가할 때는 이 표에 한 줄 추가하고, 폴더 바로 아래에 `model.config` 가 오게 넣을 것.
