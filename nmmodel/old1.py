# NNMODEL/old1.py
import sys
from pathlib import Path
from ultralytics import YOLO
import cv2
import json

def run_inference(image_path: str, shelf_number: str = "A1"):
    # Load model
    base_dir = Path(__file__).resolve().parent
    model_path = base_dir / "best.pt"

    # Run inference
    model = YOLO(str(model_path))
    results = model(image_path)[0]

    # Load original image
    image = cv2.imread(image_path)
    if image is None:
        raise Exception("Image not found:", image_path)

    height, width = image.shape[:2]
    total_area = width * height
    empty_area = 0
    item_classes = set()

    for box in results.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        conf = float(box.conf[0])
        cls_id = int(box.cls[0])
        class_name = model.names[cls_id]

        if class_name.lower() == "empty":
            area = (x2 - x1) * (y2 - y1)
            empty_area += area
        else:
            item_classes.add(class_name)
            label = f"{class_name} ({conf*100:.1f}%)"
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(image, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    empty_percentage = (empty_area / total_area) * 100
    cv2.putText(image, f"Empty: {empty_percentage:.2f}%", (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Save to outputs/
    outputs_dir = Path("static/outputs")
    outputs_dir.mkdir(parents=True, exist_ok=True)

    output_data = {
        "shelf_number": shelf_number,
        "empty_percentage": round(empty_percentage, 2),
        "items_detected": sorted(list(item_classes)) if item_classes else []
    }

    with open(outputs_dir / "output.json", "w") as f:
        json.dump(output_data, f, indent=4)

    cv2.imwrite(str(outputs_dir / "output.jpg"), image)

if __name__ == "__main__":
    image_path = sys.argv[1]  # From FastAPI
    shelf_number = sys.argv[2] if len(sys.argv) > 2 else "A1"
    run_inference(image_path, shelf_number)
