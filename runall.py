#!/usr/bin/env python3
import subprocess
import sys
import os
import time
import webbrowser
import signal
import shutil

# ========== ADD THIS FOR NGROK ==========
from pyngrok import ngrok

# Your ngrok auth token (get from https://dashboard.ngrok.com/auth)
NGROK_AUTH_TOKEN = "38NYY7jClFPZNsovGt3BHfUwOYv_28v6SGthUx8PLAiMcoC5w"  # ← PASTE YOUR TOKEN HERE

# =========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Store running processes
processes = []

def get_python_exe(folder_name):
    """Find correct python executable"""
    root_venv = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
    if os.path.exists(root_venv):
        return root_venv
    
    folder_venv = os.path.join(BASE_DIR, folder_name, "venv", "Scripts", "python.exe")
    if os.path.exists(folder_venv):
        return folder_venv
    
    return sys.executable

def get_node_exe():
    """Find node executable"""
    node_path = shutil.which("node")
    if node_path:
        return node_path
    
    common_paths = [
        r"C:\Program Files\nodejs\node.exe",
        r"C:\Program Files (x86)\nodejs\node.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\nodejs\node.exe")
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    return "node"

def run_fastapi():
    """Start FastAPI server (Port 8000)"""
    backend_dir = os.path.join(BASE_DIR, "backend")
    python_exe = get_python_exe("backend")
    
    print(f"🐍 FastAPI using: {python_exe}")
    
    p = subprocess.Popen(
        [python_exe, "main.py"],
        cwd=backend_dir
    )
    processes.append(p)
    print("✅ FastAPI started on http://localhost:8000")

def run_flask():
    """Start Flask server (Port 5000)"""
    auth_dir = os.path.join(BASE_DIR, "2FA")
    python_exe = get_python_exe("2FA")
    
    print(f"🐍 Flask using: {python_exe}")
    
    p = subprocess.Popen(
        [python_exe, "app.py"],
        cwd=auth_dir
    )
    processes.append(p)
    print("✅ Flask started on http://localhost:5000")

def run_apify_webhook():
    """Start Apify Webhook Server (Port 3000)"""
    webhook_dir = os.path.join(BASE_DIR, "apify_webhook_server")
    
    if not os.path.exists(webhook_dir):
        print(f"⚠️ Warning: {webhook_dir} not found!")
        return
    
    index_file = os.path.join(webhook_dir, "index.js")
    if not os.path.exists(index_file):
        print(f"⚠️ Warning: index.js not found in {webhook_dir}")
        return
    
    node_exe = get_node_exe()
    print(f"🟢 Apify Webhook using: {node_exe}")
    
    p = subprocess.Popen(
        [node_exe, "index.js"],
        cwd=webhook_dir
    )
    processes.append(p)
    print("✅ Apify Webhook started on http://localhost:3000")

# ========== ADD THIS FUNCTION FOR NGROK ==========
def run_ngrok_tunnel():
    """Start ngrok tunnel automatically using pyngrok"""
    try:
        # Authenticate with ngrok
        ngrok.set_auth_token(NGROK_AUTH_TOKEN)
        print("✅ ngrok authenticated")
        
        # Create tunnel to port 3000 (Apify webhook)
        tunnel = ngrok.connect(3000, "http")
        public_url = tunnel.public_url
        webhook_url = f"{public_url}/webhook/apify/daraz"
        
        print(f"\n{'='*60}")
        print(f"   🕸️ NGROK TUNNEL ACTIVE")
        print(f"{'='*60}")
        print(f"   Public URL: {public_url}")
        print(f"   Webhook URL (Copy to Apify): {webhook_url}")
        print(f"{'='*60}\n")
        
        # Save URL to file for reference
        url_file = os.path.join(BASE_DIR, "webhook_url.txt")
        with open(url_file, "w") as f:
            f.write(webhook_url)
        
        return webhook_url
        
    except Exception as e:
        print(f"❌ Failed to start ngrok: {e}")
        print("   Please check your auth token and internet connection.")
        return None
# ================================================

def open_browser():
    """Open browser after all servers are ready"""
    time.sleep(10)
    webbrowser.open("http://localhost:5000")

def shutdown(signum=None, frame=None):
    """Shutdown all servers gracefully"""
    print("\n🛑 Shutting down all servers...")
    
    # Close ngrok tunnel
    try:
        ngrok.kill()
        print("✅ ngrok tunnel closed")
    except:
        pass
    
    for p in processes:
        try:
            p.terminate()
            time.sleep(0.5)
            if p.poll() is None:
                p.kill()
        except:
            pass
    
    print("✅ All servers stopped")
    sys.exit(0)

if __name__ == "__main__":
    print("=" * 60)
    print("   PRODUCT POLARIZATION SYSTEM")
    print("=" * 60)
    print("")
    
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    # Start all servers
    run_fastapi()
    time.sleep(2)
    run_flask()
    time.sleep(2)
    run_apify_webhook()
    time.sleep(2)
    
    # Start ngrok tunnel automatically
    run_ngrok_tunnel()
    
    # Open browser
    open_browser()
    
    print("\n" + "=" * 60)
    print("   ALL SERVERS ARE RUNNING")
    print("=" * 60)
    print("   🔐 Flask (Auth):    http://localhost:5000")
    print("   📡 FastAPI (API):   http://localhost:8000")
    print("   🕸️ Webhook:         http://localhost:3000")
    print("=" * 60)
    print("   Press Ctrl+C to stop all servers")
    print("=" * 60)
    
    while True:
        time.sleep(1)