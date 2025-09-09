import shutil
from ultralytics import YOLO

# Load the pretrained YOLOv8n model
model = YOLO("yolov8n.pt")

# Train for 50 epochs and save a checkpoint every 10 epochs
results = model.train(
    data="datasets/data.yaml",
    epochs=50,
    imgsz=640,
    batch=16,
    workers=4,
    project="runs",
    name="yolov8n_custom",
    save_period=10,
    exist_ok=True
)

# Get the path to the best weights
best_model_path = model.ckpt_path  # path to the last checkpoint used internally

# But YOLO saves the best weights here:
best_model_path = "runs/detect/yolov8n_custom/weights/best.pt"

# Copy the best model to project directory
shutil.copy(best_model_path, "./yolov8n_trained.pt")
print("Saved trained model as yolov8n_trained.pt in project directory")

# (Optional) Evaluate
metrics = model.val()
print(metrics)
