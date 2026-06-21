# flask_app.py - 
# omplete Clean Stateless API
from flask import Flask, request, jsonify, redirect, url_for
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

# In-memory storage dictionary to track temporary OTP records safely without relying on broken browser session cookies
OTP_STORE = {}

def create_jwt_token(username, role):
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

app = Flask(__name__)

# flask_app.py mein is tarah configure karein
# flask_app.py
# flask_app.py mein ye change karein
CORS(app, origins=["https://product-polarization-analyzer-135z9naw0.vercel.app", "https://product-polarization-analyzer.vercel.app"])
SENDER_EMAIL = "arobaarif271@gmail.com"

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
    else:
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        if "role" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'User'")
            conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def send_email(to_email, otp):
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
        return response.status_code == 201
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

@app.route('/')
def home():
    return jsonify({"status": "running", "message": "API Backend is active"}), 200

# Endpoint path standardized with frontend routing syntax
@app.route('/register', methods=['POST'])
def api_register():
    data = request.json or {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'User')
    
    if not all([username, email, password, role]):
        return jsonify({"status": "error", "message": "All fields required"}), 400
    
    if len(username) < 3:
        return jsonify({"status": "error", "message": "Username must be at least 3 characters"}), 400
    
    if '@' not in email or '.' not in email:
        return jsonify({"status": "error", "message": "Invalid email"}), 400
    
    if len(password) < 6:
        return jsonify({"status": "error", "message": "Password must be at least 6 characters"}), 400
    
    password_hash = hash_password(password)
    conn = sqlite3.connect("users.db")
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

# Endpoint path standardized with frontend routing syntax
@app.route('/login', methods=['POST'])
def api_login():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password required"}), 400
    
    password_hash = hash_password(password)
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, email, role FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return jsonify({"status": "error", "message": "User not found"}), 404
    
    stored_hash, email, role = result
    if stored_hash != password_hash:
        return jsonify({"status": "error", "message": "Invalid password"}), 401
    
    otp = str(random.randint(100000, 999999))
    send_email(email, otp)
    
    # Store OTP details inside the server context cache mapped directly against their unique username identifier
    OTP_STORE[username] = {
        "otp": otp,
        "expires_at": datetime.now() + timedelta(minutes=5),
        "role": role
    }
    
    return jsonify({"status": "success", "message": "OTP sent to your email"}), 200

# Endpoint path standardized with frontend routing syntax
@app.route('/verify_otp', methods=['POST'])
def api_verify_otp():
    data = request.json or {}
    username = data.get('username')
    user_otp = data.get('otp')
    
    if not username or not user_otp:
        return jsonify({"status": "error", "message": "Missing username or OTP token parameter"}), 400
        
    user_record = OTP_STORE.get(username)
    
    if not user_record:
        return jsonify({"status": "error", "message": "No active verification requests found. Please request a new OTP."}), 400
        
    if datetime.now() > user_record["expires_at"]:
        OTP_STORE.pop(username, None)
        return jsonify({"status": "error", "message": "OTP has expired. Please re-authenticate."}), 400
        
    if user_otp != user_record["otp"]:
        return jsonify({"status": "error", "message": "Invalid verification token sequence"}), 400
        
    role = user_record["role"]
    jwt_token = create_jwt_token(username, role)
    
    # Clean up validation token entry
    OTP_STORE.pop(username, None)
    
    return jsonify({
        "status": "success",
        "message": "Authentication validation successful",
        "token": jwt_token,
        "username": username,
        "role": role
    }), 200

@app.route('/api/get-users', methods=['GET'])
def api_get_users():
    # Admin API route returning database rows cleanly as arrays
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, role FROM users")
    users = cursor.fetchall()
    conn.close()
    return jsonify({"status": "success", "users": users}), 200

if __name__ == "__main__":
    ensure_role_column()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))