import argparse
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="Mamba-YOLO simple test script: val or predict")
    parser.add_argument("--mode", choices=["val", "predict"], default="val", help="Test mode: val or predict")
    parser.add_argument("--model", type=str, required=True, help="Model path: .pt weights or .yaml config")
    parser.add_argument("--data", type=str, default=None, help="Dataset config data.yaml (required for val mode)")
    parser.add_argument("--imgsz", type=int, default=640, help="Input image size")
    parser.add_argument("--device", type=str, default="0", help="Device: GPU index or cpu")
    parser.add_argument("--batch", type=int, default=8, help="Batch size (val only)")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold (predict only)")
    parser.add_argument("--source", type=str, default=None, help="Prediction source: file/folder/video (predict only)")
    parser.add_argument("--project", type=str, default="./runs/test", help="Output project directory")
    parser.add_argument("--name", type=str, default="exp", help="Output experiment name")
    # export options
    parser.add_argument("--save_txt", action="store_true", help="Save predictions as YOLO txt labels (predict)")
    parser.add_argument("--save_conf", action="store_true", help="Include confidence in saved txt (predict)")
    parser.add_argument("--save_json", action="store_true", help="Save COCO-style predictions.json (val)")
    parser.add_argument("--iou", type=float, default=0.7, help="NMS IoU threshold (predict)")
    args = parser.parse_args()

    model = YOLO(args.model)

    if args.mode == "val":
        if not args.data:
            raise ValueError("val mode requires --data=path/to/data.yaml")
        # lower conf for comprehensive evaluation
        results = model.val(
            data=args.data,
            imgsz=args.imgsz,
            device=args.device,
            batch=args.batch,
            conf=0.001,
            save_json=args.save_json,
            project=args.project,
            name=args.name,
        )
        print("\n=== Val Metrics ===")
        print(results)  # Ultralytics returns a dict/object with P/R/mAP
    else:  # predict
        if not args.source:
            raise ValueError("predict mode requires --source=path/to/image_or_video")
        model.predict(
            source=args.source,
            imgsz=args.imgsz,
            conf=args.conf,
            iou=args.iou,
            device=args.device,
            project=args.project,
            name=args.name,
            save=True,
            save_txt=args.save_txt,
            save_conf=args.save_conf,
        )
        print("\nPrediction completed. Results saved at:", f"{args.project}/{args.name}")
        if args.save_txt:
            print("Predicted labels (YOLO txt) at:", f"{args.project}/{args.name}/labels")


if __name__ == "__main__":
    main()