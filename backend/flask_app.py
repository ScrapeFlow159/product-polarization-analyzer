# flask_app.py - Complete Flask app (2FA)
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_cors import CORS
import sqlite3
import hashlib
import random
import smtplib
import os
import json
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import jwt
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-this-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

def create_jwt_token(username, role):
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

app = Flask(__name__)
# Enable CORS so your Vercel frontend can safely speak to this Railway backend
CORS(app, supports_credentials=True)
app.secret_key = os.getenv("SECRET_KEY", "secretkey123")

SENDER_EMAIL = "arobaarif271@gmail.com"
APP_PASSWORD = "ekrpepzprnyklzry"

def ensure_role_column():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'User'
            )
        ''')
        conn.commit()
        print("✅ Users table created successfully")
    else:
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        if "role" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'User'")
            conn.commit()
            print("✅ 'role' column added to users table")
        else:
            print("ℹ️ 'role' column already exists")
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def send_email(to_email, otp):
    import requests
    import os
    
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": os.getenv("BREVO_API_KEY"),
        "Content-Type": "application/json"
    }
    data = {
        "sender": {"email": SENDER_EMAIL},
        "to": [{"email": to_email}],
        "subject": "Your OTP for Login",
        "htmlContent": f"<p>Your OTP is: <strong>{otp}</strong></p>"
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 201:
            print("✅ Email sent via Brevo")
            return True
        else:
            print(f"❌ Brevo error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False
login_attempts = {}

# ================= FIXED ROUTES =================

@app.route('/')
def home():
    # FIXED: Instead of serving a broken index page, route users straight to the registration template or view
    return redirect(url_for('register'))

@app.route('/index.html')
def serve_index():
    # FIXED: Route index fallback traffic directly to registration as well
    return redirect(url_for('register'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password'].strip()
        role = request.form['role']
        
        errors = []
        if not username:
            errors.append("❌ Username is required")
        if not email:
            errors.append("❌ Email is required")
        if not password:
            errors.append("❌ Password is required")
        if not role:
            errors.append("❌ Role is required")
        
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template('register.html')
        
        if len(username) < 3:
            errors.append("❌ Username must be at least 3 characters")
        if '@' not in email or '.' not in email:
            errors.append("❌ Please enter a valid email address")
        if len(password) < 6:
            errors.append("❌ Password must be at least 6 characters")
        
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template('register.html')
        
        password_hash = hash_password(password)
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (username, email, password_hash, role)
            )
            conn.commit()
            flash("✅ User registered successfully! Please login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("❌ Username already exists!", "danger")
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        if not username or not password:
            flash("❌ Username and password are required", "danger")
            return render_template('login.html')
        
        password_hash = hash_password(password)
        attempts = login_attempts.get(username, {"count": 0, "last_attempt": None})
        if attempts["count"] >= 3:
            flash("Maximum login attempts reached. Try again later.", "danger")
            return render_template('login.html')
        
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, email, role FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            stored_hash, email, role = result
            if stored_hash == password_hash:
                otp = str(random.randint(100000, 999999))
                send_email(email, otp)
                session['otp'] = otp
                session['otp_time'] = datetime.now().isoformat()
                session['username'] = username
                session['role'] = role
                login_attempts[username] = {"count": 0, "last_attempt": None}
                return redirect(url_for('verify_otp'))
            else:
                attempts["count"] += 1
                login_attempts[username] = attempts
                flash(f"Incorrect password! Attempt {attempts['count']}/3", "danger")
        else:
            flash("Username not found!", "danger")
    
    return render_template('login.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        user_otp = request.form['otp']
        otp = session.get('otp')
        otp_time_str = session.get('otp_time')
        
        if not otp or not otp_time_str:
            flash("OTP expired. Please login again.", "danger")
            return render_template('otp.html', expired=True)
        
        otp_time = datetime.fromisoformat(otp_time_str)
        if datetime.now() > otp_time + timedelta(minutes=2):
            flash("OTP expired! Please request a new OTP.", "danger")
            session.pop('otp', None)
            session.pop('otp_time', None)
            return render_template('otp.html', expired=True)
        
        if user_otp == otp:
            flash("Login successful! 🎉", "success")
            session.pop('otp')
            session.pop('otp_time')
            jwt_token = create_jwt_token(session['username'], session['role'])
            session['jwt_token'] = jwt_token
            return redirect(url_for('dashboard', token=jwt_token))
        else:
            flash("Incorrect OTP!", "danger")
    
    return render_template('otp.html', expired=False)

@app.route('/dashboard')
def dashboard():
    username = session.get('username')
    role = session.get('role')
    jwt_token = session.get('jwt_token', '')
    if not username:
        # FIXED: Protection logic. If someone isn't logged in, don't let them see the dashboard!
        return redirect(url_for('register'))
    return render_template('dashboard.html', username=username, role=role, jwt_token=jwt_token)

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for('login'))

# Admin routes
@app.route('/admin/manage-users')
def admin_manage_users():
    username = session.get('username')
    role = session.get('role')
    if role != 'Admin':
        return redirect(url_for('dashboard'))
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, role FROM users")
    users = cursor.fetchall()
    conn.close()
    return render_template('admin_users.html', users=users, username=username)

@app.route('/admin/delete-user/<int:user_id>')
def admin_delete_user(user_id):
    role = session.get('role')
    if role != 'Admin':
        return redirect(url_for('dashboard'))
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash("User deleted successfully!", "success")
    return redirect(url_for('admin_manage_users'))

if __name__ == "__main__":
    ensure_role_column()
    app.run(debug=True)