import sys
import os

# Auto-detect and delegate to project virtual environment if needed
def _auto_venv():
    try:
        import flask
        import cv2
        import numpy
    except (ImportError, AttributeError):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base_dir, '.venv_cam', 'Scripts', 'python.exe'),
            os.path.join(base_dir, '.venv', 'Scripts', 'python.exe')
        ]
        for exe in candidates:
            if os.path.exists(exe):
                print(f"[Auto-Launcher] Redirecting to virtual environment Python: {exe}")
                os.execv(exe, [exe] + sys.argv)

_auto_venv()

from flask import Flask, render_template, request, jsonify, Response, send_file, make_response
import csv
import time
from datetime import datetime
import smtplib
import html
import threading
import base64
from email.message import EmailMessage
import numpy as np

# Load OpenCV safely
try:
    import cv2
    cv2_available = True
except Exception as e:
    print(f"Warning: OpenCV failed to load: {e}")
    cv2 = None
    cv2_available = False

# Environment variable loader
def load_env_file():
    env_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'),
        os.path.expanduser('~/.env')
    ]
    for path in env_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            os.environ[k.strip()] = v.strip().strip("'\"")
            except Exception:
                pass

load_env_file()

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINED_IMAGES_PATH = os.path.join(BASE_DIR, 'trained_images')
ATTENDANCE_PATH = os.path.join(BASE_DIR, 'attendance.csv')
STUDENT_DETAILS_PATH = os.path.join(BASE_DIR, 'StudentDetails.csv')
CASCADE_PATH = os.path.join(BASE_DIR, 'haarcascade_frontalface_default.xml')

os.makedirs(TRAINED_IMAGES_PATH, exist_ok=True)

# -------------------------------------------------------------------------
# Face Preprocessing & Standardization Helpers (Illumination & Outfit Invariant)
# -------------------------------------------------------------------------
def extract_face_crop(frame, bbox):
    """
    Extracts the facial region strictly without capturing neck, collar, or clothing.
    Adds a subtle 4% margin around the detected box to keep facial boundaries
    intact without including the torso/shoulders where outfit changes occur.
    """
    if frame is None or bbox is None:
        return None
    h_frame, w_frame = frame.shape[:2]
    x, y, w, h = bbox
    pad_x = int(w * 0.04)
    pad_y = int(h * 0.04)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(w_frame, x + w + pad_x)
    y2 = min(h_frame, y + h + pad_y)
    crop = frame[y1:y2, x1:x2]
    return crop if crop.size > 0 else None

def preprocess_face_for_recognition(face_img):
    """
    Standardizes face illumination and dimensions for robust LBPH recognition:
    1. Converts to grayscale if needed.
    2. Resizes to canonical 200x200 dimensions.
    3. Applies CLAHE (Contrast Limited Adaptive Histogram Equalization)
       to equalize local contrast, removing harsh shadows and normalizing dim/bright light.
    4. Applies mild bilateral filtering to suppress camera sensor noise while
       sharpening structural facial edges.
    """
    if face_img is None or face_img.size == 0:
        return None
    try:
        if len(face_img.shape) == 3:
            gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_img

        face_resized = cv2.resize(gray, (200, 200), interpolation=cv2.INTER_AREA)

        # CLAHE (clipLimit=2.2, tileGridSize=(8,8)) neutralizes directional lighting & shadows
        clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
        face_clahe = clahe.apply(face_resized)

        # Bilateral filter removes webcam CMOS sensor noise without softening biometric edge gradients
        face_filtered = cv2.bilateralFilter(face_clahe, d=5, sigmaColor=35, sigmaSpace=35)
        return face_filtered
    except Exception as e:
        print(f"[Preprocess] Error: {e}")
        return None

def augment_face_samples(face_processed):
    """
    Generates synthetic lighting and pose augmentations:
    - Darker gamma (gamma=0.75) for dim room lighting
    - Brighter gamma (gamma=1.35) for strong overhead light
    """
    samples = []
    try:
        # Darker illumination simulation
        inv_gamma_dark = 1.0 / 0.75
        table_dark = np.array([((i / 255.0) ** inv_gamma_dark) * 255 for i in np.arange(0, 256)]).astype("uint8")
        dark_sample = cv2.LUT(face_processed, table_dark)
        samples.append(dark_sample)

        # Brighter illumination simulation
        inv_gamma_bright = 1.0 / 1.35
        table_bright = np.array([((i / 255.0) ** inv_gamma_bright) * 255 for i in np.arange(0, 256)]).astype("uint8")
        bright_sample = cv2.LUT(face_processed, table_bright)
        samples.append(bright_sample)
    except Exception as e:
        print(f"[Augment] Error: {e}")
    return samples

# -------------------------------------------------------------------------
# Face Recognition & LBPH Model Manager
# -------------------------------------------------------------------------
class FaceRecognizerManager:
    def __init__(self):
        self.recognizer = None
        self.label_to_student = {}  # {int_id: {'name': str, 'roll': str}}
        self.is_trained = False
        self.lock = threading.Lock()
        self.init_recognizer()

    def init_recognizer(self):
        if cv2_available and hasattr(cv2, 'face') and hasattr(cv2.face, 'LBPHFaceRecognizer_create'):
            try:
                # LBPH with radius 1, 8 neighbors, 8x8 spatial grid for fine facial texture
                self.recognizer = cv2.face.LBPHFaceRecognizer_create(radius=1, neighbors=8, grid_x=8, grid_y=8)
                self.train_from_storage()
            except Exception as e:
                print(f"[FaceRecognizer] Error initializing LBPH: {e}")
                self.recognizer = None

    def train_from_storage(self):
        with self.lock:
            if not cv2_available or self.recognizer is None:
                return False

            if not os.path.exists(TRAINED_IMAGES_PATH):
                self.is_trained = False
                return False

            image_files = [f for f in os.listdir(TRAINED_IMAGES_PATH) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if not image_files:
                self.is_trained = False
                self.label_to_student.clear()
                return False

            faces = []
            labels = []
            student_to_label = {}
            current_label = 0

            for filename in image_files:
                name_part = os.path.splitext(filename)[0]
                if '--' not in name_part:
                    continue
                parts = name_part.split('--')
                name = parts[0].strip()
                roll = parts[1].strip()

                key = (name, roll)
                if key not in student_to_label:
                    student_to_label[key] = current_label
                    self.label_to_student[current_label] = {'name': name, 'roll': roll}
                    current_label += 1

                label = student_to_label[key]
                img_path = os.path.join(TRAINED_IMAGES_PATH, filename)
                try:
                    img = cv2.imread(img_path)
                    if img is not None:
                        face_proc = preprocess_face_for_recognition(img)
                        if face_proc is not None:
                            faces.append(face_proc)
                            labels.append(label)
                            # Add horizontal flip for lateral lighting/pose symmetry
                            faces.append(cv2.flip(face_proc, 1))
                            labels.append(label)
                except Exception as ex:
                    print(f"[FaceRecognizer] Could not load {img_path}: {ex}")

            if faces and labels:
                try:
                    self.recognizer.train(faces, np.array(labels))
                    self.is_trained = True
                    print(f"[FaceRecognizer] Successfully trained on {len(faces)} samples for {len(student_to_label)} student(s).")
                    return True
                except Exception as e:
                    print(f"[FaceRecognizer] Training error: {e}")
                    self.is_trained = False
                    return False
            else:
                self.is_trained = False
                return False

    def predict(self, face_crop):
        with self.lock:
            if not self.is_trained or self.recognizer is None:
                return None, 999.0, 0
            try:
                face_proc = preprocess_face_for_recognition(face_crop)
                if face_proc is None:
                    return None, 999.0, 0
                label, distance = self.recognizer.predict(face_proc)
                student = self.label_to_student.get(label)
                # Compute confidence percentage (0-100%):
                # distance 40 -> ~76%, distance 60 -> ~64%, distance 80 -> ~52%
                conf_pct = max(0, min(100, int(100.0 - (distance * 0.6))))
                return student, distance, conf_pct
            except Exception as e:
                print(f"[FaceRecognizer] Predict error: {e}")
                return None, 999.0, 0

face_manager = FaceRecognizerManager()

# -------------------------------------------------------------------------
# High-Performance Camera Stream Manager (Zero-Lag + Real-Time Tracking)
# -------------------------------------------------------------------------
class CameraStream:
    def __init__(self):
        self.cap = None
        self.lock = threading.Lock()
        self.latest_frame = None
        self.is_running = False
        self.thread = None
        self.cascade = None
        self.hud_banner_text = ""
        self.hud_banner_expire = 0.0
        self.cached_faces = []
        self.frame_count = 0
        self.load_cascade()

    def load_cascade(self):
        if cv2_available and os.path.exists(CASCADE_PATH):
            try:
                self.cascade = cv2.CascadeClassifier(CASCADE_PATH)
            except Exception as e:
                print(f"[CameraStream] Cascade load error: {e}")
                self.cascade = None

    def _open_camera(self):
        # Prefer DirectShow on Windows to avoid driver delays
        backends = []
        if hasattr(cv2, 'CAP_DSHOW'):
            backends.append((0, cv2.CAP_DSHOW))
            backends.append((1, cv2.CAP_DSHOW))
        backends.append((0, None))
        backends.append((1, None))

        for idx, backend in backends:
            try:
                if backend is not None:
                    cap = cv2.VideoCapture(idx, backend)
                else:
                    cap = cv2.VideoCapture(idx)

                if cap.isOpened():
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        # Set hardware buffer to 1 to eliminate frame lag/queuing
                        try:
                            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        except Exception:
                            pass
                        print(f"[CameraStream] Connected to camera device {idx} (backend={backend}, buffersize=1)")
                        return cap
                    cap.release()
            except Exception:
                pass
        return None

    def start(self):
        with self.lock:
            if self.is_running:
                return
            self.cap = self._open_camera()
            if self.cap is None:
                print("[CameraStream] Warning: No active camera device found.")
                return
            self.is_running = True
            self.thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.thread.start()

    def _capture_loop(self):
        """Dedicated high-speed thread to drain camera frames with zero queuing."""
        while self.is_running:
            if self.cap is None or not self.cap.isOpened():
                time.sleep(0.2)
                continue
            ret, frame = self.cap.read()
            if ret and frame is not None:
                with self.lock:
                    self.latest_frame = frame
            else:
                time.sleep(0.01)

    def get_raw_frame(self, timeout=1.0):
        start_t = time.time()
        while time.time() - start_t < timeout:
            with self.lock:
                if self.latest_frame is not None:
                    return True, self.latest_frame.copy()
            time.sleep(0.01)
        return False, None

    def set_hud_banner(self, text, duration=3.5):
        with self.lock:
            self.hud_banner_text = text
            self.hud_banner_expire = time.time() + duration

    def detect_faces(self, frame):
        """Fast face detection by downscaling 0.5x, achieving 4x-5x speedup."""
        if self.cascade is None or frame is None:
            return []
        try:
            # Downscale frame for fast Haar cascade evaluation
            small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_LINEAR)
            gray_small = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            gray_small = cv2.equalizeHist(gray_small)
            faces_small = self.cascade.detectMultiScale(
                gray_small,
                scaleFactor=1.12,
                minNeighbors=4,
                minSize=(25, 25)
            )
            # Scale coordinates back to full frame
            faces = [(int(x * 2), int(y * 2), int(w * 2), int(h * 2)) for (x, y, w, h) in faces_small]
            return faces
        except Exception as e:
            print(f"[DetectFaces] Error: {e}")
            return []

    def generate_display_frame(self):
        with self.lock:
            if self.latest_frame is None:
                return None
            frame = self.latest_frame.copy()

        self.frame_count += 1
        # Run detection every 2nd frame for smooth 30 FPS fluidity
        if self.frame_count % 2 == 0 or not self.cached_faces:
            self.cached_faces = self.detect_faces(frame)

        faces = self.cached_faces

        for (x, y, w, h) in faces:
            label_text = "FACE DETECTED"
            color = (235, 99, 37) # Electric Blue (BGR)

            if face_manager.is_trained:
                face_crop = extract_face_crop(frame, (x, y, w, h))
                if face_crop is not None:
                    student, dist, conf_pct = face_manager.predict(face_crop)
                    # LBPH distance <= 80.0 is verified match
                    if student is not None and dist <= 80.0:
                        label_text = f"{student['name']} ({student['roll']}) [{conf_pct}%]"
                        color = (128, 220, 16) # Vibrant Emerald (BGR)

            # Sleek bounding box corners
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            corner_len = min(16, max(8, w // 4))
            cv2.line(frame, (x, y), (x + corner_len, y), (255, 255, 255), 3)
            cv2.line(frame, (x, y), (x, y + corner_len), (255, 255, 255), 3)
            cv2.line(frame, (x + w, y), (x + w - corner_len, y), (255, 255, 255), 3)
            cv2.line(frame, (x + w, y), (x + w, y + corner_len), (255, 255, 255), 3)

            # Clean Name tag chip
            tag_w = max(130, len(label_text) * 8 + 16)
            cv2.rectangle(frame, (x, y - 24), (x + tag_w, y), color, -1)
            cv2.putText(frame, label_text, (x + 6, y - 7),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

        # Draw Confirmation Banner if active
        with self.lock:
            if time.time() < self.hud_banner_expire and self.hud_banner_text:
                banner_w = frame.shape[1]
                cv2.rectangle(frame, (0, 0), (banner_w, 42), (255, 255, 255), -1)
                cv2.line(frame, (0, 42), (banner_w, 42), (235, 99, 37), 2)
                cv2.putText(frame, f"[BIOMETRIC VERIFIED] {self.hud_banner_text}",
                            (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (15, 23, 42), 2, cv2.LINE_AA)

        return frame

    def stop(self):
        with self.lock:
            self.is_running = False
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None

camera_stream = CameraStream()

# Start camera on app startup
if cv2_available:
    camera_stream.start()

def frame_to_base64_thumbnail(image, max_dim=160):
    """Encodes a face crop as a base64 JPEG data URL for UI display."""
    try:
        if image is None or image.size == 0:
            return None
        h, w = image.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            image = cv2.resize(image, (int(w * scale), int(h * scale)))
        ret, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if ret:
            b64_str = base64.b64encode(buffer).decode('utf-8')
            return f"data:image/jpeg;base64,{b64_str}"
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
    return None

# -------------------------------------------------------------------------
# Flask Routes
# -------------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

def gen_frames():
    """Generator function yielding smooth 30 FPS JPEG frames for the video feed."""
    target_interval = 1.0 / 30.0 # 33.3 ms per frame
    while True:
        if not cv2_available:
            time.sleep(0.5)
            continue

        start_time = time.time()
        frame = camera_stream.generate_display_frame()
        if frame is None:
            time.sleep(0.015)
            continue

        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            time.sleep(0.01)
            continue

        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        # Dynamically adapt sleep to preserve steady 30 FPS without lag accumulation
        elapsed = time.time() - start_time
        sleep_time = max(0.001, target_interval - elapsed)
        time.sleep(sleep_time)

@app.route('/video_feed')
def video_feed():
    if cv2_available:
        return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

    # SVG Placeholder fallback if cv2 not available
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">
    <rect width="100%" height="100%" fill="#07080c" />
    <text x="50%" y="50%" fill="#00ff9d" font-family="sans-serif" font-size="16" text-anchor="middle">OpenCV unavailable — camera disabled</text>
    </svg>'''
    resp = make_response(svg)
    resp.headers['Content-Type'] = 'image/svg+xml'
    return resp

@app.route('/train_image', methods=['POST'])
def train_image():
    name = request.form.get('student_name', '').strip()
    roll = request.form.get('roll_no', '').strip()
    email = request.form.get('email', '').strip()

    if not name or not roll:
        return jsonify({'status': 'error', 'message': 'Both Student Name and Roll Number are required.'})

    # Validate roll uniqueness in StudentDetails.csv
    if os.path.exists(STUDENT_DETAILS_PATH):
        with open(STUDENT_DETAILS_PATH, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) > 1 and row[1].strip() == roll:
                    return jsonify({'status': 'error', 'message': f'Roll Number {roll} is already registered to {row[0]}.'})

    # Burst capture multiple clean facial crops to capture subtle head angles & expressions
    captured_crops = []
    primary_thumbnail = None

    for i in range(5):
        success, frame = camera_stream.get_raw_frame(timeout=0.6)
        if success and frame is not None:
            faces = camera_stream.detect_faces(frame)
            if len(faces) > 0:
                faces_sorted = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
                # Standardized crop excluding clothing/collars
                face_crop = extract_face_crop(frame, faces_sorted[0])
                if face_crop is not None and face_crop.size > 0:
                    captured_crops.append(face_crop)
                    if primary_thumbnail is None:
                        primary_thumbnail = frame_to_base64_thumbnail(face_crop)
        time.sleep(0.08) # Short burst interval

    if not captured_crops:
        return jsonify({'status': 'error', 'message': 'No face detected in video feed. Please look directly into the camera with good lighting.'})

    # Save primary image (standard format)
    primary_path = os.path.join(TRAINED_IMAGES_PATH, f"{name}--{roll}.jpg")
    cv2.imwrite(primary_path, captured_crops[0])

    # Save multi-sample frames and synthetic lighting augmentations
    for idx, crop in enumerate(captured_crops):
        sample_path = os.path.join(TRAINED_IMAGES_PATH, f"{name}--{roll}--{idx}.jpg")
        cv2.imwrite(sample_path, crop)

        # Generate synthetic illumination samples (dark room + bright room)
        preprocessed = preprocess_face_for_recognition(crop)
        if preprocessed is not None:
            augmented = augment_face_samples(preprocessed)
            if len(augmented) >= 2:
                # augmented[0] is dark gamma, augmented[1] is bright gamma
                cv2.imwrite(os.path.join(TRAINED_IMAGES_PATH, f"{name}--{roll}--{idx}--dark.jpg"), augmented[0])
                cv2.imwrite(os.path.join(TRAINED_IMAGES_PATH, f"{name}--{roll}--{idx}--bright.jpg"), augmented[1])

    # Save to StudentDetails.csv
    file_exists = os.path.exists(STUDENT_DETAILS_PATH)
    with open(STUDENT_DETAILS_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Name', 'Roll', 'Email', 'RegisteredAt'])
        timestamp_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        writer.writerow([name, roll, email, timestamp_now])

    # Re-train LBPH model with new samples and lighting augmentations
    face_manager.train_from_storage()

    # Flash HUD confirmation on video monitor
    camera_stream.set_hud_banner(f"REGISTERED: {name} (ROLL {roll})")

    total_samples = len(captured_crops) * 4 # (original + dark + bright) * 2 horizontal flips
    return jsonify({
        'status': 'success',
        'message': f'Student {name} (Roll: {roll}) registered with {total_samples} illumination-invariant biometric profiles!',
        'student_name': name,
        'roll_number': roll,
        'timestamp': timestamp_now,
        'photo': primary_thumbnail
    })

@app.route('/take_attendance', methods=['POST'])
def take_attendance():
    # Capture frame from live feed
    success, frame = camera_stream.get_raw_frame()
    if not success or frame is None:
        return jsonify({'status': 'error', 'message': 'Camera is not currently capturing frames. Please check connection.'})

    faces = camera_stream.detect_faces(frame)
    if len(faces) == 0:
        return jsonify({'status': 'error', 'message': 'No face detected in video feed. Please face the camera clearly.'})

    if not face_manager.is_trained:
        return jsonify({
            'status': 'error',
            'message': 'No registered students found in the database. Please register a student first using "TRAIN IMAGE".'
        })

    # Pick the largest face
    faces_sorted = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
    face_bbox = faces_sorted[0]

    # Standardized facial crop matching training dimensions
    face_crop = extract_face_crop(frame, face_bbox)
    if face_crop is None or face_crop.size == 0:
        return jsonify({'status': 'error', 'message': 'Could not extract face region from frame.'})

    thumbnail_b64 = frame_to_base64_thumbnail(face_crop)

    student, distance, conf_pct = face_manager.predict(face_crop)

    # LBPH distance threshold <= 80.0 is genuine verified match
    if student is None or distance > 80.0:
        return jsonify({
            'status': 'warning',
            'message': f'Face detected, but biometric confidence was too low ({conf_pct}%, distance {int(distance)}). Please look directly at the camera.',
            'photo': thumbnail_b64
        })

    name = student['name']
    roll = student['roll']
    now = datetime.now()
    today_date = now.strftime('%Y-%m-%d')
    current_time_str = now.strftime('%Y-%m-%d %H:%M:%S')

    # Check if attendance already marked today for this student
    already_marked = False
    existing_time = ""
    if os.path.exists(ATTENDANCE_PATH):
        with open(ATTENDANCE_PATH, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) >= 3:
                    row_roll = row[1].strip()
                    row_time = row[2].strip()
                    if row_roll == roll and row_time.startswith(today_date):
                        already_marked = True
                        existing_time = row_time
                        break

    if already_marked:
        camera_stream.set_hud_banner(f"ALREADY MARKED: {name} (ROLL {roll})")
        return jsonify({
            'status': 'info',
            'already_marked': True,
            'student_name': name,
            'roll_number': roll,
            'timestamp': existing_time,
            'message': f'Attendance was ALREADY recorded for {name} (Roll: {roll}) today at {existing_time}.',
            'photo': thumbnail_b64
        })

    # Record attendance
    file_exists = os.path.exists(ATTENDANCE_PATH)
    with open(ATTENDANCE_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Name', 'Roll', 'Timestamp'])
        writer.writerow([name, roll, current_time_str])

    # Flash HUD confirmation
    camera_stream.set_hud_banner(f"ATTENDANCE MARKED: {name} (ROLL {roll})")

    return jsonify({
        'status': 'success',
        'already_marked': False,
        'student_name': name,
        'roll_number': roll,
        'timestamp': current_time_str,
        'message': f'Attendance confirmed & recorded for {name} (Roll: {roll})!',
        'photo': thumbnail_b64
    })

@app.route('/download_attendance', methods=['GET'])
def download_attendance():
    """Directly download the attendance CSV report."""
    if not os.path.exists(ATTENDANCE_PATH):
        # Create an empty attendance file with headers
        with open(ATTENDANCE_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Name', 'Roll', 'Timestamp'])

    today_str = datetime.now().strftime('%Y-%m-%d')
    return send_file(
        ATTENDANCE_PATH,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'attendance_report_{today_str}.csv'
    )

def save_env_file(email, password):
    """Persist sender credentials to .env file."""
    env_path = os.path.join(BASE_DIR, '.env')
    try:
        content = (
            "# Gmail Sender Credentials for Attendance Email Reports\n"
            f"SENDER_EMAIL={email.strip()}\n"
            f"SENDER_PASSWORD={password.strip()}\n"
        )
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(content)
        os.environ['SENDER_EMAIL'] = email.strip()
        os.environ['SENDER_PASSWORD'] = password.strip()
        return True
    except Exception as e:
        print(f"Error saving .env file: {e}")
        return False

@app.route('/get_email_config', methods=['GET'])
def get_email_config():
    sender_email = os.getenv('SENDER_EMAIL', '').strip()
    sender_password = os.getenv('SENDER_PASSWORD', '').strip()
    has_config = bool(sender_email and sender_password and 'your_email' not in sender_email and 'app_password' not in sender_password)
    return jsonify({
        'configured': has_config,
        'sender_email': sender_email if has_config else ''
    })

@app.route('/send_email', methods=['POST'])
def send_email():
    try:
        import urllib.parse
        recipient_email = request.form.get('email', '').strip()
        if not recipient_email:
            return jsonify({'status': 'error', 'message': 'Recipient email address is required.'})

        # Check for sender credentials passed from UI or environment
        custom_sender = request.form.get('sender_email', '').strip()
        custom_password = request.form.get('sender_password', '').strip()
        save_creds = request.form.get('save_credentials', 'false').lower() == 'true'

        sender_email = custom_sender or os.getenv('SENDER_EMAIL', '').strip()
        sender_password = custom_password or os.getenv('SENDER_PASSWORD', '').strip()

        # If user supplied custom credentials and wants them saved
        if custom_sender and custom_password and save_creds:
            save_env_file(custom_sender, custom_password)

        if not os.path.exists(ATTENDANCE_PATH):
            return jsonify({'status': 'error', 'message': 'No attendance records found yet to send. Please take attendance first.'})

        # Read attendance rows
        rows = []
        with open(ATTENDANCE_PATH, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)
            for r in reader:
                if len(r) >= 3:
                    rows.append(r)

        if not rows:
            return jsonify({'status': 'error', 'message': 'Attendance log is empty. Please take attendance for at least one student before generating a report.'})

        # Construct mailto URL as instant fallback
        body_text = f"Face-Track AI Daily Biometric Attendance Report\nDate: {datetime.now().strftime('%Y-%m-%d')}\n\n"
        body_text += "Name | Roll | Timestamp\n"
        body_text += "----------------------------------------\n"
        for r in rows:
            body_text += f"{r[0]} | {r[1]} | {r[2]}\n"
        body_text += "\nGenerated by Face-Track AI Biometric System."

        mailto_url = f"mailto:{urllib.parse.quote(recipient_email)}?subject={urllib.parse.quote('Face-Track AI Attendance Report')}&body={urllib.parse.quote(body_text)}"

        # Validate SMTP credentials
        if not sender_email or not sender_password or 'your_email' in sender_email or 'app_password' in sender_password:
            return jsonify({
                'status': 'needs_config',
                'message': 'Gmail SMTP sender credentials are not configured. Please enter your Gmail address and 16-character App Password, or click "Open in Email App" to dispatch via your email client.',
                'mailto_url': mailto_url
            })

        msg = EmailMessage()
        msg['Subject'] = f'Attendance Report - {datetime.now().strftime("%Y-%m-%d")}'
        msg['From'] = sender_email
        msg['To'] = recipient_email

        html_content = '''
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 24px; border-radius: 8px; border: 1px solid #e2e8f0;">
                <h2 style="color: #0f172a; margin-top: 0;">Face-Track AI - Daily Attendance Log</h2>
                <p style="color: #475569;">Please find the verified biometric attendance log below:</p>
                <table style="width: 100%; border-collapse: collapse; margin-top: 16px;">
                    <thead>
                        <tr style="background-color: #0f172a; color: #ffffff;">
                            <th style="padding: 10px; text-align: left;">Name</th>
                            <th style="padding: 10px; text-align: left;">Roll Number</th>
                            <th style="padding: 10px; text-align: left;">Timestamp</th>
                        </tr>
                    </thead>
                    <tbody>
        '''
        for r in rows:
            html_content += f'''
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <td style="padding: 8px 10px; color: #1e293b;">{html.escape(r[0])}</td>
                            <td style="padding: 8px 10px; color: #1e293b;">{html.escape(r[1])}</td>
                            <td style="padding: 8px 10px; color: #64748b;">{html.escape(r[2])}</td>
                        </tr>
            '''
        html_content += '''
                    </tbody>
                </table>
                <p style="margin-top: 20px; font-size: 12px; color: #94a3b8;">Generated automatically by Face-Track AI Biometric System.</p>
            </div>
        </body>
        </html>
        '''

        msg.set_content('Please find the attached Face-Track AI attendance report.')
        msg.add_alternative(html_content, subtype='html')

        with open(ATTENDANCE_PATH, 'rb') as f:
            msg.add_attachment(
                f.read(),
                maintype='text',
                subtype='csv',
                filename=f'attendance_{datetime.now().strftime("%Y%m%d")}.csv'
            )

        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=12) as smtp:
            smtp.login(sender_email, sender_password.replace(" ", ""))
            smtp.send_message(msg)

        return jsonify({
            'status': 'success',
            'message': f'Attendance report dispatched successfully to {recipient_email}!',
            'mailto_url': mailto_url
        })

    except smtplib.SMTPAuthenticationError:
        return jsonify({
            'status': 'auth_error',
            'message': 'Gmail Authentication failed (535 Bad Credentials). Google requires 2-Step Verification ON and a 16-character App Password (from https://myaccount.google.com/apppasswords). Alternatively, click "Open in Email App" to send directly.',
            'mailto_url': mailto_url if 'mailto_url' in locals() else None
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to send email: {str(e)}',
            'mailto_url': mailto_url if 'mailto_url' in locals() else None
        })

@app.route('/delete_data', methods=['POST'])
def delete_data():
    try:
        if os.path.exists(ATTENDANCE_PATH):
            os.remove(ATTENDANCE_PATH)
        if os.path.exists(STUDENT_DETAILS_PATH):
            os.remove(STUDENT_DETAILS_PATH)
        if os.path.exists(TRAINED_IMAGES_PATH):
            for file in os.listdir(TRAINED_IMAGES_PATH):
                file_path = os.path.join(TRAINED_IMAGES_PATH, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")

        # Reset model
        face_manager.is_trained = False
        face_manager.label_to_student.clear()
        camera_stream.set_hud_banner("SYSTEM RESET: ALL DATA PURGED", duration=4.0)

        return jsonify({'status': 'success', 'message': 'All attendance records and student biometric training data have been cleared.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error during reset: {str(e)}'})

if __name__ == '__main__':
    print("\n=======================================================")
    print("  Face-Track AI Digital Biometric Attendance Server")
    print("  Local Dashboard: http://127.0.0.1:5000")
    print("=======================================================\n")
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
