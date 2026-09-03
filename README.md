# Face-Track AI 👁️

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**Face-Track AI** is a smart, automated face-recognition attendance monitoring system. Designed with a modern, glassmorphic web dashboard powered by Flask, it streamlines student registration, real-time face tracking, attendance logging, and automated email reporting with CSV attachments.

---

## ✨ Features

- **Real-time Face Detection & Recognition**: Utilizes OpenCV Haar Cascade classifiers for robust facial landmark detection.
- **Student Enrollment & Image Training**: Capture and store student profile snapshots mapped to their student name and university roll number.
- **Automated Attendance Logging**: Generates timestamped logs into structured CSV records (`attendance.csv` and `StudentDetails.csv`).
- **Automated Email Reports**: Instantly dispatches attendance summaries formatted as HTML tables with the full CSV report attached directly to administrator / faculty inboxes via secure Gmail SMTP (SSL).
- **Glassmorphic UI**: Sleek, responsive, dark-mode dashboard with interactive controls, status indicators, and micro-animations.

---

## 🛠️ Architecture & Project Structure

```text
Face-Track_AI/
├── static/
│   ├── clg-logo.JPG           # Organization / University branding
│   ├── glass-theme.css        # Glassmorphic UI theme styling
│   ├── scripts.js             # Client-side asynchronous interaction handlers
│   └── style.css              # Core responsive layout stylesheet
├── templates/
│   └── index.html             # Main dashboard frontend interface
├── trained_images/            # Training image dataset repository (.gitkeep)
├── .env.example               # Environment variables template
├── .gitignore                 # Standard Python / Flask / OS gitignore
├── app.py                     # Primary Flask backend & REST API server
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
Copy `.env.example` to `.env` and fill in your Gmail SMTP credentials:
```bash
cp .env.example .env
```

Edit `.env`:
```ini
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_16_digit_app_password
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

---

## 🔒 Security Best Practices

- **Never commit `.env`**: Always store sensitive credentials such as email addresses and SMTP app passwords in `.env`, which is strictly excluded via `.gitignore`.
- **Session & Data Cleanup**: Built-in endpoints allow clearing local training datasets and test CSV records securely.

---

## 📄 License

This project is licensed under the MIT License.
