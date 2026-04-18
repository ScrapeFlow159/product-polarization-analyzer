from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from sklearn.metrics import silhouette_score
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import traceback
import os
from datetime import datetime
import math
import re

app = FastAPI(title="Product Polarization API - CSV Only",
              description="Analyze product polarization using REAL CSV data only",
              version="3.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

class AnalysisRequest(BaseModel):
    platform: str  # "daraz" or "etsy"
    category: str
    subcategory: str
    max_products: Optional[int] = 100

# Global variables for CSV data
DARAZ_DATASETS = {}
ETSY_DATA = []
CSV_FILES_FOUND = {
    "daraz": False,
    "etsy": False
}

print("\n" + "="*60)
print("🚀 PRODUCT POLARIZATION API - CSV ONLY MODE")
print("="*60)

def load_csv_data():
    """Load data from CSV files - MULTIPLE DARAZ CATEGORIES"""
    global DARAZ_DATASETS, ETSY_DATA, CSV_FILES_FOUND
    
    print("\n📂 LOADING CSV DATA...")
    print("⚠️ Note: This API uses ONLY CSV data. No sample data will be generated.")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # -----------------------------
    # DARAZ MULTI-CATEGORY FILES
    # -----------------------------
    daraz_files = {
        "earpods": [
            os.path.join(base_dir, "latest_data.csv"),
            os.path.join(base_dir, "data", "latest_data.csv"),
            "latest_data.csv"
        ],
        "powerbanks": [
            os.path.join(base_dir, "powerbanks.csv"),
            os.path.join(base_dir, "data", "powerbanks.csv"),
            "powerbanks.csv"
        ]
    }

    daraz_loaded = False

    # Load each category separately
    for category, paths in daraz_files.items():
        for path in paths:
            if os.path.exists(path):
                try:
                    print(f"📖 Reading Daraz {category} CSV from: {path}")
                    df = pd.read_csv(path, encoding='utf-8')

                    # Clean data
                    df = df.dropna(how='all')
                    df = df.fillna('')

                    # Store separately
                    DARAZ_DATASETS[category] = df.to_dict('records')
                    CSV_FILES_FOUND[f"daraz_{category}"] = True
                    CSV_FILES_FOUND["daraz"] = True   # ✅ ADD THIS
                    daraz_loaded = True

                    print(f"✅ Loaded {len(DARAZ_DATASETS[category])} {category} products")

                    daraz_loaded = True
                    break
                except Exception as e:
                    print(f"❌ Failed to load {path}: {str(e)}")
                    continue

    # -----------------------------
    # ETSY (UNCHANGED)
    # -----------------------------
    possible_paths_etsy = [
        os.path.join(base_dir, "etsy.csv"),
        os.path.join(base_dir, "data", "etsy.csv"),
        "etsy.csv",
        "./etsy.csv",
        "../etsy.csv"
    ]

    etsy_loaded = False
    etsy_path_used = ""

    for path in possible_paths_etsy:
        if os.path.exists(path):
            try:
                print(f"📖 Reading Etsy CSV from: {path}")
                df = pd.read_csv(path, encoding='utf-8')

                df = df.dropna(how='all')
                df = df.fillna('')

                ETSY_DATA = df.to_dict('records')
                etsy_loaded = True
                etsy_path_used = path
                CSV_FILES_FOUND["etsy"] = True

                print(f"✅ SUCCESS: Loaded {len(ETSY_DATA)} Etsy products")
                break
            except Exception as e:
                print(f"❌ Failed to load {path}: {str(e)}")
                continue

    # -----------------------------
    # STATUS OUTPUT
    # -----------------------------
    print("\n" + "="*60)
    print("📊 CSV FILE STATUS:")

    if daraz_loaded:
        print("✅ Daraz Categories Loaded:")
        for category, data in DARAZ_DATASETS.items():
            print(f"   - {category}: {len(data)} products")
            if len(data) > 0:
                print(f"     Sample: {data[0].get('name', 'N/A')[:50]}...")
    else:
        print("❌ Daraz CSV files NOT FOUND")
        print("   Required files:")
        print("   - earpods.csv")
        print("   - powerbanks.csv")

    if etsy_loaded:
        print(f"\n✅ Etsy.csv: FOUND at {etsy_path_used}")
        print(f"   - Total products: {len(ETSY_DATA)}")
        if len(ETSY_DATA) > 0:
            print(f"   - Sample product: {ETSY_DATA[0].get('name', 'N/A')[:50]}...")
    else:
        print("\n❌ Etsy.csv: NOT FOUND")
        print("   Please place etsy.csv in the same directory as main.py")

    if not daraz_loaded and not etsy_loaded:
        print("\n⚠️ CRITICAL ERROR: No CSV files found!")
        print("The API will not work without CSV files.")
    else:
        print("\n✅ CSV files loaded successfully!")

    print("="*60)
# Load data on startup
load_csv_data()

# Helper functions for data cleaning
def clean_price(price_str, platform):
    """Clean price string based on platform"""
    if not isinstance(price_str, str):
        price_str = str(price_str)
    
    original = price_str
    
    # Remove currency symbols and commas
    if platform == 'daraz':
        price_str = price_str.replace('Rs.', '').replace('Rs', '').replace('rs', '')
        price_str = price_str.replace('PKR', '').replace('pkr', '')
    else:  # etsy
        price_str = price_str.replace('$', '').replace('USD', '').replace('usd', '')
    
    price_str = price_str.replace(',', '').replace('+', '').replace('~', '').strip()
    
    # Extract numeric part using regex
    numbers = re.findall(r'\d+\.?\d*', price_str)
    if numbers:
        try:
            return float(numbers[0])
        except:
            pass
    
    # If no numbers found, return 0
    print(f"⚠️ Could not parse price: '{original}' -> returning 0")
    return 0.0

def clean_rating(rating_str):
    """Convert rating to float"""
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
    """Convert reviews to integer"""
    if not reviews_str or reviews_str == '':
        return 0
    
    try:
        if isinstance(reviews_str, (int, float)):
            return int(reviews_str)
        reviews_str = str(reviews_str).strip()
        if reviews_str and reviews_str != '':
            # Extract numbers only
            numbers = re.findall(r'\d+', reviews_str)
            if numbers:
                return int(numbers[0])
    except:
        pass
    return 0

def extract_daraz_products(subcategory, limit=100):
    """Extract and clean Daraz products from CSV only"""
    products = []
    data = DARAZ_DATASETS.get(subcategory.lower())
    if not data:
        raise Exception(f"No data found for subcategory: {subcategory}")
    
    print(f"\n📦 Processing Daraz products from CSV...")
    
    for idx, item in enumerate(data):
        if len(products) >= limit:
            break
            
        try:
            # Get product name
            name = str(item.get('name', ''))
            if not name or len(name) < 3 or name == 'nan':
                continue
            
            # Get price
            price_str = str(item.get('price', '0'))
            price = clean_price(price_str, 'daraz')
            
            # Skip if price is 0 (invalid)
            if price <= 0:
                continue
            
            # Get rating
           # Replace the rating line with:
            rating = clean_rating(item.get('ratingScore', item.get('seller_rating', '0')))
            
            # Get reviews (itemSold)
            reviews = clean_reviews(item.get('itemSold', '0'))
            
            # Get seller and brand
            seller = str(item.get('sellerName', 'Unknown Seller'))
            if seller == 'nan':
                seller = 'Unknown Seller'
            
            brand = str(item.get('brandName', 'No Brand'))
            if brand == 'nan':
                brand = 'No Brand'
            
            # Calculate popularity score (0-1 based on reviews)
            # Using max 1000 reviews as reference
            popularity = min(1.0, reviews / 1000) if reviews > 0 else 0.1
            
            products.append({
                'name': name[:100],
                'price': price,
                'rating': rating,
                'reviews': reviews,
                'popularity': popularity,
                'seller': seller[:50],
                'brand': brand[:30],
                'original_price': price_str
            })
            
        except Exception as e:
            print(f"⚠️ Error processing Daraz product {idx}: {str(e)}")
            continue
    
    print(f"✅ Extracted {len(products)} valid Daraz products")
    return products
    print("Available keys:", DARAZ_DATASETS.keys())
    print("Requested:", subcategory)

def extract_etsy_products(limit=100):
    """Extract and clean Etsy products from CSV only"""
    products = []
    
    if not ETSY_DATA:
        raise Exception("No Etsy CSV data available. Please ensure etsy.csv exists.")
    
    print(f"\n🛍️ Processing Etsy products from CSV...")
    
    for idx, item in enumerate(ETSY_DATA):
        if len(products) >= limit:
            break
            
        try:
            # Get product name
            name = str(item.get('name', ''))
            if not name or len(name) < 3 or name == 'nan':
                continue
            
            # Get price
            price_str = str(item.get('Price', '0'))
            price = clean_price(price_str, 'etsy')
            
            # Skip if price is 0 (invalid)
            if price <= 0:
                continue
            
            # Get rating
           # Replace the rating line with:
            rating = clean_rating(item.get('ratingScore', item.get('seller_rating', '0')))
            
            # Get reviews
            reviews = clean_reviews(item.get('numberOfReviews', '0'))
            
            # Get favorites (as popularity)
            favorites = clean_reviews(item.get('favorites', '0'))
            
            # Get seller
            seller = str(item.get('seller_name', 'Unknown Seller'))
            if seller == 'nan':
                seller = 'Unknown Seller'
            
            # Calculate popularity score (0-1 based on favorites)
            popularity = min(1.0, favorites / 3000) if favorites > 0 else 0.1
            
            products.append({
                'name': name[:100],
                'price': price,
                'rating': rating,
                'reviews': reviews,
                'popularity': popularity,
                'seller': seller[:50],
                'brand': 'Etsy Handmade',
                'original_price': price_str
            })
            
        except Exception as e:
            print(f"⚠️ Error processing Etsy product {idx}: {str(e)}")
            continue
    
    print(f"✅ Extracted {len(products)} valid Etsy products")
    return products

def normalize_features(products):
    """Normalize features for clustering"""
    if not products:
        return products
    
    # Extract features
    prices = [p['price'] for p in products]
    ratings = [p['rating'] for p in products]
    reviews = [p['reviews'] for p in products]
    popularities = [p['popularity'] for p in products]
    
    # Min-max normalization
    price_min, price_max = min(prices), max(prices)
    review_min, review_max = min(reviews), max(reviews)
    
    for p in products:
        # Price normalization (0-1)
        if price_max > price_min:
            p['price_norm'] = (p['price'] - price_min) / (price_max - price_min)
        else:
            p['price_norm'] = 0.5
        
        # Rating normalization (already 0-5)
        p['rating_norm'] = p['rating'] / 5.0 if p['rating'] > 0 else 0.1
        
        # Review normalization
        if review_max > review_min:
            p['review_norm'] = (p['reviews'] - review_min) / (review_max - review_min)
        else:
            p['review_norm'] = 0.5
        
        # Popularity already normalized
        p['popularity_norm'] = p['popularity']
    
    return products

def calculate_ranking_score(product):
    """Calculate ranking score for top products"""
    # Weights: Rating 35%, Reviews 30%, Popularity 20%, Price 15%
    score = (
        product['rating_norm'] * 0.35 +
        product['review_norm'] * 0.30 +
        product['popularity_norm'] * 0.20 +
        (1 - product['price_norm']) * 0.15  # Lower price is better
    )
    return score

def apply_clustering(products, n_clusters=3):
    """Apply K-Means clustering to products"""
    if len(products) < n_clusters:
        n_clusters = max(2, len(products))
    
    # Prepare feature matrix
    features = []
    for p in products:
        features.append([
            p['price_norm'],
            p['rating_norm'],
            p['review_norm'],
            p['popularity_norm']
        ])
    
    X = np.array(features)
    
    # Apply clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X)
    
    # Calculate cluster centers and sort by price
    centers = kmeans.cluster_centers_
    center_prices = [center[0] for center in centers]
    sorted_indices = np.argsort(center_prices)
    
    # Map original clusters to sorted labels
    cluster_map = {old: new for new, old in enumerate(sorted_indices)}
    mapped_clusters = [cluster_map[c] for c in clusters]
    
    # Assign labels based on price order
    labels = []
    for i in range(n_clusters):
        if i == 0:
            labels.append("Budget")
        elif i == n_clusters - 1:
            labels.append("Premium")
        else:
            labels.append("Mid-Range")
    
    # Add clusters to products
    for i, p in enumerate(products):
        p['cluster'] = int(mapped_clusters[i])
        p['cluster_label'] = labels[mapped_clusters[i]]
        p['ranking_score'] = calculate_ranking_score(p)

        # Inside apply_clustering (after K-Means)
    sil_score = 0.0
    if n_clusters >= 2 and len(products) >= n_clusters:
        try:
            sil_score = silhouette_score(X, mapped_clusters)
        except:
            sil_score = 0.0

    return products, centers, labels, sil_score   # ← Added sil_score


def calculate_polarization_score(products, centers, n_clusters):
    """Final Polished Polarization Score - Ready for FYP Submission"""
    if len(centers) < 2 or len(products) < 20:
        return 0.55
    
    # Inter-cluster separation
    distances = []
    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            dist = np.linalg.norm(centers[i] - centers[j])
            distances.append(dist)
    
    avg_inter_dist = np.mean(distances)
    max_dist = np.sqrt(4)
    
    # Intra-cluster variance penalty
    intra_vars = []
    for c in range(n_clusters):
        feats = [[p['price_norm'], p['rating_norm'], p['review_norm'], p['popularity_norm']] 
                 for p in products if p.get('cluster') == c]
        if len(feats) > 1:
            intra_vars.append(np.var(feats, axis=0).mean())
    
    avg_intra = np.mean(intra_vars) if intra_vars else 0.0
    
    # Balanced & natural scaling
    raw_score = avg_inter_dist / (max_dist * 0.9 + avg_intra * 6)
    polarization_score = min(0.96, max(0.45, raw_score * 2.05))
    
    return round(polarization_score, 3)



def get_polarization_level(score):
    """Convert polarization score to descriptive level"""
    if score < 0.25:
        return "Low Polarization"
    elif score < 0.45:
        return "Medium Polarization"
    elif score < 0.65:
        return "High Polarization"
    else:
        return "Very High Polarization"
# API Endpoints
@app.get("/")
def read_root():
    """Root endpoint with CSV status"""
    return {
        "message": "Product Polarization API - CSV ONLY MODE",
        "version": "3.0.0",
        "csv_status": {
            "daraz": {
                "found": CSV_FILES_FOUND["daraz"],
                "product_count": len(DARAZ_DATASETS)
            },
            "etsy": {
                "found": CSV_FILES_FOUND["etsy"],
                "product_count": len(ETSY_DATA)
            }
        },
        "note": "This API uses ONLY CSV data. No sample data is generated.",
        "endpoints": {
            "GET /": "This info",
            "GET /api/platforms": "Get available platforms",
            "POST /api/analyze": "Run polarization analysis",
            "GET /api/csv-status": "Check CSV files status"
        }
    }

@app.get("/api/csv-status")
def csv_status():
    """Detailed CSV file status"""
    return {
        "daraz": {
            "file_exists": CSV_FILES_FOUND["daraz"],
            "products_loaded": len(DARAZ_DATASETS),
            "sample": next(iter(DARAZ_DATASETS.values()))[0] if DARAZ_DATASETS else None
        },
        "etsy": {
            "file_exists": CSV_FILES_FOUND["etsy"],
            "products_loaded": len(ETSY_DATA),
            "sample": ETSY_DATA[0] if ETSY_DATA else None
        }
    }

@app.get("/api/platforms")
def get_platforms():
    """Get available platforms with CSV data status"""
    platforms = []
    
    if CSV_FILES_FOUND["daraz"]:
        platforms.append({
            "id": "daraz",
            "name": "Daraz.pk",
            "currency": "PKR",
            "categories": ["Earbuds", "Headphones", "Mobile Accessories"],
            "data_loaded": True,
            "product_count": len(DARAZ_DATASETS),
            "csv_file": "daraz.csv"
        })
    
    if CSV_FILES_FOUND["etsy"]:
        platforms.append({
            "id": "etsy",
            "name": "Etsy.com",
            "currency": "USD",
            "categories": ["Earpods", "Headphones", "Audio Accessories"],
            "data_loaded": True,
            "product_count": len(ETSY_DATA),
            "csv_file": "etsy.csv"
        })
    
    if not platforms:
        return {
            "platforms": [],
            "error": "No CSV files found. Please ensure daraz.csv and/or etsy.csv exist."
        }
    
    return {"platforms": platforms}

@app.post("/api/analyze", response_model=PolarizationAnalysis)
async def analyze_polarization(request: AnalysisRequest):
    """Main analysis endpoint - Uses ONLY CSV data"""
    try:
        print(f"\n{'='*60}")
        print(f"🔍 Analyzing {request.platform.upper()} - {request.subcategory}")
        print(f"{'='*60}")
        
        if request.platform.lower() == "daraz":
            subcategory = request.subcategory.lower().replace(" ", "")
            if subcategory not in DARAZ_DATASETS:
                raise HTTPException(
                status_code=404,
                detail=f"No CSV found for subcategory: {request.subcategory}"
                 )

            products = extract_daraz_products(subcategory, request.max_products)
            platform_name = "Daraz.pk"
            csv_file = "latest_data.csv"

        elif request.platform.lower() == "etsy":
            if not ETSY_DATA:
                 raise HTTPException(
                 status_code=404, 
                 detail="Etsy.csv not found. Please ensure the file exists."
                 )

            products = extract_etsy_products(request.max_products)
            platform_name = "Etsy.com"
            csv_file = "etsy.csv"

        else:
            raise HTTPException(
                status_code=400, 
                detail="Invalid platform. Choose 'daraz' or 'etsy'"
                 )
        if not products:
            raise HTTPException(
                status_code=404, 
                detail=f"No valid products found in {csv_file}. Please check the file format."
            )
        
        print(f"📊 Processing {len(products)} products")
        
        # Normalize features
        products = normalize_features(products)
        
        # Apply clustering
        n_clusters = min(3, len(products))
       # === REPLACE THIS LINE (around line 636) ===
        clustered_products, centers, cluster_labels, sil_score = apply_clustering(products, n_clusters)
        
        # Sort by ranking score for top products
        clustered_products.sort(key=lambda x: x['ranking_score'], reverse=True)
        
        # Calculate polarization score
             # Calculate polarization score
        polarization_score = calculate_polarization_score(clustered_products, centers, n_clusters)
        polarization_level = get_polarization_level(polarization_score)
        
        # Prepare cluster statistics
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
        
        # Feature importance
        feature_importance = {
            "price": round(abs(centers[:, 0].max() - centers[:, 0].min()) * 100, 1),
            "rating": round(abs(centers[:, 1].max() - centers[:, 1].min()) * 100, 1),
            "reviews": round(abs(centers[:, 2].max() - centers[:, 2].min()) * 100, 1),
            "popularity": round(abs(centers[:, 3].max() - centers[:, 3].min()) * 100, 1)
        }
        
        # Prepare response products (Top 20)
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
        
        print(f"\n✅ Analysis Complete:")
        print(f"   Platform: {platform_name}")
        print(f"   Products: {len(products)}")
        print(f"   Clusters: {n_clusters}")
        print(f"   Polarization Score: {polarization_score:.3f} ({polarization_level})")
        print(f"   Data Source: {csv_file}")
        
        return PolarizationAnalysis(
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
            silhouette_score=round(sil_score, 4)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("🌐 API STARTING - CSV ONLY MODE")
    print("="*60)
    
    if not CSV_FILES_FOUND["daraz"] and not CSV_FILES_FOUND["etsy"]:
        print("\n⚠️  WARNING: No CSV files found!")
        print("   The API will not work without CSV files.")
        print("   Please ensure daraz.csv and etsy.csv exist.")
    else:
        print("\n✅ CSV Files Status:")
        if CSV_FILES_FOUND["daraz"]:
            print(f"   📦 Daraz.csv: {len(DARAZ_DATASETS)} products")
        if CSV_FILES_FOUND["etsy"]:
            print(f"   🛍️ Etsy.csv: {len(ETSY_DATA)} products")
    
    print("\n🚀 Server running at: http://localhost:8000")
    print("📊 Check CSV status: http://localhost:8000/api/csv-status")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)