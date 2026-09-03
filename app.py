from flask import Flask, render_template, request, jsonify, Response
import os
# Remove direct OpenCV import to avoid NumPy/OpenCV ABI import failures.
# Camera and OpenCV features are disabled in this workspace; UI will
# show a placeholder instead.
cv2 = None
import csv
import time
import smtplib
import html
import threading
from email.message import EmailMessage
from io import BytesIO
import numpy as np

def load_env_file():
    env_paths = [os.path.join(os.path.dirname(__file__), '.env'), os.path.expanduser('~/.env')]
    for path in env_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            os.environ[k.strip()] = v.strip().strip("'\"")
            except Exception:
                pass

load_env_file()

app = Flask(__name__)
TRAINED_IMAGES_PATH = 'trained_images'
ATTENDANCE_PATH = 'attendance.csv'
STUDENT_DETAILS_PATH = 'StudentDetails.csv'
SENDER_EMAIL = os.getenv('SENDER_EMAIL', '')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', '')

os.makedirs(TRAINED_IMAGES_PATH, exist_ok=True)
video_capture = None
latest_frame = None
camera_lock = threading.Lock()
face_cascade = None
cv2_available = False

def get_camera():
    raise RuntimeError("Camera functionality is disabled in this build.")

def release_camera():
    global video_capture
    with camera_lock:
        if video_capture is not None:
            video_capture.release()
            video_capture = None
    if cv2_available:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

def capture_frame():
    global latest_frame

    with camera_lock:
        if latest_frame is not None:
            return True, latest_frame.copy()

        if not cv2_available:
            return False, None
        cap = get_camera()
        try:
            return cap.read()
        finally:
            cap.release()

def detect_faces(frame):
    # Face detection disabled when camera/OpenCV is not available
    return []

def save_student_data(name, roll, email, frame):
    if not cv2_available:
        raise RuntimeError('Saving images is disabled because OpenCV is not available.')
    # Save the image with the student's face
    filename = f"{name}--{roll}.jpg"
    filepath = os.path.join(TRAINED_IMAGES_PATH, filename)
    cv2.imwrite(filepath, frame)
    
    # Save student details to CSV
    file_exists = os.path.exists(STUDENT_DETAILS_PATH)
    with open(STUDENT_DETAILS_PATH, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Name', 'Roll', 'Email'])
        writer.writerow([name, roll, email])
    
    return True

@app.route('/')
def index():
    return render_template('index.html')

def gen_frames():
    global video_capture, latest_frame
    try:
        if not cv2_available:
            print("gen_frames: OpenCV not available, streaming disabled.")
            return

        while True:
            with camera_lock:
                if video_capture is None:
                    video_capture = get_camera()
                success, frame = video_capture.read()

            if not success:
                break
            else:
                latest_frame = frame.copy()

                # Detect faces in the frame
                faces = detect_faces(frame)
                
                # Draw rectangles around the faces
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    except Exception as e:
        print(f"Error in gen_frames: {e}")
    finally:
        if cv2_available:
            release_camera()

@app.route('/video_feed')
def video_feed():
    # Return a simple SVG placeholder so the UI still shows an image
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">
    <rect width="100%" height="100%" fill="#07080c" />
    <g fill="#ffffff" fill-opacity="0.04">
      <rect x="12" y="12" width="616" height="336" rx="12" />
    </g>
    <text x="50%" y="50%" fill="#8a99ad" font-size="18" text-anchor="middle" dominant-baseline="middle">Camera disabled — placeholder</text>
</svg>'''
    resp = make_response(svg)
    resp.headers['Content-Type'] = 'image/svg+xml'
    return resp

@app.route('/release_camera', methods=['POST'])
def release_camera_route():
    release_camera()
    return jsonify({'status': 'success', 'message': 'Camera released.'})

@app.route('/train_image', methods=['POST'])
def train_image():
    if 'student_name' not in request.form or 'aktu_roll_number' not in request.form:
        return jsonify({'status': 'error', 'message': 'Name and Roll Number are required.'})
    
    name = request.form['student_name']
    roll = request.form['aktu_roll_number']
    email = request.form.get('email', '')

    if not name or not roll:
        return jsonify({'status': 'error', 'message': 'Name and Roll Number are required.'})

    # Check if roll number already exists
    if os.path.exists(STUDENT_DETAILS_PATH):
        with open(STUDENT_DETAILS_PATH, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            for row in reader:
                if len(row) > 1 and row[1] == roll:
                    return jsonify({'status': 'error', 'message': 'This Roll Number already exists.'})

    # Camera/training disabled in this environment
    return jsonify({'status': 'error', 'message': 'Camera/training disabled in this environment.'})

@app.route('/take_attendance', methods=['POST'])
def take_attendance():
    # Camera/attendance disabled in this environment
    return jsonify({'status': 'error', 'message': 'Camera/attendance disabled in this environment.'})

@app.route('/send_email', methods=['POST'])
def send_email():
    try:
        if 'email' not in request.form:
            return jsonify({'status': 'error', 'message': 'Email address is required.'})
        
        if not os.path.exists(ATTENDANCE_PATH):
            return jsonify({'status': 'error', 'message': 'No attendance records found.'})
        
        msg = EmailMessage()
        msg['Subject'] = 'Attendance Report'
        msg['From'] = SENDER_EMAIL
        msg['To'] = request.form['email']
        
        # Create HTML content for the email
        html_content = '''
        <html>
            <body>
                <h2>Attendance Report</h2>
                <table border="1" cellpadding="5" cellspacing="0">
                    <tr>
                        <th>Name</th>
                        <th>Roll</th>
                        <th>Timestamp</th>
                    </tr>
        '''
        
        # Read attendance data
        with open(ATTENDANCE_PATH, 'r', newline='') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            for row in reader:
                if len(row) >= 3:
                    html_content += f'''
                    <tr>
                        <td>{html.escape(row[0])}</td>
                        <td>{html.escape(row[1])}</td>
                        <td>{html.escape(row[2])}</td>
                    </tr>
                    '''
        
        html_content += '''
                </table>
            </body>
        </html>
        '''
        
        # Set email content
        msg.set_content('Please find attached the attendance report.')
        msg.add_alternative(html_content, subtype='html')

        # Attach the CSV file
        with open(ATTENDANCE_PATH, 'rb') as f:
            file_data = f.read()
            msg.add_attachment(
                file_data,
                maintype='text',
                subtype='csv',
                filename='attendance.csv'
            )

        # Send the email
        sender_email = os.getenv('SENDER_EMAIL', SENDER_EMAIL)
        sender_pass = os.getenv('SENDER_PASSWORD', SENDER_PASSWORD).replace(" ", "").strip()

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_pass)
            smtp.send_message(msg)
        
        return jsonify({'status': 'success', 'message': f'Email sent successfully to {request.form["email"]}'})
        
    except smtplib.SMTPAuthenticationError:
        return jsonify({
            'status': 'error', 
            'message': 'Gmail Auth Failed (535): Invalid App Password. Please generate a 16-character App Password at https://myaccount.google.com/apppasswords and set SENDER_PASSWORD in .env'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to send email: {str(e)}'})

@app.route('/delete_data', methods=['POST'])
def delete_data():
    try:
        # Delete attendance file if it exists
        if os.path.exists(ATTENDANCE_PATH):
            os.remove(ATTENDANCE_PATH)
            
        # Delete student details file if it exists
        if os.path.exists(STUDENT_DETAILS_PATH):
            os.remove(STUDENT_DETAILS_PATH)
        
        # Delete all images in the trained_images directory
        if os.path.exists(TRAINED_IMAGES_PATH):
            for file in os.listdir(TRAINED_IMAGES_PATH):
                file_path = os.path.join(TRAINED_IMAGES_PATH, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f'Error deleting {file_path}: {e}')
        
        return jsonify({
            'status': 'success', 
            'message': 'All data has been deleted successfully.'
        })
    except Exception as e:
        return jsonify({
            'status': 'error', 
            'message': f'Error deleting data: {str(e)}'
        })

if __name__ == '__main__':
    # Create necessary directories if they don't exist
    os.makedirs(TRAINED_IMAGES_PATH, exist_ok=True)
    
    # Face detection and camera initialization disabled in this build.
    face_cascade = None
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)
