import argparse
import csv
from datetime import datetime
from pathlib import Path
import yaml

DOCS_PATH = Path.home() / "apc_ws/docs/experiments.md"

HEADER = """# 비전 모델 실험 기록 (Apple Grader)

학습 실행(`runs/`)별 모델 아키텍처, 하이퍼파라미터, 검증 성능(`best.pt` 기준)을 기록합니다.

| 실험 ID | 날짜 | 모델 (알고리즘) | 데이터셋 | 해상도 / 배치 | Epoch (Best/Total) | Precision | Recall | mAP50 | mAP50-95 | 비고 |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
"""

def parse_best_metrics(csv_path: Path):
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [
            {k.strip(): v.strip() for k, v in r.items()}
            for r in reader
            if r and any(v.strip() for v in r.values() if v)
        ]

    if not rows:
        raise ValueError(f"아직 기록된 에포크가 없습니다: {csv_path}")

    best_row = max(
        rows,
        key=lambda r: 0.1 * float(r["metrics/mAP50(B)"]) + 0.9 * float(r["metrics/mAP50-95(B)"])
    )
    best_epoch = int(float(best_row["epoch"]))
    return best_row, best_epoch

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="apple_grader_v1", help="runs/ 하위 실험 폴더명")
    parser.add_argument("--dataset", default="AI Hub QC 사과 (25,024장)", help="사용한 데이터셋 설명")
    parser.add_argument("--note", default="4등급(특/상/보통/비상품) 베이스라인", help="실험 비고 및 변경점")
    args = parser.parse_args()

    run_dir = Path.home() / "apc_ws/runs" / args.run
    csv_path = run_dir / "results.csv"
    args_path = run_dir / "args.yaml"

    if not csv_path.exists():
        raise FileNotFoundError(f"results.csv 파일을 찾을 수 없습니다: {csv_path}")

    with open(args_path, encoding="utf-8") as f:
        train_args = yaml.safe_load(f)

    best_row, best_epoch = parse_best_metrics(csv_path)

    model_name = Path(str(train_args.get("model", "unknown"))).name
    imgsz = train_args.get("imgsz", "-")
    batch = train_args.get("batch", "-")
    total_epochs = train_args.get("epochs", "-")
    today = datetime.now().strftime("%Y-%m-%d")

    precision = float(best_row["metrics/precision(B)"])
    recall = float(best_row["metrics/recall(B)"])
    map50 = float(best_row["metrics/mAP50(B)"])
    map50_95 = float(best_row["metrics/mAP50-95(B)"])

    new_line = (
        f"| `{args.run}` | {today} | `{model_name}` | {args.dataset} | "
        f"{imgsz} / {batch} | {best_epoch} / {total_epochs} | "
        f"{precision:.3f} | {recall:.3f} | {map50:.3f} | {map50_95:.3f} | {args.note} |"
    )

    DOCS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DOCS_PATH.exists():
        lines = DOCS_PATH.read_text(encoding="utf-8").splitlines()
    else:
        lines = HEADER.strip().splitlines()

    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"| `{args.run}` |"):
            lines[i] = new_line
            updated = True
            break

    if not updated:
        lines.append(new_line)

    DOCS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[기록 완료] {DOCS_PATH}")
    print(new_line)

if __name__ == "__main__":
    main()
