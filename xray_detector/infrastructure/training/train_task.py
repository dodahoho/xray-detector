import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Sökväg till YOLO data.yaml")
    parser.add_argument("--weights", required=True, help="Basmodell")
    parser.add_argument("--output", required=True, help="Katalog för sparade vikter")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    from ultralytics import YOLO

    from xray_detector.infrastructure.detectors.yolo_detector import resolve_device

    device = resolve_device(args.device)
    print(f"Träning på enhet: {device}")
    model = YOLO(args.weights)
    model.train(
        data=args.dataset,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=device,
        project=args.output,
        name=f"{Path(args.weights).stem}",
        exist_ok=True,
    )
    print("TRAINING_DONE")


if __name__ == "__main__":
    main()
