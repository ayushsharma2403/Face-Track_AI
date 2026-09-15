# Face-Track AI 👁️

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org/)

**Face-Track AI** is a smart, automated face-recognition attendance monitoring system. Designed with a modern neumorphic & glassmorphic web dashboard powered by Flask, it streamlines student registration, real-time face tracking, automatic attendance logging, dual-role authentication, and automated email reporting with CSV attachments.

---

## ✨ Features

- **Dual-Role Authentication (Admin vs. User Mode)**:
  - **Admin Mode**: Password-protected access (`ADMIN_PASSWORD`). Full control over student enrollment, model training, email reports, data purge, and manual attendance.
  - **User Mode**: Credential-free entry dedicated exclusively to taking attendance. All administrative actions (CSV download, registration, data reset) are hidden and restricted with 403 API protection.
- **Continuous Auto-Attendance Scanning**:
  - Automatically scans optical camera feed in User mode and marks attendance when face match confidence is **> 80%**. Includes duplicate cooldown and live HUD biometric confirmation card.
- **Real-Time Zero-Lag Camera Streaming**: Optimized low-latency MJPEG video streaming using threaded frames and browser camera integration.
- **Student Enrollment & Image Training**: Capture and store student profile snapshots mapped to their student name and university roll number.
- **Automated Attendance Logging**: Generates timestamped logs into local CSV files (`attendance.csv` and `StudentDetails.csv`) and Supabase Cloud storage.
- **Automated Email Reports**: Instantly dispatches attendance summaries formatted as HTML tables with the full CSV report attached directly to administrator / faculty inboxes via secure Gmail SMTP (SSL).
- **Glassmorphic & Neumorphic UI**: Sleek, responsive, dark & ambient dashboard with interactive controls, status indicators, dynamic role switcher, and micro-animations.

---

## 🛠️ Architecture & Project Structure

```text
Face-Track_AI/
├── static/
│   ├── glass-theme.css        # Glassmorphic UI theme styling
│   ├── scripts.js             # Client-side interaction & auto-scan handlers
│   └── style.css              # Neumorphic layout & role badge stylesheet
├── templates/
│   ├── index.html             # Main dashboard interface with role switcher modal
│   └── login.html             # Dual-role authentication page (Admin/User selector)
├── trained_images/            # Training image dataset repository
├── .env.example               # Environment variables template
├── .gitignore                 # Standard Python / Flask / OS gitignore
├── app.py                     # Primary Flask backend, auth session management & REST APIs
├── haarcascade_frontalface_default.xml # Pre-trained OpenCV Haar Cascade model
├── README.md                  # Project documentation & guides
├── requirements.txt           # Python dependency declarations
└── run_app.py                 # Application launcher script
```

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/ayushsharma2403/Face-Track_AI.git
cd Face-Track_AI
```

### 2. Create and Activate a Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and configure your credentials:
```bash
cp .env.example .env
```

Edit `.env`:
```ini
# Gmail Sender Credentials for Email Reports
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_16_digit_app_password

# Admin Authentication Password (Default: admin123)
ADMIN_PASSWORD=admin123
```
> **Note**: For Gmail, generate a 16-character [Google App Password](https://myaccount.google.com/apppasswords) under Security settings (2-Factor Authentication required).

---

## 💻 Running the Application

Start the Flask server:
```bash
python app.py
```
Or use the launcher:
```bash
python run_app.py
```

Once running, navigate to `http://localhost:5000` in your web browser.

- **Admin Login**: Select **Admin**, enter your configured password (`admin123` by default) to unlock full system capabilities.
- **User Mode**: Select **User** for instant access to automatic face recognition attendance.

---

## 🔒 Security Best Practices

- **Never commit `.env`**: Always store sensitive credentials such as SMTP app passwords and admin credentials in `.env`, which is strictly excluded via `.gitignore`.
- **API Role Enforcement**: Admin-only routes (`/train_image`, `/send_email`, `/delete_data`, `/download_attendance`) strictly enforce session role authorization, returning HTTP 403 Forbidden for unauthorized requests.
- **Session & Data Cleanup**: Built-in endpoints allow clearing local training datasets and test CSV records securely.

