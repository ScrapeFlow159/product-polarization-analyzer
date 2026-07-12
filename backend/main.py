from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Response, status
from pydantic import BaseModel
from typing import List, Dict, Optional
import pandas as pd
import json  
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import numpy as np
from fastapi.middleware.wsgi import WSGIMiddleware
from sklearn.metrics import silhouette_score
from sklearn.cluster import KMeans
import sqlite3
from database import DB_PATH  
import traceback
import os
from datetime import datetime, timedelta
import re
from flask_app import app as flask_app
from database import (
    save_analysis_result, get_current_analysis, get_weekly_analysis,
    get_monthly_analysis, get_polarization_comparison, save_time_snapshot,
    get_trend_data, get_all_historical_data,
    save_daily_snapshot, get_daily_snapshots, get_weekly_snapshots ,
    get_system_settings, save_system_settings 
)
from scheduler import start_scheduler
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
import sqlite3
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
import uvicorn
from pydantic import BaseModel


app = FastAPI(title="Product Polarization API - Time-Based Analysis",
              description="Analyze product polarization with weekly/monthly trends",
              version="5.0.0")

import csv
from io import StringIO
from fastapi.responses import StreamingResponse

SECRET_KEY = "secretkey123secretkey123secretkey123"
ALGORITHM = "HS256"

# main.py mein ye change karein
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://product-polarization-analyzer.vercel.app",
        "https://polarizationanalyzer.com",
        "https://www.polarizationanalyzer.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Flask app mounted successfully on /auth")
# main.py - ADMIN ENDPOINTS (Corrected)
# ============================================

import os
import sqlite3
from fastapi import Request

# ✅ JWT Verification Function
def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"username": payload.get("sub"), "role": payload.get("role")}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ✅ USERS_DB_PATH define karein
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_DB_PATH = os.path.join(BASE_DIR, "users.db")

@app.get("/")
def root():
    return {"message": "API running 🚀"}

@app.get("/api/manage-users")
async def get_users(
    auth_data: dict = Depends(verify_jwt_token)  # ✅ ADD THIS
):
    if auth_data["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    """Get all users for admin panel"""
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role FROM users")
        users = cursor.fetchall()
        conn.close()
        
        user_list = []
        for user in users:
            user_list.append({
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "role": user[3]
            })
        
        return {"status": "success", "users": user_list}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.put("/api/manage-users/{user_id}")
async def update_user(
    user_id: int,
    request: Request,
    auth_data: dict = Depends(verify_jwt_token)  # ✅ ADD THIS
):
    if auth_data["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    """Update user role"""
    try:
        data = await request.json()
        new_role = data.get('role')
        
        if not new_role:
            return {"status": "error", "message": "Role required"}, 400
        
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            (new_role, user_id)
        )
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        if affected == 0:
            return {"status": "error", "message": "User not found"}, 404
        
        return {"status": "success", "message": "User role updated"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.delete("/api/manage-users/{user_id}")
async def delete_user(
    user_id: int,
    auth_data: dict = Depends(verify_jwt_token)  # ✅ ADD THIS
):
    if auth_data["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    """Delete user"""
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        if affected == 0:
            return {"status": "error", "message": "User not found"}, 404
        
        return {"status": "success", "message": "User deleted"}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.get("/api/system-settings")
async def get_settings(
    auth_data: dict = Depends(verify_jwt_token)
):
    if auth_data["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    """Get system settings from database"""
    try:
        from database import get_system_settings
        settings = get_system_settings()
        return {
            "status": "success",
            "settings": settings
        }
    except Exception as e:
        print(f"❌ Error getting settings: {e}")
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e)
        }, 500


@app.put("/api/system-settings")
async def update_settings(
    request: Request,
    auth_data: dict = Depends(verify_jwt_token)
):
    if auth_data["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    """Save system settings to database"""
    try:
        from database import save_system_settings
        
        data = await request.json()
        settings = data.get("settings", data)  # Handle both formats
        
        # Save to database
        success = save_system_settings(settings)
        
        if success:
            return {
                "status": "success",
                "message": "Settings saved successfully!",
                "settings": settings
            }
        else:
            return {
                "status": "error",
                "message": "Failed to save settings"
            }, 500
            
    except Exception as e:
        print(f"❌ Error saving settings: {e}")
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e)
        }, 500
@app.get("/api/view-logs")
async def view_logs(
    auth_data: dict = Depends(verify_jwt_token)  # ✅ ADD THIS
):
    if auth_data["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    """View system logs"""
    try:
        logs = []
        log_files = ["app.log", "logs/app.log", "log.txt", "server.log"]
        
        for log_file in log_files:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    logs = lines[-100:]
                break
        
        if not logs:
            logs = ["No logs found. System is running smoothly!"]
        
        return {
            "status": "success",
            "logs": logs,
            "total_lines": len(logs)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        conn.close()
        
        return {
            "status": "healthy",
            "users": user_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 500
def save_user_params(username, k_value, weights):
    """Save user parameters to database"""
    conn = sqlite3.connect(USERS_DB_PATH)
    cursor = conn.cursor()
    
    # Create table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_params (
            username TEXT PRIMARY KEY,
            k_value INTEGER,
            weights TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Save params
    cursor.execute(
        "INSERT OR REPLACE INTO user_params (username, k_value, weights) VALUES (?, ?, ?)",
        (username, k_value, json.dumps(weights))
    )
    conn.commit()
    conn.close()
    print(f"✅ Saved params to database for {username}: K={k_value}")

def get_user_params(username):
    """Get user parameters - with guaranteed table creation"""
    try:
        conn = sqlite3.connect(USERS_DB_PATH)
        cursor = conn.cursor()
        
        # FORCE CREATE TABLE BEFORE QUERY
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_params (
                username TEXT PRIMARY KEY,
                k_value INTEGER NOT NULL,
                weights TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute(
            "SELECT k_value, weights FROM user_params WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            print(f"✅ Found in database for {username}: K={row[0]}")
            return {
                "k_value": row[0],
                "weights": json.loads(row[1])
            }
        else:
            print(f"⚠️ No saved params found for {username}")
            return None
    except Exception as e:
        print(f"❌ Error getting params: {e}")
        return None
# Data models
class Product(BaseModel):
    name: str
    price: float
    rating: float
    reviews: int
    popularity_score: float
    cluster: int
    cluster_label: str
    seller: Optional[str] = None
    brand: Optional[str] = None

class PolarizationAnalysis(BaseModel):
    platform: str
    total_products: int
    polarization_score: float
    polarization_level: str
    clusters: List[Dict]
    products: List[Product]
    feature_importance: Dict[str, float]
    analysis_timestamp: str
    data_source: str
    csv_file_used: str
    silhouette_score: float
    analysis_type: Optional[str] = "current"
    insights: Optional[Dict] = None

class TimeComparisonResponse(BaseModel):
    current: Optional[Dict]
    weekly_avg: Optional[float]
    monthly_avg: Optional[float]
    weekly_trend: Optional[str]
    monthly_trend: Optional[str]
    historical_data: Dict

class AnalysisRequest(BaseModel):
    platform: str
    category: str
    subcategory: str
    max_products: Optional[int] = 100
    analysis_type: Optional[str] = "current"  # current, weekly, monthly
    save_to_db: Optional[bool] = True
    k_value: Optional[int] = None          # Changed to None
    weights: Optional[Dict[str, float]] = None   # Changed to Non

class CustomAnalysisRequest(BaseModel):
    platform: str
    category: str
    unit: str  # 'days' ya 'weeks'
    duration: int  # 3,5,7 for days / 2,3,4 for weeks
    max_products: Optional[int] = 50
    k_value: Optional[int] = 3  # ✅ ADD THIS
    weights: Optional[Dict[str, float]] = None  # ✅ ADD THIS

class AnalysisParams(BaseModel):
    k_value: int = 3
    price_weight: float = 1.0
    rating_weight: float = 1.0
    reviews_weight: float = 1.0
    popularity_weight: float = 1.0

class AnalysisParams(BaseModel):
    k_value: int = 3
    price_weight: float = 1.0
    rating_weight: float = 1.0
    reviews_weight: float = 1.0
    popularity_weight: float = 1.0



def get_k_value_from_db():
    conn = sqlite3.connect(DB_PATH)  # ✅ SAHI DB
    cursor = conn.cursor()
    cursor.execute("SELECT config_value FROM system_settings WHERE config_key = 'analysis.default_k_value'")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return int(row[0])
    return 3
@app.post("/api/analyze")
async def analyze_polarization(
    request: AnalysisRequest,
    auth_data: dict = Depends(verify_jwt_token)  
):
    username = auth_data["username"] 
    role = auth_data["role"] 
    """Main analysis endpoint with time-based analysis support"""
    try:
        print(f"\n{'='*60}")
        print(f"🔍 Analyzing {request.platform.upper()} - {request.subcategory}")
        print(f"   Type: {request.analysis_type}")
        print(f"   User: {username}, Role: {role}")
        print(f"{'='*60}")
        
        # ========== GET SYSTEM DEFAULTS (Admin Settings) ==========
        from database import get_system_settings
        system_settings = get_system_settings()
        system_default_k = system_settings.get("analysis", {}).get("default_k_value", 3)
        print(f"📊 System Default K-Value: {system_default_k}")
        
        # ========== GET CUSTOM PARAMETERS ==========
        # Priority 1: Frontend values (user ne manually select kiya)
        custom_k = request.k_value if request.k_value is not None else system_default_k
        weights = request.weights if request.weights is not None else {
            "price": 1.0, "rating": 1.0, "reviews": 1.0, "popularity": 1.0
        }

        print(f"📥 Received from Frontend → k={request.k_value}, weights={request.weights}")
        print(f"✅ FINAL VALUES → k={custom_k}, weights={weights}")

        # ========== RESEARCH ANALYST SAVED PARAMS ==========
        if username and role and role.lower() == "research analyst":
            db_params = get_user_params(username)
            if db_params:
                print(f"📊 Found saved params in DB: K={db_params.get('k_value')}")
                
                # Use saved params ONLY if frontend sent default
                if custom_k == system_default_k:
                    custom_k = db_params.get("k_value", system_default_k)
                    print(f"🔄 Using saved K from DB: {custom_k}")

                if (weights.get("price") == 1.0 and 
                    weights.get("rating") == 1.0 and 
                    weights.get("reviews") == 1.0 and 
                    weights.get("popularity") == 1.0):
                    
                    saved_weights = db_params.get("weights")
                    if saved_weights:
                        weights = saved_weights
                        print(f"🔄 Using saved weights from DB")
        
        print(f"✅ FINAL PARAMETERS USED → k={custom_k}, weights={weights}")
        
        
        # ========== PLATFORM SELECTION & DATA EXTRACTION ==========
        if request.platform.lower() == "daraz":
            subcategory = request.subcategory.lower().replace(" ", "_")
            if subcategory not in DARAZ_DATASETS:
                raise HTTPException(status_code=404, detail=f"No CSV found for subcategory: {request.subcategory}")
            products = extract_daraz_products(subcategory, request.max_products)
            platform_name = "Daraz.pk"
            csv_file = f"{subcategory}.csv"
        elif request.platform.lower() == "etsy":
            subcategory = request.subcategory.lower().replace(" ", "_")
            if subcategory not in ETSY_DATASETS:
                raise HTTPException(status_code=404, detail=f"No CSV found for Etsy subcategory: {request.subcategory}")
            products = extract_etsy_products(subcategory, request.max_products)
            platform_name = "Etsy.com"
            csv_file = f"{subcategory}.csv"
        else:
            raise HTTPException(status_code=400, detail="Invalid platform")
        
        if not products:
            raise HTTPException(status_code=404, detail=f"No valid products found")
        
        # Debug output
        print(f"\n🔍 ===== DEBUG for {request.subcategory} =====")
        print(f"📦 Total products: {len(products)}")
        if products:
            prices = [p['price'] for p in products[:10]]
            ratings = [p['rating'] for p in products[:10]]
            print(f"💰 Sample prices: {prices[:5]}")
            print(f"⭐ Sample ratings: {ratings[:5]}")
        print(f"==========================================\n")
        
        # ========== NORMALIZATION & CLUSTERING ==========
        products = normalize_features(products, weights)
        n_clusters = min(custom_k, len(products))
        print(f"📊 Clustering with k={n_clusters}")
        
        clustered_products, centers, cluster_labels, sil_score = apply_clustering(products, n_clusters, weights)
        clustered_products.sort(key=lambda x: x['ranking_score'], reverse=True)
        
        # ========== POLARIZATION SCORE ==========
        polarization_score = calculate_polarization_score(clustered_products, centers, n_clusters)
        
        # ========== FOR WEEKLY/MONTHLY: OVERRIDE WITH HISTORICAL AVERAGE ==========
        if request.analysis_type in ["weekly", "monthly"]:
            from database import get_daily_snapshots
            days = 7 if request.analysis_type == "weekly" else 30
            snapshots = get_daily_snapshots(platform_name, request.subcategory)
            
            if snapshots and len(snapshots) >= days:
                last_n_scores = [s['polarization_score'] for s in snapshots[-days:]]
                avg_score = sum(last_n_scores) / len(last_n_scores)
                print(f"📊 {request.analysis_type.upper()} - Using historical average: {avg_score:.4f} (current would be: {polarization_score:.4f})")
                polarization_score = avg_score
            else:
                print(f"⚠️ Not enough historical data for {request.analysis_type} (need {days}, have {len(snapshots) if snapshots else 0})")
        
        polarization_level = get_polarization_level(polarization_score)
        
        # ========== BUILD CLUSTERS INFO ==========
        clusters = []
        for i in range(n_clusters):
            cluster_products = [p for p in clustered_products if p['cluster'] == i]
            if cluster_products:
                avg_price = np.mean([p['price'] for p in cluster_products])
                avg_rating = np.mean([p['rating'] for p in cluster_products])
                clusters.append({
                    "cluster_id": i,
                    "label": cluster_labels[i],
                    "size": len(cluster_products),
                    "avg_price": round(avg_price, 2),
                    "avg_rating": round(avg_rating, 2),
                    "percentage": round(len(cluster_products) / len(products) * 100, 1)
                })
        
        # ========== FEATURE IMPORTANCE ==========
        feature_importance = {
            "price": round(abs(centers[:, 0].max() - centers[:, 0].min()) * 100, 1),
            "rating": round(abs(centers[:, 1].max() - centers[:, 1].min()) * 100, 1),
            "reviews": round(abs(centers[:, 2].max() - centers[:, 2].min()) * 100, 1),
            "popularity": round(abs(centers[:, 3].max() - centers[:, 3].min()) * 100, 1)
        }
        
        # ========== RESPONSE PRODUCTS ==========
        response_products = []
        for p in clustered_products[:20]:
            response_products.append(Product(
                name=p['name'],
                price=p['price'],
                rating=p['rating'],
                reviews=p['reviews'],
                popularity_score=p['popularity'],
                cluster=p['cluster'],
                cluster_label=p['cluster_label'],
                seller=p.get('seller'),
                brand=p.get('brand')
            ))
        results = [{
            "date": datetime.now().strftime('%Y-%m-%d'),
            "polarization_score": polarization_score
        }]
        insights = generate_insights(results)
        result = PolarizationAnalysis(
            platform=platform_name,
            total_products=len(products),
            polarization_score=round(polarization_score, 3),
            polarization_level=polarization_level,
            clusters=clusters,
            products=response_products,
            feature_importance=feature_importance,
            analysis_timestamp=datetime.now().isoformat(),
            data_source=f"CSV - {csv_file}",
            csv_file_used=csv_file,
            silhouette_score=round(sil_score, 4),
            analysis_type=request.analysis_type,
            insights=insights
        )
        
        # ========== SAVE TO DATABASE ==========
        if request.save_to_db:
            save_analysis_result(
                platform=platform_name,
                category=request.subcategory,
                analysis_type=request.analysis_type,
                analysis_date=datetime.now(),
                total_products=len(products),
                polarization_score=polarization_score,
                polarization_level=polarization_level,
                silhouette_score=sil_score,
                clusters=clusters,
                feature_importance=feature_importance,
                top_products=[p.model_dump() for p in response_products]
            )
            
            avg_price = np.mean([p.price for p in response_products[:10]])
            avg_rating = np.mean([p.rating for p in response_products[:10]])
            cluster_dist = {c['label']: c['size'] for c in clusters}
            
            save_time_snapshot(
                platform=platform_name,
                category=request.subcategory,
                snapshot_type=request.analysis_type,
                snapshot_date=datetime.now(),
                polarization_score=polarization_score,
                total_products=len(products),
                avg_price=round(avg_price, 2),
                avg_rating=round(avg_rating, 2),
                cluster_distribution=cluster_dist
            )
            
            save_daily_snapshot(
                platform=platform_name,
                category=request.subcategory,
                snapshot_date=datetime.now().date(),
                polarization_score=polarization_score,
                total_products=len(products)
            )
            print(f"✅ Daily snapshot saved: {platform_name}/{request.subcategory}")
        
        print(f"✅ Analysis complete! Polarization Score: {polarization_score}")
        return result.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/public-system-settings")
async def get_public_settings():
    """
    Public endpoint for getting system settings - NO AUTH REQUIRED
    Sirf default_k_value return karega, sensitive data nahi
    """
    try:
        from database import get_system_settings
        settings = get_system_settings()
        return {
            "status": "success",
            "default_k_value": settings.get("analysis", {}).get("default_k_value", 3)
        }
    except Exception as e:
        print(f"❌ Error getting public settings: {e}")
        return {
            "status": "error",
            "default_k_value": 3
        }
@app.get("/test")
def test():
    return {"message": "working"}



# ✅ THEN mount Flask app
app.mount("/auth", WSGIMiddleware(flask_app))



# Serve static files (frontend)
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
print(f"📁 Frontend path: {frontend_path}")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# Serve index.html at root
@app.get("/")
@app.get("/index.html")
async def serve_index():
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Frontend not found</h1>", status_code=404)

@app.get("/api/export-results")
async def export_results(
    platform: str = "daraz", 
    category: str = "earpods", 
    analysis_type: str = "current",
    auth_data: dict = Depends(verify_jwt_token)
):
    username = auth_data["username"]
    role = auth_data["role"]
    
    if role not in ["Research Analyst", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Research Analyst and Admin can export data")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        platform_name = "Daraz.pk" if platform.lower() == "daraz" else "Etsy.com"

        # ✅ First check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='polarization_analysis'")
        if not cursor.fetchone():
            raise HTTPException(
                status_code=404, 
                detail="No analysis data found. Please run analysis first."
            )

        # ✅ Get columns to query dynamically
        cursor.execute("PRAGMA table_info(polarization_analysis)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Build query based on available columns
        select_fields = ["polarization_score", "total_products", "analysis_date"]
        if 'clusters' in columns:
            select_fields.append("clusters")
        else:
            select_fields.append("NULL as clusters")
            
        if 'feature_importance' in columns:
            select_fields.append("feature_importance")
        else:
            select_fields.append("NULL as feature_importance")
            
        if 'top_products' in columns:
            select_fields.append("top_products")
        else:
            select_fields.append("NULL as top_products")
        
        query = f'''
            SELECT {", ".join(select_fields)}
            FROM polarization_analysis 
            WHERE platform = ? AND category = ? AND analysis_type = ?
            ORDER BY analysis_date DESC LIMIT 1
        '''
        
        cursor.execute(query, (platform_name, category, analysis_type))
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(
                status_code=404, 
                detail=f"No {analysis_type} data found for {platform_name} - {category}. Please run analysis first."
            )

        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # ========== HEADER SECTION ==========
        writer.writerow(["=" * 60])
        writer.writerow(["PRODUCT POLARIZATION ANALYSIS REPORT"])
        writer.writerow(["=" * 60])
        writer.writerow([])
        
        # ========== BASIC INFO ==========
        writer.writerow(["Platform:", platform_name])
        writer.writerow(["Category:", category])
        writer.writerow(["Analysis Type:", analysis_type.upper()])
        writer.writerow(["Generated On:", str(row[2])[:19] if row[2] else "N/A"])
        writer.writerow(["Polarization Score:", round(float(row[0]), 3) if row[0] else "N/A"])
        writer.writerow(["Polarization Level:", get_polarization_level(float(row[0])) if row[0] else "N/A"])
        writer.writerow(["Total Products Analyzed:", row[1] if row[1] else 0])
        writer.writerow([])
        
        # ========== CLUSTER DETAILS ==========
        writer.writerow(["-" * 60])
        writer.writerow(["CLUSTER DISTRIBUTION"])
        writer.writerow(["-" * 60])
        writer.writerow(["Cluster", "Size", "Avg Price", "Avg Rating", "Market Share"])
        
        clusters_data = row[3] if len(row) > 3 else None
        if clusters_data:
            try:
                clusters = json.loads(clusters_data)
                if clusters:
                    for c in clusters:
                        writer.writerow([
                            c.get('label', 'N/A'),
                            c.get('size', 0),
                            f"${c.get('avg_price', 0):.2f}" if platform.lower() == "etsy" else f"Rs. {c.get('avg_price', 0):.2f}",
                            c.get('avg_rating', 0),
                            f"{c.get('percentage', 0)}%"
                        ])
                else:
                    writer.writerow(["No cluster data available"])
            except:
                writer.writerow(["Error parsing cluster data"])
        else:
            writer.writerow(["No cluster data available"])
        
        writer.writerow([])
        
        # ========== TOP 10 PRODUCTS ==========
        writer.writerow(["-" * 60])
        writer.writerow(["🏆 TOP 10 PRODUCTS RANKING"])
        writer.writerow(["-" * 60])
        writer.writerow(["Rank", "Product Name", "Price", "Rating", "Reviews", "Cluster", "Score"])
        
        top_products_data = row[5] if len(row) > 5 else None  # top_products is at index 5
        if top_products_data:
            try:
                products = json.loads(top_products_data)
                if products:
                    for idx, p in enumerate(products[:10], 1):
                        # Calculate ranking score if not available
                        score = p.get('ranking_score', 0)
                        if score == 0:
                            # Calculate simple score
                            rating_norm = p.get('rating', 0) / 5.0
                            reviews_norm = min(1.0, p.get('reviews', 0) / 1000)
                            price_norm = min(1.0, p.get('price', 0) / 1000)
                            score = round((rating_norm * 0.4 + reviews_norm * 0.3 + (1 - price_norm) * 0.3) * 100, 1)
                        
                        price_str = f"${p.get('price', 0):.2f}" if platform.lower() == "etsy" else f"Rs. {p.get('price', 0):.2f}"
                        writer.writerow([
                            idx,
                            p.get('name', 'N/A')[:50],
                            price_str,
                            p.get('rating', 0),
                            p.get('reviews', 0),
                            p.get('cluster_label', 'N/A'),
                            f"{score:.1f}%"
                        ])
                else:
                    writer.writerow(["No product data available"])
            except Exception as e:
                writer.writerow([f"Error parsing product data: {str(e)}"])
        else:
            writer.writerow(["No product data available"])
        
        writer.writerow([])
        
        # ========== FEATURE IMPORTANCE ==========
        writer.writerow(["-" * 60])
        writer.writerow(["FEATURE IMPORTANCE"])
        writer.writerow(["-" * 60])
        
        feature_data = row[4] if len(row) > 4 else None  # feature_importance is at index 4
        if feature_data:
            try:
                features = json.loads(feature_data)
                if features:
                    writer.writerow(["Feature", "Importance (%)"])
                    for key, value in features.items():
                        writer.writerow([key.capitalize(), f"{value:.1f}%"])
                else:
                    writer.writerow(["No feature importance data available"])
            except:
                writer.writerow(["Error parsing feature importance data"])
        else:
            writer.writerow(["No feature importance data available"])
        
        writer.writerow([])
        writer.writerow(["=" * 60])
        writer.writerow(["END OF REPORT"])
        writer.writerow(["=" * 60])

        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={platform}_{category}_{analysis_type}_report.csv"}
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Export error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
# Store parameters in session (temporary)
analysis_params = {
    "k_value": 3,
    "weights": {
        "price": 1.0,
        "rating": 1.0,
        "reviews": 1.0,
        "popularity": 1.0
    }
}

# ========== RESEARCH ANALYST PARAMETERS ENDPOINTS ==========

# Store parameters per user
research_analyst_params = {}

@app.get("/api/get-params")
async def get_parameters(
    auth_data: dict = Depends(verify_jwt_token)  # ✅ ADD THIS
):
    username = auth_data["username"]
    role = auth_data["role"]
    
    if role != "Research Analyst":
        raise HTTPException(status_code=403, detail="Research Analyst access required")
    """Get current parameters for the user - FIXED"""
    print(f"📊 Get params called: username={username}, role={role}")
    
    default_params = {
        "k_value": 3,
        "weights": {
            "price": 1.0,
            "rating": 1.0,
            "reviews": 1.0,
            "popularity": 1.0
        }
    }
    
    if username and role and role.lower() == "research analyst":
        # 1. PEHLE DATABASE CHECK KARO (Taake hamesha fresh data mile)
        db_params = get_user_params(username)
        
        if db_params:
            print(f"✅ Found in database for {username}")
            # Memory ko update karo taake agar kahin memory use ho rahi ho toh woh bhi fresh ho
            research_analyst_params[username] = db_params
            return db_params
        
        # 2. Agar DB mein nahi hai, tabhi memory check karo (Optional fallback)
        if username in research_analyst_params:
            print(f"✅ Found in memory for {username}")
            return research_analyst_params[username]
        
        print(f"⚠️ No saved params found for {username}")
    
    return default_params

@app.post("/api/set-params")
async def set_parameters(
    params: AnalysisParams,
    auth_data: dict = Depends(verify_jwt_token)  # ✅ ADD THIS
):
    username = auth_data["username"]
    role = auth_data["role"]
    
    if role != "Research Analyst":
        raise HTTPException(status_code=403, detail="Research Analyst access required")
    """Set analysis parameters for Research Analyst - FIXED"""
    
    print(f"📊 Set params called: username={username}, role={role}")
    
    # 1. DB mein save karein (Yeh aapka pehle se sahi hai)
    if username and role and role.lower() == "research analyst":
        save_user_params(
            username,
            params.k_value,
            {
                "price": params.price_weight,
                "rating": params.rating_weight,
                "reviews": params.reviews_weight,
                "popularity": params.popularity_weight
            }
        )
        
        # 2. MEMORY UPDATE KAREIN (Research Analyst Dictionary mein)
        # Global analysis_params ke bajaye user-specific memory ko update karein
        research_analyst_params[username] = {
            "k_value": params.k_value,
            "weights": {
                "price": params.price_weight,
                "rating": params.rating_weight,
                "reviews": params.reviews_weight,
                "popularity": params.popularity_weight
            }
        }
    
    return {
        "status": "success",
        "message": "Parameters updated successfully"
    }

# Global variables for CSV data
DARAZ_DATASETS = {}
ETSY_DATASETS = {}
CSV_FILES_FOUND = {
    "daraz": False,
    "etsy": False
}

print("\n" + "="*60)
print("🚀 PRODUCT POLARIZATION API - TIME-BASED ANALYSIS")
print("="*60)

def get_db_connection():
    """Get database connection with timeout"""
    import sqlite3
    from database import DB_PATH
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def load_csv_data():
    """Load data from CSV files"""
    global DARAZ_DATASETS, ETSY_DATASETS, CSV_FILES_FOUND
    
    print("\n📂 LOADING CSV DATA...")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    daraz_files = {
        "earpods": [os.path.join(base_dir, "earpods.csv"), os.path.join(base_dir, "data", "earpods.csv"), "earpods.csv"],
        "powerbanks": [os.path.join(base_dir, "powerbanks.csv"), os.path.join(base_dir, "data", "powerbanks.csv"), "powerbanks.csv"],
        "gaming_accessories": [os.path.join(base_dir, "gaming_accessories.csv"), os.path.join(base_dir, "data", "gaming_accessories.csv"), "gaming_accessories.csv"],
        "mobile_phone_accessories": [os.path.join(base_dir, "mobile_phone_accessories.csv"), os.path.join(base_dir, "data", "mobile_phone_accessories.csv"), "mobile_phone_accessories.csv"],
        "smart_watches": [os.path.join(base_dir, "smart_watches.csv"), os.path.join(base_dir, "data", "smart_watches.csv"), "smart_watches.csv"]
    }

    for category, paths in daraz_files.items():
        for path in paths:
            if os.path.exists(path):
                try:
                    print(f"📖 Reading Daraz {category} CSV from: {path}")
                    df = pd.read_csv(path, encoding='utf-8')
                    df = df.dropna(how='all')
                    df = df.fillna('')
                    DARAZ_DATASETS[category] = df.to_dict('records')
                    CSV_FILES_FOUND[f"daraz_{category}"] = True
                    CSV_FILES_FOUND["daraz"] = True
                    print(f"✅ Loaded {len(DARAZ_DATASETS[category])} {category} products")
                    break
                except Exception as e:
                    print(f"❌ Failed to load {path}: {str(e)}")
                    continue

    etsy_files = {
        "art": [os.path.join(base_dir, "art.csv"), os.path.join(base_dir, "data", "art.csv"), "art.csv"],
        "handmade": [os.path.join(base_dir, "handmade.csv"), os.path.join(base_dir, "data", "handmade.csv"), "handmade.csv"],
        "jewelry": [os.path.join(base_dir, "jewelry.csv"), os.path.join(base_dir, "data", "jewelry.csv"), "jewelry.csv"],
        "vintage": [os.path.join(base_dir, "vintage.csv"), os.path.join(base_dir, "data", "vintage.csv"), "vintage.csv"],
        "accessories": [os.path.join(base_dir, "accessories.csv"), os.path.join(base_dir, "data", "accessories.csv"), "accessories.csv"]
    }

    for category, paths in etsy_files.items():
        for path in paths:
            if os.path.exists(path):
                try:
                    print(f"📖 Reading Etsy {category} CSV from: {path}")
                    df = pd.read_csv(path, encoding='utf-8')
                    df = df.dropna(how='all')
                    df = df.fillna('')
                    ETSY_DATASETS[category] = df.to_dict('records')
                    CSV_FILES_FOUND[f"etsy_{category}"] = True
                    CSV_FILES_FOUND["etsy"] = True
                    print(f"✅ Loaded {len(ETSY_DATASETS[category])} {category} products")
                    break
                except Exception as e:
                    print(f"❌ Failed to load {path}: {str(e)}")

    print("\n✅ CSV files loaded successfully!")
    print("="*60)


@app.post("/api/apify-webhook")
async def apify_webhook(request: dict, background_tasks: BackgroundTasks):
    """
    Apify webhook handler - receives data from webhook service and saves CSV
    Supports both Daraz and Etsy formats
    """
    try:
        print("\n" + "="*60)
        print("🔥 WEBHOOK RECEIVED FROM APIFY")
        print("="*60)
        print(f"📦 Full Payload: {json.dumps(request, indent=2)}")
        
        # ✅ Get datasetId
        dataset_id = request.get("datasetId")
        
        # ✅ Check if it's Etsy (has datasetId)
        if dataset_id:
            # ✅ Clean datasetId if it's a template variable
            if isinstance(dataset_id, str) and dataset_id.startswith("{{"):
                resource = request.get("resource", {})
                dataset_id = resource.get("defaultDatasetId")
            
            # ✅ Get category from multiple sources
            category = request.get("category")
            
            # ✅ If category is None or starts with {{, try to get from input
            if not category or (isinstance(category, str) and category.startswith("{{")):
            # Try to get from input
                input_data = request.get("input", {})
                if isinstance(input_data, dict):
        # ✅ NEW: Get category from "keyword" field (Etsy)
                    keyword = input_data.get("keyword")
                    if keyword:
                        category = keyword
                        print(f"📂 Category from input.keyword: {category}")
        # Fallback to "search" array
            else:
                search = input_data.get("search", [])
                if search and len(search) > 0:
                    category = search[0]
                    print(f"📂 Category from input.search: {category}")
                elif input_data.get("category"):
                    category = input_data.get("category")
                
                # Try ALL_INPUT
                if not category:
                    input_data = request.get("input", {})
                    start_urls = input_data.get("startUrls", [])
    
                    if start_urls and len(start_urls) > 0:
        # Option A: URL se q= parameter
                        url = start_urls[0].get("url", "")
                        if "q=" in url:
                            import urllib.parse
                            parsed = urllib.parse.urlparse(url)
                            params = urllib.parse.parse_qs(parsed.query)
                            if params.get("q"):
                                category = params["q"][0]
                                print(f"📂 Category from URL: {category}")
        
        # Option B: userData se category
                    if not category:
                        user_data = start_urls[0].get("userData", {})
                        if user_data.get("category"):
                            category = user_data.get("category")
                            print(f"📂 Category from userData: {category}")
            
            # ✅ If still None, use "etsy" as fallback
            if not category:
                category = "etsy"
            
            platform = "etsy"
            
            print(f"📦 Etsy webhook detected")
            print(f"📦 datasetId: {dataset_id}")
            print(f"📂 Category: {category}")
            
            if dataset_id and not (isinstance(dataset_id, str) and dataset_id.startswith("{{")):
                background_tasks.add_task(fetch_apify_products, dataset_id, category, platform)
                return {
                    "status": "success",
                    "message": f"Processing Etsy dataset {dataset_id} for {category}",
                    "category": category,
                    "platform": platform
                }
            else:
                return {
                    "status": "error",
                    "message": "No valid datasetId found"
                }, 400
        
        # ✅ Daraz format - direct products
        category = request.get("category", "unknown")

# ✅ If category is "unknown", try to get from input
        if category == "unknown":
            input_data = request.get("input", {})
            if isinstance(input_data, dict):
        # Try to get category from input
                input_category = input_data.get("category")
                if input_category:
                    category = input_category
                    print(f"📂 Category from input: {category}")
        # Try searchKeyword as fallback
                elif input_data.get("searchKeyword"):
                    category = input_data.get("searchKeyword")
                    print(f"📂 Category from searchKeyword: {category}")
        products = request.get("products", [])
        platform = request.get("platform", "daraz")
        
        print(f"📂 Category: {category}")
        print(f"📦 Products received: {len(products)}")
        print(f"📱 Platform: {platform}")
        
        if products and len(products) > 0:
            # ✅ Save CSV in background
            background_tasks.add_task(save_apify_csv, products, category, platform)
            
            return {
                "status": "success",
                "message": f"Processing {len(products)} products for {category}",
                "category": category,
                "products_count": len(products)
            }
        else:
            # ✅ Try old format (direct from Apify)
            resource = request.get("resource", {})
            input_data = resource.get("input", {})
            category = input_data.get("category", "unknown")
            
            # Try to get products from dataset
            dataset_id = request.get("datasetId") or request.get("dataset_id")
            if dataset_id and not (isinstance(dataset_id, str) and dataset_id.startswith("{{")):
                import requests
                APIFY_TOKEN = os.getenv("APIFY_TOKEN", "apify_api_HlY6edMSwNJqptH4B2FWttNUIIbHKV0z1JTy")
                url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?clean=true&token={APIFY_TOKEN}"
                response = requests.get(url)
                if response.status_code == 200:
                    products = response.json()
                    background_tasks.add_task(save_apify_csv, products, category, platform)
                    return {
                        "status": "success",
                        "message": f"Fetched {len(products)} products from dataset {dataset_id}",
                        "category": category
                    }
            
            return {
                "status": "warning",
                "message": "No products found in webhook data",
                "category": category
            }
            
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}, 500

async def fetch_apify_products(dataset_id: str, category: str, platform: str):
    """Fetch products from Apify dataset"""
    try:
        import requests
        APIFY_TOKEN = os.getenv("APIFY_TOKEN", "apify_api_HlY6edMSwNJqptH4B2FWttNUIIbHKV0z1JTy")
        
        print(f"📥 Fetching products from dataset: {dataset_id}")
        
        url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?clean=true&token={APIFY_TOKEN}"
        response = requests.get(url)
        
        if response.status_code == 200:
            products = response.json()
            print(f"✅ Fetched {len(products)} products")
            await save_apify_csv(products, category, platform)
        else:
            print(f"❌ Failed to fetch: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error fetching products: {e}")
        traceback.print_exc()
        
async def save_apify_csv(products: list, category: str, platform: str):
    """
    Save Apify products to CSV and reload in memory
    """
    try:
        import pandas as pd
        import os
        
        print(f"💾 Saving {len(products)} products for {category}...")
        
        # Convert to DataFrame
        df = pd.DataFrame(products)
        
        # Clean column names for Daraz/Etsy
        if platform.lower() == "daraz":
            # Rename columns if needed
            if 'name' not in df.columns and 'title' in df.columns:
                df.rename(columns={'title': 'name'}, inplace=True)
            if 'price' not in df.columns and 'product_price' in df.columns:
                df.rename(columns={'product_price': 'price'}, inplace=True)
            if 'ratingScore' not in df.columns and 'rating' in df.columns:
                df.rename(columns={'rating': 'ratingScore'}, inplace=True)
            if 'itemSold' not in df.columns and 'sold' in df.columns:
                df.rename(columns={'sold': 'itemSold'}, inplace=True)
        
        # Save to CSV
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        csv_path = os.path.join(data_dir, f"{category}.csv")
        df.to_csv(csv_path, index=False)
        
        print(f"✅ CSV saved: {csv_path} ({len(df)} products)")


        # ✅ ========== NEW: Save raw data to database ==========
        try:
            from database import save_raw_products
            
            # Convert DataFrame to list of dicts
            raw_products = df.to_dict('records')
            
            # Ensure each product has category
            for p in raw_products:
                if 'category' not in p or not p['category']:
                    p['category'] = category
            
            save_raw_products(
                platform=platform,
                category=category,
                products=raw_products
            )
            print(f"✅ Raw data stored in database for {category}")
            
        except Exception as e:
            print(f"⚠️ Warning: Could not save raw data: {e}")
        # ========================================================
        
        # ✅ Reload in memory
        global DARAZ_DATASETS, ETSY_DATASETS
        
        if platform.lower() == "daraz":
            DARAZ_DATASETS[category] = df.to_dict('records')
            print(f"✅ Daraz data reloaded: {category} ({len(DARAZ_DATASETS[category])} products)")
        else:
            ETSY_DATASETS[category] = df.to_dict('records')
            print(f"✅ Etsy data reloaded: {category} ({len(ETSY_DATASETS[category])} products)")
            
    except Exception as e:
        print(f"❌ Error saving CSV: {e}")
        traceback.print_exc()
load_csv_data()

from database import migrate_database
migrate_database()


# Start the background scheduler
start_scheduler()


# Helper functions for data cleaning
def clean_price(price_str, platform):
    if not isinstance(price_str, str):
        price_str = str(price_str)
    
    if platform == 'daraz':
        price_str = price_str.replace('Rs.', '').replace('Rs', '').replace('rs', '')
        price_str = price_str.replace('PKR', '').replace('pkr', '')
    else:
        price_str = price_str.replace('$', '').replace('USD', '').replace('usd', '')
    
    price_str = price_str.replace(',', '').replace('+', '').replace('~', '').strip()
    numbers = re.findall(r'\d+\.?\d*', price_str)
    if numbers:
        try:
            return float(numbers[0])
        except:
            pass
    return 0.0

def clean_rating(rating_str):
    if not rating_str or rating_str == '':
        return 0.0
    try:
        if isinstance(rating_str, (int, float)):
            return float(rating_str)
        rating_str = str(rating_str).strip()
        if rating_str and rating_str != '':
            return min(5.0, max(0.0, float(rating_str)))
    except:
        pass
    return 0.0

def clean_reviews(reviews_str):
    if not reviews_str or reviews_str == '':
        return 0
    try:
        if isinstance(reviews_str, (int, float)):
            return int(reviews_str)
        reviews_str = str(reviews_str).strip()
        if reviews_str and reviews_str != '':
            numbers = re.findall(r'\d+', reviews_str)
            if numbers:
                return int(numbers[0])
    except:
        pass
    return 0

def extract_daraz_products(subcategory, limit=100):
    products = []
    data = DARAZ_DATASETS.get(subcategory.lower())
    if not data:
        raise Exception(f"No data found for subcategory: {subcategory}")
    
    for idx, item in enumerate(data):
        if len(products) >= limit:
            break
        try:
            name = str(item.get('name', ''))
            if not name or len(name) < 3 or name == 'nan':
                continue
            
            price_str = str(item.get('price', '0'))
            price = clean_price(price_str, 'daraz')
            if price <= 0:
                continue
            
            rating = clean_rating(item.get('ratingScore', item.get('seller_rating', '0')))
            reviews = clean_reviews(item.get('itemSold', '0'))
            
            seller = str(item.get('sellerName', 'Unknown Seller'))
            if seller == 'nan':
                seller = 'Unknown Seller'
            
            brand = str(item.get('brandName', 'No Brand'))
            if brand == 'nan':
                brand = 'No Brand'
            
            popularity = min(1.0, reviews / 1000) if reviews > 0 else 0.1
            
            products.append({
                'name': name[:100],
                'price': price,
                'rating': rating,
                'reviews': reviews,
                'popularity': popularity,
                'seller': seller[:50],
                'brand': brand[:30]
            })
        except Exception as e:
            continue
    
    return products
import re

def extract_etsy_products(subcategory, limit=40):
    products = []
    data = ETSY_DATASETS.get(subcategory.lower())
    if not data:
        raise Exception(f"No Etsy data found for subcategory: {subcategory}")

    for item in data:
        if len(products) >= limit:
            break
        try:
            # ✅ Name
            name = str(item.get('name', ''))
            if not name or len(name) < 3:
                name = str(item.get('title', ''))
                if not name or len(name) < 3:
                    continue
            
            # ✅ Price - NESTED in "offers"
            offers = item.get('offers', {})
            price_str = offers.get('price', '0')
            try:
                price = float(price_str)
            except:
                price = 0.0
            
            # ✅ Rating
            rating = float(item.get('rating', item.get('ratingScore', 0)))
            
            # ✅ Reviews
            reviews = int(item.get('reviewCount', item.get('itemSold', 0)))
            
            # ✅ Brand
            brand_obj = item.get('brand', {})
            brand = str(brand_obj.get('slogan', brand_obj.get('brand', 'Etsy')))
            
            # ✅ Seller
            seller = str(item.get('shopName', item.get('sellerName', 'Unknown')))
            
            # ✅ URL
            product_url = str(item.get('url', item.get('itemUrl', '')))
            
            products.append({
                'name': name[:100],
                'price': price,
                'rating': rating,
                'reviews': reviews,
                'popularity': 0.0,
                'seller': seller[:50],
                'brand': brand[:30],
                'url': product_url[:200]
            })
            
        except Exception as e:
            print(f"⚠️ Error processing Etsy item: {e}")
            continue
    
    return products

def normalize_features(products, weights=None):
    if not products:
        return products
    
    if weights is None:
        weights = {"price": 1.0, "rating": 1.0, "reviews": 1.0, "popularity": 1.0}
    
    prices = [p['price'] for p in products]
    ratings = [p['rating'] for p in products]
    reviews = [p['reviews'] for p in products]
    
    price_min, price_max = min(prices), max(prices)
    review_min, review_max = min(reviews), max(reviews)
    
    for p in products:
        # Apply weights to normalized values
        if price_max > price_min:
            p['price_norm'] = (p['price'] - price_min) / (price_max - price_min) * weights['price']
        else:
            p['price_norm'] = 0.5 * weights['price']
        
        p['rating_norm'] = (p['rating'] / 5.0 if p['rating'] > 0 else 0.1) * weights['rating']
        
        if review_max > review_min:
            p['review_norm'] = (p['reviews'] - review_min) / (review_max - review_min) * weights['reviews']
        else:
            p['review_norm'] = 0.5 * weights['reviews']
        
        p['popularity_norm'] = p['popularity'] * weights['popularity']
    
    return products
def calculate_ranking_score(product):
    score = (product['rating_norm'] * 0.35 +
             product['review_norm'] * 0.30 +
             product['popularity_norm'] * 0.20 +
             (1 - product['price_norm']) * 0.15)
    return score

def apply_clustering(products, n_clusters=3, weights=None):
    if len(products) < n_clusters:
        n_clusters = max(2, len(products))
    
    features = [[p['price_norm'], p['rating_norm'], p['review_norm'], p['popularity_norm']] for p in products]
    X = np.array(features)
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X)
    
    centers = kmeans.cluster_centers_
    center_prices = [center[0] for center in centers]
    sorted_indices = np.argsort(center_prices)
    
    cluster_map = {old: new for new, old in enumerate(sorted_indices)}
    mapped_clusters = [cluster_map[c] for c in clusters]
    
    labels = []
    for i in range(n_clusters):
        if i == 0:
            labels.append("Budget")
        elif i == n_clusters - 1:
            labels.append("Premium")
        else:
            labels.append("Mid-Range")
    
    for i, p in enumerate(products):
        p['cluster'] = int(mapped_clusters[i])
        p['cluster_label'] = labels[mapped_clusters[i]]
        p['ranking_score'] = calculate_ranking_score(p)

    sil_score = 0.0
    if n_clusters >= 2 and len(products) >= n_clusters:
        try:
            sil_score = silhouette_score(X, mapped_clusters)
        except:
            sil_score = 0.0

    return products, centers, labels, sil_score
def calculate_polarization_score(products, centers, n_clusters):
    """Calculate polarization score based on cluster separation"""
    
    if len(centers) < 2 or len(products) < 10:
        return 0.50
    
    # Calculate between-cluster distances (how far apart clusters are)
    distances = []
    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            dist = np.linalg.norm(centers[i] - centers[j])
            distances.append(dist)
    
    avg_inter_dist = np.mean(distances) if distances else 0.5
    
    # Max possible distance in normalized space (0-1 for each dimension)
    # 4 dimensions: price_norm, rating_norm, review_norm, popularity_norm
    max_possible_dist = np.sqrt(4)  # = 2.0
    
    # Calculate within-cluster variance (how tight clusters are)
    intra_vars = []
    for c in range(n_clusters):
        feats = [[p['price_norm'], p['rating_norm'], p['review_norm'], p['popularity_norm']] 
                 for p in products if p.get('cluster') == c]
        if len(feats) > 1:
            intra_vars.append(np.var(feats, axis=0).mean())
    
    avg_intra = np.mean(intra_vars) if intra_vars else 0.1
    
    # Polarization formula: 
    # Higher inter-cluster distance = more polarization
    # Lower intra-cluster variance = more polarization
    if avg_intra == 0:
        avg_intra = 0.01
    
    # Raw score between 0 and 1
    raw_score = (avg_inter_dist / max_possible_dist) * (1 / (1 + avg_intra))
    
    # Scale to 0.2 to 0.95 range
    polarization_score = 0.2 + (raw_score * 0.75)
    
    # Clamp to valid range
    polarization_score = max(0.20, min(0.95, polarization_score))
    
    return round(polarization_score, 3)

def generate_insights(trend_data, analysis_type="current"):
    """Generate smart business insights"""
    if not trend_data or len(trend_data) < 2:
        return {
            "summary": "Not enough historical data for insights.",
            "percent_change": 0,
            "direction": "stable"
        }
    
    scores = [item.get('polarization_score', 0) for item in trend_data]
    current = scores[-1]
    previous = scores[-2] if len(scores) > 1 else current
    
    change = current - previous
    percent_change = (change / previous * 100) if previous > 0 else 0
    
    direction = "increased" if change > 0 else "decreased"
    
    summary = f"Polarization has {direction} by {abs(percent_change):.1f}% in the selected period."
    
    if abs(percent_change) > 12:
        summary += " This is a significant shift in market structure."
    
    return {
        "summary": summary,
        "current_score": round(current, 3),
        "percent_change": round(percent_change, 1),
        "direction": direction,
        "trend_strength": "Strong" if abs(percent_change) > 10 else "Moderate"
    }
def get_polarization_level(score):
    if score < 0.25:
        return "Low Polarization"
    elif score < 0.45:
        return "Medium Polarization"
    elif score < 0.65:
        return "High Polarization"
    else:
        return "Very High Polarization"
    
@app.post("/api/analyze-custom")
async def analyze_custom_duration(
    request: CustomAnalysisRequest,
    auth_data: dict = Depends(verify_jwt_token) 
):
    username = auth_data["username"]
    role = auth_data["role"]
    """
    Custom duration analysis
    request.unit = 'days' ya 'weeks'
    request.duration = 3, 5, 7 (for days) ya 2, 3, 4 (for weeks)
    """
    
    platform = request.platform
    category = request.category.lower()
    unit = request.unit
    duration = request.duration

    # ✅ GET CUSTOM PARAMETERS FROM REQUEST
    custom_k = request.k_value if request.k_value else 3
    weights = request.weights if request.weights else {
        "price": 1.0, "rating": 1.0, "reviews": 1.0, "popularity": 1.0
    }
    
    # ✅ AGAR RESEARCH ANALYST HAI TOH SAVED PARAMS USE KAREIN
    if role == "Research Analyst" and username and username in research_analyst_params:
        saved_k = research_analyst_params[username].get("k_value")
        saved_weights = research_analyst_params[username].get("weights")
        if custom_k == 3 and saved_k:
            custom_k = saved_k
        if weights == {"price": 1.0, "rating": 1.0, "reviews": 1.0, "popularity": 1.0}:
            if saved_weights:
                weights = saved_weights
    
    print(f"📊 CUSTOM ANALYSIS: k={custom_k}, weights={weights}")

    if platform == "daraz":
        platform = "Daraz.pk"
    elif platform == "etsy":
        platform = "Etsy.com"
    
    
    from database import get_daily_snapshots, get_weekly_snapshots
    from datetime import datetime, timedelta
    import pandas as pd
    
    if unit == 'days':
        # Get ALL data without date filter
        snapshots = get_daily_snapshots(platform, category)  # No start_date/end_date
        
        print(f"📊 Raw data from database for {category}:")
        
        if len(snapshots) == 0:
            print("   No data found in daily_snapshots table!")
            return await calculate_from_csv(platform, category)
        
        data = []
        for s in snapshots:
            print(f"   {s['date']} -> {s['polarization_score']}")
            data.append({'snapshot_date': s['date'], 'polarization_score': s['polarization_score']})
        
        df = pd.DataFrame(data)
        
        # Take last 'duration' records
        if len(df) > duration:
            df = df.tail(duration)
        
        # ✅ SET START_DATE AND END_DATE FROM AVAILABLE DATA
        if len(df) > 0:
            start_date = datetime.strptime(str(df['snapshot_date'].iloc[0]), '%Y-%m-%d')
            end_date = datetime.strptime(str(df['snapshot_date'].iloc[-1]), '%Y-%m-%d')
        else:
            start_date = datetime.now()
            end_date = datetime.now()
        
        print(f"📅 Date range: {start_date.date()} to {end_date.date()}")
        
    elif unit == 'weeks':
        # Get weekly data from database
        snapshots = get_weekly_snapshots(platform, category, duration * 2)
    
        print(f"📊 Raw weekly data from database for {category}:")
    
        if len(snapshots) == 0:
            print("   No weekly data found! Run Weekly Analysis first.")
            # Fallback to daily data if no weekly data
            return await calculate_from_csv(platform, category)
    
        data = []
        for s in snapshots:
            # Ensure date is properly formatted
            date_val = s['date']
            if isinstance(date_val, str):
                date_val = date_val.split(' ')[0]  # Remove time part if exists
            print(f"   {date_val} -> {s['polarization_score']}")
            data.append({'analysis_date': date_val, 'polarization_score': s['polarization_score']})
        
        df = pd.DataFrame(data)
        
        if len(df) > duration:
            df = df.tail(duration)
        
        # ✅ SET START_DATE AND END_DATE FROM AVAILABLE DATA
        if len(df) > 0:
            # Pehle string ko split karke sirf date part lo
            date_str = str(df['analysis_date'].iloc[0]).split(' ')[0]  # "2026-05-30 20:02:56" -> "2026-05-30"
            start_date = datetime.strptime(date_str, '%Y-%m-%d')
            date_str_end = str(df['analysis_date'].iloc[-1]).split(' ')[0]
            end_date = datetime.strptime(date_str_end, '%Y-%m-%d')
        else:
            start_date = datetime.now()
            end_date = datetime.now()
    
    else:
        raise HTTPException(status_code=400, detail="Invalid unit. Use 'days' or 'weeks'")
    
    if df.empty:
        return await calculate_from_csv(platform, category)
    
    avg_polarization = df['polarization_score'].mean()
    
    if len(df) >= 2:
        first_score = df['polarization_score'].iloc[0]
        last_score = df['polarization_score'].iloc[-1]
        if last_score > first_score * 1.05:
            trend = "increasing"
        elif last_score < first_score * 0.95:
            trend = "decreasing"
        else:
            trend = "stable"
    else:
        trend = "stable"
    
    result = {
        "platform": platform,
        "category": category,
        "duration": duration,
        "unit": unit,
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": end_date.strftime('%Y-%m-%d'),
        "avg_polarization_score": round(avg_polarization, 4),
        "trend": trend,
        "data_points": len(df),
        "daily_scores": [float(x) for x in df['polarization_score'].tolist()],
        "dates": [str(x) for x in (df['snapshot_date'].tolist() if unit == 'days' else df['analysis_date'].tolist())]
    }
    
    print(f"✅ Returning {result['data_points']} days, scores: {result['daily_scores']}")
    print(f"📅 Start: {result['start_date']}, End: {result['end_date']}")
    return result
async def calculate_from_csv(platform, category):
    """Fallback function jab database mein data nahi ho"""
    # Create a request object
    request = AnalysisRequest(
        platform=platform,
        category=category,
        subcategory=category,
        max_products=50,
        analysis_type='current',
        save_to_db=True
    )
    result = await analyze_polarization(request)
    
    # ✅ FIX: result ek dictionary hai, object nahi
    return {
        "platform": platform,
        "category": category,
        "duration": 0,
        "unit": "days",
        "start_date": datetime.now().strftime('%Y-%m-%d'),
        "end_date": datetime.now().strftime('%Y-%m-%d'),
        "avg_polarization_score": result.get('polarization_score', 0.5),  # <-- FIXED
        "trend": "stable",
        "data_points": 1,
        "daily_scores": [result.get('polarization_score', 0.5)],  # <-- FIXED
        "dates": [datetime.now().strftime('%Y-%m-%d')],
        "note": "Using current data (no historical data available)"
    }



@app.get("/api/comparison/{platform}/{category}")
async def get_comparison(platform: str, category: str):
    """Get comparison between current, weekly, and monthly polarization"""
    try:
        from database import get_polarization_comparison, get_all_historical_data
        
        # ✅ Try to get current analysis
        current_data = get_current_analysis(platform, category)
        
        # ✅ Agar current data nahi hai toh default return karein
        if not current_data:
            return {
                "current": None,
                "weekly_avg": None,
                "monthly_avg": None,
                "weekly_trend": "No data",
                "monthly_trend": "No data",
                "historical_data": {}
            }
        
        comparison = get_polarization_comparison(platform, category)
        historical = get_all_historical_data(platform, category)

        weekly_avg = comparison.get('weekly_avg')
        monthly_avg = comparison.get('monthly_avg')
        
        # ✅ Convert to float if needed
        if weekly_avg is not None:
            try:
                weekly_avg = float(weekly_avg)
            except (ValueError, TypeError):
                weekly_avg = None
        
        if monthly_avg is not None:
            try:
                monthly_avg = float(monthly_avg)
            except (ValueError, TypeError):
                monthly_avg = None
        
        return {
            "current": current_data,
            "weekly_avg": comparison.get('weekly_avg'),
            "monthly_avg": comparison.get('monthly_avg'),
            "weekly_trend": comparison.get('weekly_trend', 'Stable'),
            "monthly_trend": comparison.get('monthly_trend', 'Stable'),
            "historical_data": historical or {}
        }
    except Exception as e:
        print(f"❌ Comparison error: {e}")
        # ✅ Error ke bajaye default response return karein
        return {
            "current": None,
            "weekly_avg": None,
            "monthly_avg": None,
            "weekly_trend": "No data",
            "monthly_trend": "No data",
            "historical_data": {},
            "error": str(e)
        }

@app.get("/api/daily-products/{platform}/{category}/{date}")
async def get_daily_products(platform: str, category: str, date: str):
    """Get top 10 products for a specific date"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Convert date string to datetime
        from datetime import datetime
        target_date = datetime.strptime(date, '%Y-%m-%d').date()
        
        # Fetch analysis for that date
        cursor.execute("""
            SELECT top_products 
            FROM polarization_analysis 
            WHERE platform = ? AND category = ? 
            AND DATE(analysis_date) = ?
            ORDER BY analysis_date DESC 
            LIMIT 1
        """, (platform, category, target_date))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            products = json.loads(row[0])
            return {"date": date, "products": products[:10], "total": len(products)}
        else:
            # If no data, return empty
            return {"date": date, "products": [], "total": 0, "message": "No data available for this date"}
            
    except Exception as e:
        print(f"Error: {e}")
        return {"date": date, "products": [], "error": str(e)}
    
@app.get("/api/historical/{platform}/{category}")
async def get_historical(platform: str, category: str):
    """Get complete historical polarization data"""
    try:
        return {
            "platform": platform,
            "category": category,
            "weekly_data": get_weekly_analysis(platform, category),
            "monthly_data": get_monthly_analysis(platform, category),
            "trend_data": get_trend_data(platform, category, "weekly", 12)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/collect-weekly")
async def collect_weekly_data(background_tasks: BackgroundTasks):
    """Manually trigger weekly data collection"""
    from scheduler import scheduler
    background_tasks.add_task(scheduler.collect_weekly_data)
    return {"message": "Weekly data collection started in background"}

if __name__ == "__main__":
   
    print("\n" + "="*60)
    print("🌐 API STARTING - TIME-BASED ANALYSIS MODE")
    print("="*60)
    print("\n📅 Features:")
    print("   - Current polarization analysis")
    print("   - Weekly trend analysis")
    print("   - Monthly trend analysis")
    print("   - Historical data comparison")
    print("   - Automatic weekly data collection")
    print("\n🚀 Server running at: http://localhost:8000")
    print("="*60)
 