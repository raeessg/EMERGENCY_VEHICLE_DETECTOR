import os
import uuid
import logging
import subprocess
from flask import Flask, request, jsonify, send_from_directory, url_for, Response
from flask_cors import CORS
from ultralytics import YOLO
import cv2

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "output"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

MODEL_PATH = "best.pt"
model = YOLO(MODEL_PATH)
CONFIDENCE_THRESHOLD = 0.25
EMERGENCY_CLASSES = {"ambulance"}

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.config['OUTPUT_FOLDER'] = os.path.join(app.root_path, OUTPUT_DIR)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def process_video(input_path, output_path):
    logger.info(f"Processing video: {input_path}")
    cap = cv2.VideoCapture(input_path)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    emergency_detected = False
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        results = model(frame, conf=CONFIDENCE_THRESHOLD)
        boxes = results[0].boxes
        keep_indices = [
            i for i, cls_id in enumerate(boxes.cls.cpu().numpy())
            if results[0].names[int(cls_id)].lower() in EMERGENCY_CLASSES
        ]
        if keep_indices:
            emergency_detected = True
            filtered_results = results[0][keep_indices]
            annotated = filtered_results.plot()
        else:
            annotated = frame
        out.write(annotated)
        frame_count += 1

    cap.release()
    out.release()
    logger.info(f"Processed {frame_count} frames. Emergency detected: {emergency_detected}")
    return emergency_detected

def make_web_ready(input_path, output_path):
    cmd = [
        "ffmpeg", "-y", "-i", input_path, "-c:v", "libx264",
        "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "23",
        "-movflags", "+faststart", output_path
    ]
    logger.info(f"Running ffmpeg: {' '.join(cmd)}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        logger.error(f"FFmpeg error: {result.stderr.decode()}")
        raise Exception("FFmpeg conversion failed")

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route("/detect", methods=["POST"])
def detect():
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    file = request.files["video"]
    uid = uuid.uuid4().hex
    safe_in = f"input_{uid}.mp4"
    safe_out_raw = f"processed_raw_{uid}.mp4"
    safe_out_final = f"processed_{uid}.mp4"

    in_path = os.path.join(UPLOAD_DIR, safe_in)
    raw_out_path = os.path.join(OUTPUT_DIR, safe_out_raw)
    final_out_path = os.path.join(OUTPUT_DIR, safe_out_final)

    file.save(in_path)
    logger.info(f"Uploaded video saved: {in_path}")

    # Process video
    emergency_detected = process_video(in_path, raw_out_path)
    make_web_ready(raw_out_path, final_out_path)

    # Cleanup
    # for path in (raw_out_path, in_path):
    #     if os.path.exists(path):
    #         os.remove(path)

    # Build an absolute URL (safe for frontend)
    output_url = url_for('serve_output', filename=safe_out_final, _external=True)
    logger.info(f"Returning processed video URL: {output_url}")

    return jsonify({
        "file_type": "video",
        "output_video_url": output_url,
        "emergency_detected": emergency_detected
    })

# Serve processed videos with range support
@app.route('/output/<path:filename>')
def serve_output(filename):
    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    range_header = request.headers.get('Range')
    if not range_header:
        # No Range header → return full file
        return send_from_directory(app.config['OUTPUT_FOLDER'], filename, mimetype='video/mp4')

    # Handle partial content (Range requests)
    size = os.path.getsize(file_path)
    byte1, byte2 = 0, None
    m = range_header.replace('bytes=', '').split('-')
    if m[0]:
        byte1 = int(m[0])
    if len(m) > 1 and m[1]:
        byte2 = int(m[1])

    length = size - byte1 if byte2 is None else byte2 - byte1 + 1
    with open(file_path, 'rb') as f:
        f.seek(byte1)
        data = f.read(length)

    rv = Response(data, 206, mimetype='video/mp4', direct_passthrough=True)
    rv.headers.add('Content-Range', f'bytes {byte1}-{byte1 + length - 1}/{size}')
    rv.headers.add('Accept-Ranges', 'bytes')
    rv.headers.add('Content-Length', str(length))  # 🔹 Required for some browsers
    return rv


# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=False, threaded=True, host="0.0.0.0", port=5000)
