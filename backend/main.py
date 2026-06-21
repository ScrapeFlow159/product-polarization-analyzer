from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Response, status
from pydantic import BaseModel
from typing import List, Dict, Optional
import pandas as pd
import json  # ← YEH LINE ADD KARO (pehle se nahi hai)
import numpy as np
from fastapi.middleware.wsgi import WSGIMiddleware
from sklearn.metrics import silhouette_score
from sklearn.cluster import KMeans
import sqlite3
from database import DB_PATH  # <-- YEH LINE ADD KARO
import traceback
import os
from datetime import datetime, timedelta
import re
from flask_app import app as flask_app
from database import (
    save_analysis_result, get_current_analysis, get_weekly_analysis,
    get_monthly_analysis, get_polarization_comparison, save_time_snapshot,
    get_trend_data, get_all_historical_data,
    save_daily_snapshot, get_daily_snapshots, get_weekly_snapshots  # <-- YEH ADD KARO
)
from scheduler import start_scheduler
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
import sqlite3
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
from pydantic import BaseModel


app = FastAPI(title="Product Polarization API - Time-Based Analysis",
              description="Analyze product polarization with weekly/monthly trends",
              version="5.0.0")

import csv
from io import StringIO
from fastapi.responses import StreamingResponse

origins = [
    "https://product-polarization-analyzer.vercel.app",
    "http://localhost:3000",  # Agar local testing karni ho
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Ya testing ke liye ["*"] rakh sakte hain
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)

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

class CustomAnalysisRequest(BaseModel):
    platform: str
    category: str
    unit: str  # 'days' ya 'weeks'
    duration: int  # 3,5,7 for days / 2,3,4 for weeks
    max_products: Optional[int] = 50

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




@app.post("/api/analyze")
async def analyze_polarization(
    request: AnalysisRequest,
    username: str = None,
    role: str = None
):
    """Main analysis endpoint with time-based analysis support"""
    try:
        print(f"\n{'='*60}")
        print(f"🔍 Analyzing {request.platform.upper()} - {request.subcategory}")
        print(f"   Type: {request.analysis_type}")
        print(f"   User: {username}, Role: {role}")
        print(f"{'='*60}")
        
        # ========== GET CUSTOM PARAMETERS ==========
        custom_k = 3
        weights = {"price": 1.0, "rating": 1.0, "reviews": 1.0, "popularity": 1.0}
        
        if role == "Research Analyst" and username and username in research_analyst_params:
            custom_k = research_analyst_params[username].get("k_value", 3)
            weights = research_analyst_params[username].get("weights", weights)
            print(f"📊 USING CUSTOM PARAMETERS: k={custom_k}, weights={weights}")
        else:
            print(f"📊 Using DEFAULT parameters")
        
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
            analysis_type=request.analysis_type
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
    platform: str, 
    category: str, 
    analysis_type: str = "current",
    username: str = None,
    role: str = None
):
    """Export analysis results as CSV"""
    try:
        print(f"📊 Export requested: platform={platform}, category={category}, type={analysis_type}")
        
        # Check authorization
        if role not in ["Research Analyst", "Admin"]:
            raise HTTPException(status_code=403, detail="Only Research Analyst and Admin can export data")
        
        import sqlite3
        from database import DB_PATH
        import json
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Try to get data - first check polarization_analysis
        cursor.execute('''
            SELECT * FROM polarization_analysis 
            WHERE platform LIKE ? AND category = ? 
            ORDER BY analysis_date DESC LIMIT 1
        ''', (f'%{platform}%', category))
        
        row = cursor.fetchone()
        
        if not row:
            # Try without platform filter
            cursor.execute('''
                SELECT * FROM polarization_analysis 
                WHERE category = ? 
                ORDER BY analysis_date DESC LIMIT 1
            ''', (category,))
            row = cursor.fetchone()
        
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"No data found for {category}. Please run Current Analysis first.")
        
        # Parse the data (adjust indices based on your table schema)
        # polarization_analysis table columns:
        # 0:id,1:platform,2:category,3:analysis_type,4:analysis_date,5:week_number,6:month_number,7:year,
        # 8:total_products,9:polarization_score,10:polarization_level,11:silhouette_score,
        # 12:cluster_data,13:feature_importance,14:top_products
        
        data = {
            'platform': row[1],
            'category': row[2],
            'analysis_type': row[3],
            'analysis_date': row[4],
            'total_products': row[8],
            'polarization_score': row[9],
            'polarization_level': row[10],
            'silhouette_score': row[11],
            'clusters': json.loads(row[12]) if row[12] else [],
            'top_products': json.loads(row[14]) if row[14] else []
        }
        
        print(f"✅ Found data: {data['platform']}/{data['category']} - Score: {data['polarization_score']}")
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Platform', 'Category', 'Analysis Type', 'Analysis Date', 
                        'Total Products', 'Polarization Score', 'Polarization Level', 'Silhouette Score'])
        
        writer.writerow([
            data['platform'],
            data['category'],
            data['analysis_type'],
            str(data['analysis_date']),
            data['total_products'],
            data['polarization_score'],
            data['polarization_level'],
            data['silhouette_score']
        ])
        
        writer.writerow([])
        writer.writerow(['CLUSTER DETAILS'])
        writer.writerow(['Cluster Label', 'Size', 'Avg Price', 'Avg Rating', 'Percentage'])
        
        for cluster in data['clusters']:
            writer.writerow([
                cluster.get('label', ''),
                cluster.get('size', 0),
                cluster.get('avg_price', 0),
                cluster.get('avg_rating', 0),
                cluster.get('percentage', 0)
            ])
        
        writer.writerow([])
        writer.writerow(['TOP 10 PRODUCTS'])
        writer.writerow(['Rank', 'Product Name', 'Price', 'Rating', 'Reviews', 'Popularity', 'Cluster'])
        
        for idx, product in enumerate(data['top_products'][:10], 1):
            writer.writerow([
                idx,
                product.get('name', ''),
                product.get('price', 0),
                product.get('rating', 0),
                product.get('reviews', 0),
                product.get('popularity_score', 0),
                product.get('cluster_label', '')
            ])
        
        output.seek(0)
        filename = f"{platform}_{category}_{data['analysis_type']}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Export error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))






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
async def get_parameters(username: str = None, role: str = None):
    """Get current parameters for the user"""
    print(f"📊 Get params called: username={username}, role={role}")
    
    # Default parameters for all users
    default_params = {
        "k_value": 3,
        "weights": {
            "price": 1.0,
            "rating": 1.0,
            "reviews": 1.0,
            "popularity": 1.0
        }
    }
    
    # Only Research Analyst can have custom parameters
    if role == "Research Analyst" and username and username in research_analyst_params:
        print(f"✅ Returning custom params for {username}")
        return research_analyst_params[username]
    
    print(f"✅ Returning default params for {role}")
    return default_params




@app.post("/api/set-params")
async def set_parameters(params: AnalysisParams):
    """Set analysis parameters for Research Analyst"""
    global analysis_params
    analysis_params["k_value"] = params.k_value
    analysis_params["weights"]["price"] = params.price_weight
    analysis_params["weights"]["rating"] = params.rating_weight
    analysis_params["weights"]["reviews"] = params.reviews_weight
    analysis_params["weights"]["popularity"] = params.popularity_weight
    return {"message": "Parameters updated successfully", "params": analysis_params}
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
async def apify_webhook(request: dict):
    print("\n🔥 WEBHOOK RECEIVED")
    print("FULL DATA:")
    print(request)

    # Extract category (we will use later)
    category = request.get("resource", {}).get("input", {}).get("category")

    print("CATEGORY RECEIVED:", category)

    return {"status": "received", "category": category}

load_csv_data()

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

def extract_etsy_products(subcategory, limit=100):
    products = []
    data = ETSY_DATASETS.get(subcategory.lower())
    if not data:
        raise Exception(f"No Etsy data found for subcategory: {subcategory}")

    for idx, item in enumerate(data):
        if len(products) >= limit:
            break
        try:
            name = str(item.get('name', ''))
            if not name or len(name) < 3 or name == 'nan':
                continue

            price_str = str(item.get('Price', '0'))
            price = clean_price(price_str, 'etsy')
            if price <= 0:
                continue

            rating = clean_rating(item.get('ratingScore', item.get('seller_rating', '0')))
            reviews = clean_reviews(item.get('numberOfReviews', '0'))
            favorites = clean_reviews(item.get('favorites', '0'))

            seller = str(item.get('seller_name', 'Unknown Seller'))
            if seller == 'nan':
                seller = 'Unknown Seller'

            popularity = min(1.0, favorites / 3000) if favorites > 0 else 0.1

            products.append({
                'name': name[:100],
                'price': price,
                'rating': rating,
                'reviews': reviews,
                'popularity': popularity,
                'seller': seller[:50],
                'brand': 'Etsy Handmade'
            })
        except Exception as e:
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
async def analyze_custom_duration(request: CustomAnalysisRequest):
    """
    Custom duration analysis
    request.unit = 'days' ya 'weeks'
    request.duration = 3, 5, 7 (for days) ya 2, 3, 4 (for weeks)
    """
    
    platform = request.platform
    category = request.category.lower()
    unit = request.unit
    duration = request.duration

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
        comparison = get_polarization_comparison(platform, category)
        historical = get_all_historical_data(platform, category)
        
        return TimeComparisonResponse(
            current=get_current_analysis(platform, category),
            weekly_avg=comparison['weekly_avg'],
            monthly_avg=comparison['monthly_avg'],
            weekly_trend=comparison['weekly_trend'],
            monthly_trend=comparison['monthly_trend'],
            historical_data=historical
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    import uvicorn
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
    
#uvicorn.run(app, host="0.0.0.0", port=8000)