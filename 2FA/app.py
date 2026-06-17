from flask import Flask, render_template, request, redirect, url_for, flash, session
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

# Load environment variables
load_dotenv()

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-this-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

def create_jwt_token(username, role):
    """Create JWT token for authenticated user"""
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

app = Flask(__name__)
app.secret_key = "secretkey123"

# --- Gmail settings for OTP ---
SENDER_EMAIL = "arobaarif271@gmail.com"
APP_PASSWORD = "ekrpepzprnyklzry"

# --- Helper functions ---
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
    subject = "Your OTP for Login"
    body = f"Your OTP is: {otp}"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email

    try:
        print("📡 Connecting SMTP...")
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15)
        server.set_debuglevel(1)
        print("🔑 Logging in Gmail...")
        login_response = server.login(SENDER_EMAIL, APP_PASSWORD)
        print("LOGIN RESPONSE:", login_response)
        print("📨 Sending email...")
        send_response = server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        print("SEND RESPONSE:", send_response)
        server.quit()
        print("✅ SMTP transaction completed")
    except Exception as e:
        print("❌ EMAIL ERROR:", str(e))

# --- Track login attempts ---
login_attempts = {}

# --- Routes ---

@app.route('/')
def home():
    return redirect(url_for('register'))

# ================= REGISTER =================
# ================= REGISTER =================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', '')

        # ✅ Complete Validation
        errors = []
        
        # Check if any field is empty
        if not username:
            errors.append("❌ Username is required")
        if not email:
            errors.append("❌ Email is required")
        if not password:
            errors.append("❌ Password is required")
        if not role:
            errors.append("❌ Role is required")
        
        # If any field is empty, show error and return
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template('register.html', username=username, email=email, role=role)
        
        # Username length validation
        if len(username) < 3:
            errors.append("❌ Username must be at least 3 characters")
        elif len(username) > 50:
            errors.append("❌ Username must be less than 50 characters")
        
        # Email validation
        if '@' not in email or '.' not in email:
            errors.append("❌ Please enter a valid email address (example@domain.com)")
        elif len(email) > 100:
            errors.append("❌ Email address is too long")
        
        # Password validation
        if len(password) < 6:
            errors.append("❌ Password must be at least 6 characters")
        elif len(password) > 100:
            errors.append("❌ Password is too long")
        
        # Role validation
        valid_roles = ['User', 'Research Analyst', 'Evaluator', 'Admin']
        if role not in valid_roles:
            errors.append("❌ Please select a valid role")
        
        # If validation errors exist, show them
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template('register.html', username=username, email=email, role=role)

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
            flash("❌ Username already exists! Please choose a different username.", "danger")
        finally:
            conn.close()

    return render_template('register.html')
# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = hash_password(password)
        
        errors = []
        
        if not username:
            errors.append("Username is required")
        if not password:
            errors.append("Password is required")
        
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template('login.html')

        attempts = login_attempts.get(username, {"count": 0, "last_attempt": None})
        if attempts["count"] >= 3:
            flash("Maximum login attempts reached. Try again later.", "danger")
            return render_template('login.html')

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password_hash, email, role FROM users WHERE username = ?",
            (username,)
        )
        result = cursor.fetchone()
        conn.close()

        if result:
            stored_hash, email, role = result

            if stored_hash == password_hash:
                # Generate OTP
                otp = str(random.randint(100000, 999999))
                send_email(email, otp)

                # Store session data
                session['otp'] = otp
                session['otp_time'] = datetime.now().isoformat()
                session['username'] = username
                session['role'] = role

                # Reset attempts
                login_attempts[username] = {"count": 0, "last_attempt": None}

                return redirect(url_for('verify_otp'))

            else:
                attempts["count"] += 1
                attempts["last_attempt"] = datetime.now()
                login_attempts[username] = attempts
                flash(f"Incorrect password! Attempt {attempts['count']}/3", "danger")

        else:
            flash("Username not found!", "danger")

    return render_template('login.html')

# ================= OTP VERIFY =================
@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        user_otp = request.form['otp']
        otp = session.get('otp')
        otp_time_str = session.get('otp_time')

        if not otp or not otp_time_str:
            flash("OTP expired or not found. Please login again.", "danger")
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
            
            # ✅ Generate JWT token after successful OTP verification
            jwt_token = create_jwt_token(session['username'], session['role'])
            session['jwt_token'] = jwt_token
            
            # Pass token to dashboard via URL parameter
            return redirect(url_for('dashboard', token=jwt_token))
        else:
            flash("Incorrect OTP!", "danger")

    return render_template('otp.html', expired=False)

# ================= RESEND OTP =================
@app.route('/resend_otp', methods=['POST'])
def resend_otp():
    username = session.get('username')

    if not username:
        flash("Please login first.", "danger")
        return redirect(url_for('login'))

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()

    if result:
        email = result[0]
        otp = str(random.randint(100000, 999999))
        send_email(email, otp)

        session['otp'] = otp
        session['otp_time'] = datetime.now().isoformat()

        flash("New OTP sent! Please check your email.", "success")
        return redirect(url_for('verify_otp'))

    else:
        flash("User not found. Please login again.", "danger")
        return redirect(url_for('login'))

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    username = session.get('username')
    role = session.get('role')
    jwt_token = session.get('jwt_token', '')

    if not username:
        return redirect(url_for('login'))

    # Pass token to frontend via URL parameter
    return render_template('dashboard.html', 
                          username=username, 
                          role=role, 
                          jwt_token=jwt_token)

# ================= ADMIN PANEL ROUTES =================

@app.route('/admin/manage-users')
def admin_manage_users():
    username = session.get('username')
    role = session.get('role')
    
    if role != 'Admin':
        flash("Access denied. Admin only.", "danger")
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT rowid, username, email, role FROM users")
    users = cursor.fetchall()
    conn.close()
    
    return render_template('admin_users.html', users=users, username=username, role=role)

@app.route('/admin/delete-user/<int:user_id>')
def admin_delete_user(user_id):
    username = session.get('username')
    role = session.get('role')
    
    if role != 'Admin':
        flash("Access denied.", "danger")
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE rowid = ?", (user_id,))
    conn.commit()
    conn.close()
    
    flash("User deleted successfully!", "success")
    return redirect(url_for('admin_manage_users'))

@app.route('/admin/change-role/<int:user_id>', methods=['POST'])
def admin_change_role(user_id):
    username = session.get('username')
    role = session.get('role')
    
    if role != 'Admin':
        flash("Access denied.", "danger")
        return redirect(url_for('dashboard'))
    
    new_role = request.form.get('role')
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE rowid = ?", (new_role, user_id))
    conn.commit()
    conn.close()
    
    flash("User role updated successfully!", "success")
    return redirect(url_for('admin_manage_users'))

@app.route('/admin/system-settings', methods=['GET', 'POST'])
def admin_system_settings():
    username = session.get('username')
    role = session.get('role')
    
    if role != 'Admin':
        flash("Access denied. Admin only.", "danger")
        return redirect(url_for('dashboard'))
    
    settings_file = os.path.join(os.path.dirname(__file__), 'settings.json')
    
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as f:
            settings = json.load(f)
    else:
        settings = {
            "apify_api_key": "",
            "scrape_schedule": "daily",
            "scrape_time": "02:00",
            "max_products_per_category": 100,
            "default_k_value": 3,
            "enable_weekly_scheduler": True,
            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    if request.method == 'POST':
        settings["apify_api_key"] = request.form.get('apify_api_key', '')
        settings["scrape_schedule"] = request.form.get('scrape_schedule', 'daily')
        settings["scrape_time"] = request.form.get('scrape_time', '02:00')
        settings["max_products_per_category"] = int(request.form.get('max_products_per_category', 100))
        settings["default_k_value"] = int(request.form.get('default_k_value', 3))
        settings["enable_weekly_scheduler"] = request.form.get('enable_weekly_scheduler') == 'on'
        settings["last_updated"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=4)
        
        flash("System settings saved successfully!", "success")
        return redirect(url_for('admin_system_settings'))
    
    return render_template('admin_settings.html', settings=settings, username=username, role=role)

@app.route('/admin/view-logs')
def admin_view_logs():
    username = session.get('username')
    role = session.get('role')
    
    if role != 'Admin':
        flash("Access denied. Admin only.", "danger")
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect("polarization_data.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_logs'")
    if cursor.fetchone():
        cursor.execute('''
            SELECT id, log_type, message, created_at 
            FROM system_logs 
            ORDER BY created_at DESC 
            LIMIT 100
        ''')
        logs = cursor.fetchall()
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_type TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        logs = []
    
    conn.close()
    
    return render_template('admin_logs.html', logs=logs, username=username, role=role)

@app.route('/admin/clear-logs', methods=['POST'])
def admin_clear_logs():
    username = session.get('username')
    role = session.get('role')
    
    if role != 'Admin':
        flash("Access denied.", "danger")
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect("polarization_data.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM system_logs")
    conn.commit()
    conn.close()
    
    flash("All logs cleared!", "success")
    return redirect(url_for('admin_view_logs'))

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for('login'))

# ================= RUN =================
if __name__ == "__main__":
    ensure_role_column()
    app.run(debug=True)