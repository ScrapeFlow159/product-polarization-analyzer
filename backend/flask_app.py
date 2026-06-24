# flask_app.py - Complete Updated Version with Database OTP Storage

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import hashlib
import random
import os
import requests
from datetime import datetime, timedelta
import jwt
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = "secretkey123secretkey123secretkey123"
ALGORITHM = os.getenv("ALGORITHM", "HS256")

app = Flask(__name__)

# CORS configuration
CORS(app, origins=[
    "https://product-polarization-analyzer-135z9naw0.vercel.app",
    "https://product-polarization-analyzer.vercel.app",
    "*"
])

SENDER_EMAIL = "arobaarif271@gmail.com"

# ========== DATABASE FUNCTIONS ==========

def get_db_connection():
    """Get database connection with WAL mode"""
    conn = sqlite3.connect("users.db", timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn

def ensure_otp_table():
    """Create OTP table if not exists"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS otp_store (
            username TEXT PRIMARY KEY,
            otp TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            role TEXT DEFAULT 'User',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ OTP table ensured")

def ensure_role_column():
    """Create users table if not exists"""
    conn = get_db_connection()
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
    else:
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        if "role" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'User'")
            conn.commit()
    conn.close()
    print("✅ Users table ensured")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def send_email(to_email, otp):
    """Send OTP via Brevo API"""
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": os.getenv("BREVO_API_KEY"),
        "Content-Type": "application/json"
    }
    data = {
        "sender": {"email": SENDER_EMAIL},
        "to": [{"email": to_email}],
        "subject": "Your OTP for Login",
        "htmlContent": f"<p>Your OTP is: <strong>{otp}</strong></p><p>This OTP will expire in 10 minutes.</p>"
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 201:
            print(f"✅ Email sent to {to_email}")
            return True
        else:
            print(f"❌ Email failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

def create_jwt_token(username, role):
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# ========== ENDPOINTS ==========

@app.route('/')
def home():
    return jsonify({"status": "running", "message": "API Backend is active"}), 200

@app.route('/register', methods=['POST'])
def api_register():
    data = request.json or {}
    username = data.get('username', '').strip().lower()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'User')
    
    if not all([username, email, password]):
        return jsonify({"status": "error", "message": "All fields required"}), 400
    
    if len(username) < 3:
        return jsonify({"status": "error", "message": "Username must be at least 3 characters"}), 400
    
    if '@' not in email or '.' not in email:
        return jsonify({"status": "error", "message": "Invalid email"}), 400
    
    if len(password) < 6:
        return jsonify({"status": "error", "message": "Password must be at least 6 characters"}), 400
    
    password_hash = hash_password(password)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (username, email, password_hash, role)
        )
        conn.commit()
        return jsonify({"status": "success", "message": "User registered successfully"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"status": "error", "message": "Username already exists"}), 400
    finally:
        conn.close()

@app.route('/login', methods=['POST'])
def api_login():
    data = request.json or {}
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password required"}), 400
    
    password_hash = hash_password(password)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, email, role FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return jsonify({"status": "error", "message": "User not found"}), 404
    
    stored_hash = result['password_hash']
    email = result['email']
    role = result['role']
    
    if stored_hash != password_hash:
        return jsonify({"status": "error", "message": "Invalid password"}), 401
    
    # ✅ Check if OTP already exists and not expired
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT otp, expires_at FROM otp_store WHERE username = ?",
        (username,)
    )
    existing = cursor.fetchone()
    conn.close()
    
    if existing:
        expires_at = datetime.strptime(existing['expires_at'], '%Y-%m-%d %H:%M:%S.%f')
        if datetime.utcnow() < expires_at:
            return jsonify({
                "status": "success", 
                "message": "OTP already sent to your email. Please check your inbox."
            }), 200
    
    # ✅ Generate new OTP
    otp = str(random.randint(100000, 999999))
    email_sent = send_email(email, otp)
    
    if not email_sent:
        return jsonify({"status": "error", "message": "Failed to send OTP email"}), 500
    
    # ✅ Store OTP in database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO otp_store (username, otp, expires_at, role) VALUES (?, ?, ?, ?)",
        (username, otp, str(datetime.utcnow() + timedelta(minutes=10)), role)
    )
    conn.commit()
    conn.close()
    
    print(f"🔑 NEW OTP for {username}: {otp}")
    
    return jsonify({
        "status": "success", 
        "message": "OTP sent to your email"
    }), 200

@app.route('/verify_otp', methods=['POST'])
def api_verify_otp():
    data = request.json or {}
    username = data.get('username', '').strip().lower()
    user_otp = data.get('otp', '').strip()
    
    if not username or not user_otp:
        return jsonify({"status": "error", "message": "Username and OTP required"}), 400
    
    # ✅ Debug log
    print(f"🔍 Verifying OTP for: {username}")
    print(f"   Entered OTP: {user_otp}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT otp, expires_at, role FROM otp_store WHERE username = ?",
        (username,)
    )
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        print(f"❌ No OTP found for {username}")
        return jsonify({
            "status": "error", 
            "message": "No OTP found. Please request a new OTP."
        }), 400
    
    stored_otp = result['otp']
    expires_at = datetime.strptime(result['expires_at'], '%Y-%m-%d %H:%M:%S.%f')
    role = result['role']
    
    print(f"   Stored OTP: {stored_otp}")
    print(f"   Expires at: {expires_at}")
    
    if datetime.utcnow() > expires_at:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM otp_store WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        return jsonify({
            "status": "error", 
            "message": "OTP has expired. Please request a new OTP."
        }), 400
    
    if user_otp != stored_otp:
        return jsonify({
            "status": "error", 
            "message": "Invalid OTP. Please try again."
        }), 400
    
    # ✅ OTP verified - delete from database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM otp_store WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    
    # ✅ Generate JWT token
    jwt_token = create_jwt_token(username, role)
    
    print(f"✅ OTP verified for {username}")
    
    return jsonify({
        "status": "success",
        "message": "OTP verified successfully",
        "token": jwt_token,
        "username": username,
        "role": role
    }), 200

@app.route('/resend_otp', methods=['POST'])
def api_resend_otp():
    data = request.json or {}
    username = data.get('username', '').strip().lower()
    
    if not username:
        return jsonify({"status": "error", "message": "Username required"}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email, role FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return jsonify({"status": "error", "message": "User not found"}), 404
    
    email = result['email']
    role = result['role']
    
    # ✅ Delete old OTP
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM otp_store WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    
    # ✅ Generate new OTP
    otp = str(random.randint(100000, 999999))
    send_email(email, otp)
    
    # ✅ Store new OTP
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO otp_store (username, otp, expires_at, role) VALUES (?, ?, ?, ?)",
        (username, otp, str(datetime.utcnow() + timedelta(minutes=10)), role)
    )
    conn.commit()
    conn.close()
    
    print(f"🔄 RESEND OTP for {username}: {otp}")
    
    return jsonify({
        "status": "success", 
        "message": "New OTP sent to your email"
    }), 200

@app.route('/api/get-users', methods=['GET'])
def api_get_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, role FROM users")
    users = cursor.fetchall()
    conn.close()
    return jsonify({"status": "success", "users": [dict(u) for u in users]}), 200

# ========== INITIALIZATION ==========

# Ensure tables exist
ensure_role_column()
ensure_otp_table()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))