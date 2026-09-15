# Free Deployment Guide for Face-Track AI 🌐

To deploy **Face-Track AI** for **100% free**, you have 3 practical options depending on how you plan to use the physical camera:

---

## 🎯 Comparison of Free Deployment Options

| Deployment Option | Camera Support | Persistence | Setup Time | Best For |
| :--- | :--- | :--- | :--- | :--- |
| **Option A: Cloudflare Tunnel (Recommended)** | 📸 Uses Local Webcam (HD) | Permanent while PC is on | 5 mins | Live Attendance Stations, College/School Labs |
| **Option B: Render.com Free Cloud Hosting** | 🌐 Browser Camera / Client Feed | Free 750 hrs/month | 10 mins | Remote Access, Demo Web App |
| **Option C: Local Network Hosting (Wi-Fi)** | 📸 Direct Local Hardware | Infinite | 2 mins | Local Lab / Classroom Network |

---

## 🚀 Option A: Free Public URL via Cloudflare Tunnel (Recommended)

If you are running the app on a computer with a webcam and want to expose it securely over HTTPS to any device globally for free:

### Step 1: Install Cloudflare Tunnel (`cloudflared`)
Run in PowerShell / CMD:
```bash
winget install Cloudflare.cloudflared
```

### Step 2: Start Your App & Tunnel
1. Run your Flask app:
   ```bash
   python run_app.py
   ```
2. In a separate terminal window, start a tunnel:
   ```bash
   cloudflared tunnel --url http://127.0.0.1:5000
   ```
3. Cloudflare will output a free, secure `https://xxx.trycloudflare.com` URL.  
   Anyone with this link can open the dashboard, log in as Admin or User, and view attendance.

---

## ☁️ Option B: Free Cloud Hosting on Render.com

To host the Flask app on **Render.com** cloud servers for free:

### Step 1: Add `gunicorn` to `requirements.txt`
```text
gunicorn>=21.2.0
```

### Step 2: Create a `Procfile`
Create a file named `Procfile` in the project root:
```text
web: gunicorn app:app --workers 1 --threads 4 --timeout 120
```

### Step 3: Deploy on Render.com
1. Go to [Render.com](https://render.com) and create a free account.
2. Click **New +** -> **Web Service**.
3. Select your GitHub repository: `ayushsharma2403/Face-Track_AI`.
4. Config:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --workers 1 --threads 4`
5. Add Environment Variables under **Environment**:
   - `SENDER_EMAIL` = `your_email@gmail.com`
   - `SENDER_PASSWORD` = `your_app_password`
   - `ADMIN_PASSWORD` = `admin123`
6. Click **Create Web Service**. Your app will be live at `https://face-track-ai.onrender.com`!

---

## 📱 Option C: Local Network Hosting (Wi-Fi)

To access Face-Track AI from any mobile phone or device connected to your same Wi-Fi network:

1. Check your computer's local IP:
   ```cmd
   ipconfig
   ```
   *(Find `IPv4 Address`, e.g. `192.168.1.15`)*
2. Start the server:
   ```bash
   python run_app.py
   ```
3. Open `http://192.168.1.15:5000` in any browser on your phone/tablet connected to the same Wi-Fi.
