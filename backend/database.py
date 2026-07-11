import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os
import traceback
import time  # ← YEH LINE ADD KAREIN (time module import karne ke liye)

DB_PATH = os.path.join(os.path.dirname(__file__), "polarization_data.db")

def get_db_connection():
    """Get database connection with timeout and WAL mode"""
    conn = sqlite3.connect(DB_PATH, timeout=20.0)  # ← 20 seconds timeout
    conn.execute("PRAGMA journal_mode=WAL")  # ← Write-Ahead Logging
    conn.execute("PRAGMA busy_timeout = 20000")  # ← 20 second busy timeout
    return conn

def init_database():
    """Initialize SQLite database with required tables"""
    conn = get_db_connection()  # ← Use get_db_connection instead of direct connect
    cursor = conn.cursor()
    
    # Main table for polarization analysis results
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS polarization_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            category TEXT NOT NULL,
            analysis_type TEXT NOT NULL,
            analysis_date DATETIME NOT NULL,
            week_number INTEGER,
            month_number INTEGER,
            year INTEGER,
            total_products INTEGER,
            polarization_score REAL,
            polarization_level TEXT,
            silhouette_score REAL,
            cluster_data TEXT,
            feature_importance TEXT,
            top_products TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table for storing daily/weekly snapshots
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS time_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            category TEXT NOT NULL,
            snapshot_type TEXT NOT NULL,
            snapshot_date DATETIME NOT NULL,
            polarization_score REAL,
            total_products INTEGER,
            avg_price REAL,
            avg_rating REAL,
            cluster_distribution TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            id INTEGER PRIMARY KEY,
            config_key TEXT UNIQUE,
            config_value TEXT
        )
    """)
    
    # Table for trend analysis
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS polarization_trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            category TEXT NOT NULL,
            period TEXT NOT NULL,
            start_date DATETIME,
            end_date DATETIME,
            avg_polarization REAL,
            trend_direction TEXT,
            volatility REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")


# ============================================================
# RAW PRODUCT DATA STORAGE (For Reproducibility)
# ============================================================

def init_raw_data_table():
    """Create table for storing raw product data"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS raw_product_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                category TEXT NOT NULL,
                product_name TEXT,
                price REAL,
                rating REAL,
                reviews INTEGER,
                popularity REAL,
                seller TEXT,
                brand TEXT,
                product_url TEXT,
                scraped_date DATE NOT NULL,
                analysis_id INTEGER,
                FOREIGN KEY (analysis_id) REFERENCES polarization_analysis(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Raw product data table initialized")
        
    except Exception as e:
        print(f"❌ Error creating raw data table: {e}")
        traceback.print_exc()


def save_raw_products(platform, category, products, analysis_id=None):
    """Save raw product data to database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        scraped_date = datetime.now().date()
        saved_count = 0
        
        for product in products:
            # Ensure all fields exist
            product_name = str(product.get('name', product.get('title', '')))[:200]
            price = float(product.get('price', 0))
            rating = float(product.get('rating', 0))
            reviews = int(product.get('reviews', product.get('reviewCount', 0)))
            popularity = float(product.get('popularity', 0))
            seller = str(product.get('seller', product.get('shopName', '')))[:50]
            brand = str(product.get('brand', 'Unknown'))[:30]
            product_url = str(product.get('url', product.get('listingUrl', '')))[:200]
            
            cursor.execute('''
                INSERT INTO raw_product_data 
                (platform, category, product_name, price, rating, reviews, 
                 popularity, seller, brand, product_url, scraped_date, analysis_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                platform,
                category,
                product_name,
                price,
                rating,
                reviews,
                popularity,
                seller,
                brand,
                product_url,
                scraped_date,
                analysis_id
            ))
            saved_count += 1
        
        conn.commit()
        conn.close()
        print(f"✅ Saved {saved_count} raw products for {platform}/{category}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving raw products: {e}")
        traceback.print_exc()
        return False


def get_raw_products(platform=None, category=None, date=None, limit=100):
    """Retrieve raw product data for verification"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM raw_product_data WHERE 1=1"
        params = []
        
        if platform:
            query += " AND platform = ?"
            params.append(platform)
        if category:
            query += " AND category = ?"
            params.append(category)
        if date:
            query += " AND scraped_date = ?"
            params.append(date)
        
        query += " ORDER BY scraped_date DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
        
    except Exception as e:
        print(f"❌ Error fetching raw products: {e}")
        return []


def get_category_stats(platform=None):
    """Get statistics per category"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                platform,
                category,
                COUNT(*) as total_products,
                AVG(price) as avg_price,
                AVG(rating) as avg_rating,
                AVG(reviews) as avg_reviews,
                MIN(scraped_date) as first_seen,
                MAX(scraped_date) as last_seen
            FROM raw_product_data
        '''
        params = []
        
        if platform:
            query += " WHERE platform = ?"
            params.append(platform)
        
        query += " GROUP BY platform, category ORDER BY total_products DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
        
    except Exception as e:
        print(f"❌ Error getting category stats: {e}")
        return []


def delete_raw_products(platform=None, category=None, days_old=None):
    """Delete raw products (for cleanup)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "DELETE FROM raw_product_data WHERE 1=1"
        params = []
        
        if platform:
            query += " AND platform = ?"
            params.append(platform)
        if category:
            query += " AND category = ?"
            params.append(category)
        if days_old:
            cutoff_date = (datetime.now() - timedelta(days=days_old)).date()
            query += " AND scraped_date < ?"
            params.append(cutoff_date)
        
        cursor.execute(query, params)
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"✅ Deleted {deleted} raw products")
        return deleted
        
    except Exception as e:
        print(f"❌ Error deleting raw products: {e}")
        return 0


def save_analysis_result(platform, category, analysis_type, analysis_date, 
                         total_products, polarization_score, polarization_level,
                         silhouette_score, clusters, feature_importance, top_products):
    """Save analysis result to database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create table with all columns (if not exists)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS polarization_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                category TEXT,
                analysis_type TEXT,
                analysis_date TIMESTAMP,
                total_products INTEGER,
                polarization_score REAL,
                polarization_level TEXT,
                silhouette_score REAL,
                clusters TEXT,
                feature_importance TEXT,
                top_products TEXT
            )
        """)
        
        # Insert data
        cursor.execute("""
            INSERT INTO polarization_analysis 
            (platform, category, analysis_type, analysis_date, total_products, 
             polarization_score, polarization_level, silhouette_score, 
             clusters, feature_importance, top_products)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            platform, category, analysis_type, analysis_date,
            total_products, polarization_score, polarization_level,
            silhouette_score, 
            json.dumps(clusters) if clusters else None,
            json.dumps(feature_importance) if feature_importance else None,
            json.dumps(top_products) if top_products else None
        ))
        
        conn.commit()
        conn.close()
        print(f"✅ Saved {analysis_type} analysis for {platform}/{category}")
        
    except Exception as e:
        print(f"❌ Error saving analysis: {e}")
        traceback.print_exc()
def migrate_database():
    """Add missing columns to polarization_analysis table"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if clusters column exists
        cursor.execute("PRAGMA table_info(polarization_analysis)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Add clusters column if missing
        if 'clusters' not in columns:
            print("🔧 Adding 'clusters' column to polarization_analysis...")
            cursor.execute("ALTER TABLE polarization_analysis ADD COLUMN clusters TEXT")
            print("✅ Added clusters column")
        
        # Add feature_importance column if missing
        if 'feature_importance' not in columns:
            print("🔧 Adding 'feature_importance' column to polarization_analysis...")
            cursor.execute("ALTER TABLE polarization_analysis ADD COLUMN feature_importance TEXT")
            print("✅ Added feature_importance column")
        
        # Add top_products column if missing
        if 'top_products' not in columns:
            print("🔧 Adding 'top_products' column to polarization_analysis...")
            cursor.execute("ALTER TABLE polarization_analysis ADD COLUMN top_products TEXT")
            print("✅ Added top_products column")
        
        # Add analysis_date column if missing
        if 'analysis_date' not in columns:
            print("🔧 Adding 'analysis_date' column to polarization_analysis...")
            cursor.execute("ALTER TABLE polarization_analysis ADD COLUMN analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            print("✅ Added analysis_date column")
        
        conn.commit()
        conn.close()
        print("✅ Database migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
        traceback.print_exc()

def get_current_analysis(platform: str, category: str) -> Optional[Dict]:
    """Get most recent analysis for current period"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM polarization_analysis 
        WHERE platform = ? AND category = ? AND analysis_type = 'current'
        ORDER BY analysis_date DESC LIMIT 1
    ''', (platform, category))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'id': row[0],
            'platform': row[1],
            'category': row[2],
            'analysis_type': row[3],
            'analysis_date': row[4],
            'total_products': row[7],
            'polarization_score': row[8],
            'polarization_level': row[9],
            'silhouette_score': row[10],
            'clusters': json.loads(row[11]),
            'feature_importance': json.loads(row[12]),
            'top_products': json.loads(row[13])
        }
    return None

def get_weekly_analysis(platform: str, category: str, week_offset: int = 0) -> List[Dict]:
    """Get weekly analysis (0 = current week, -1 = last week, -2 = 2 weeks ago)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM polarization_analysis 
        WHERE platform = ? AND category = ? AND analysis_type = 'weekly'
        ORDER BY analysis_date DESC
        LIMIT 5
    ''', (platform, category))
    
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        results.append({
            'id': row[0],
            'analysis_date': row[4],
            'week_number': row[5],
            'total_products': row[7],
            'polarization_score': row[8],
            'polarization_level': row[9],
            'silhouette_score': row[10],
            'clusters': json.loads(row[11])
        })
    
    return results

def get_monthly_analysis(platform: str, category: str, month_offset: int = 0) -> List[Dict]:
    """Get monthly analysis"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM polarization_analysis 
        WHERE platform = ? AND category = ? AND analysis_type = 'monthly'
        ORDER BY analysis_date DESC
        LIMIT 6
    ''', (platform, category))
    
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        results.append({
            'id': row[0],
            'analysis_date': row[4],
            'month_number': row[6],
            'year': row[7],
            'total_products': row[8],
            'polarization_score': row[9],
            'polarization_level': row[10]
        })
    
    return results

def save_time_snapshot(platform, category, snapshot_type, snapshot_date,
                       polarization_score, total_products, avg_price, 
                       avg_rating, cluster_distribution):
    """Save time snapshot to database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create table with all columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                category TEXT,
                snapshot_type TEXT,
                snapshot_date TIMESTAMP,
                polarization_score REAL,
                total_products INTEGER,
                avg_price REAL,
                avg_rating REAL,
                cluster_distribution TEXT
            )
        """)
        
        cursor.execute("""
            INSERT INTO time_snapshots 
            (platform, category, snapshot_type, snapshot_date, 
             polarization_score, total_products, avg_price, avg_rating, cluster_distribution)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            platform, category, snapshot_type, snapshot_date,
            polarization_score, total_products, avg_price, avg_rating,
            json.dumps(cluster_distribution) if cluster_distribution else None
        ))
        
        conn.commit()
        conn.close()
        print(f"✅ Saved {snapshot_type} snapshot for {platform}/{category}")
        
    except Exception as e:
        print(f"❌ Error saving snapshot: {e}")
        traceback.print_exc()
def get_trend_data(platform: str, category: str, period: str, limit: int = 10) -> List[Dict]:
    """Get trend data for visualization"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT snapshot_date, polarization_score, total_products 
        FROM time_snapshots 
        WHERE platform = ? AND category = ? AND snapshot_type = ?
        ORDER BY snapshot_date DESC
        LIMIT ?
    ''', (platform, category, period, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [{'date': row[0], 'polarization_score': row[1], 'total_products': row[2]} for row in rows]

def get_polarization_comparison(platform: str, category: str) -> Dict:
    """Get comparison between current, weekly avg, and monthly avg"""
    current = get_current_analysis(platform, category)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get average of last 4 weeks
    cursor.execute('''
        SELECT AVG(polarization_score), COUNT(*) 
        FROM polarization_analysis 
        WHERE platform = ? AND category = ? AND analysis_type = 'weekly'
        ORDER BY analysis_date DESC
        LIMIT 4
    ''', (platform, category))
    
    weekly_row = cursor.fetchone()
    weekly_avg = weekly_row[0] if weekly_row and weekly_row[0] else 0
    weekly_count = weekly_row[1] if weekly_row else 0
    
    # Get average of last 3 months
    cursor.execute('''
        SELECT AVG(polarization_score), COUNT(*) 
        FROM polarization_analysis 
        WHERE platform = ? AND category = ? AND analysis_type = 'monthly'
        ORDER BY analysis_date DESC
        LIMIT 3
    ''', (platform, category))
    
    monthly_row = cursor.fetchone()
    monthly_avg = monthly_row[0] if monthly_row and monthly_row[0] else 0
    monthly_count = monthly_row[1] if monthly_row else 0
    
    conn.close()
    
    return {
        'current': current['polarization_score'] if current else 0,
        'weekly_avg': round(weekly_avg, 4) if weekly_count > 0 else None,
        'monthly_avg': round(monthly_avg, 4) if monthly_count > 0 else None,
        'weekly_trend': calculate_trend(current['polarization_score'] if current else 0, weekly_avg) if weekly_avg else None,
        'monthly_trend': calculate_trend(current['polarization_score'] if current else 0, monthly_avg) if monthly_avg else None
    }

def calculate_trend(current: float, historical: float) -> str:
    """Calculate trend direction"""
    if current > historical * 1.05:
        return "increasing"
    elif current < historical * 0.95:
        return "decreasing"
    else:
        return "stable"

def get_all_historical_data(platform: str, category: str) -> Dict:
    """Get complete historical data for charts"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all weekly data
    cursor.execute('''
        SELECT analysis_date, polarization_score, total_products
        FROM polarization_analysis 
        WHERE platform = ? AND category = ? AND analysis_type = 'weekly'
        ORDER BY analysis_date ASC
    ''', (platform, category))
    
    weekly_data = [{'date': row[0], 'score': row[1], 'products': row[2]} for row in cursor.fetchall()]
    
    # Get all monthly data
    cursor.execute('''
        SELECT analysis_date, polarization_score, total_products
        FROM polarization_analysis 
        WHERE platform = ? AND category = ? AND analysis_type = 'monthly'
        ORDER BY analysis_date ASC
    ''', (platform, category))
    
    monthly_data = [{'date': row[0], 'score': row[1], 'products': row[2]} for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        'weekly': weekly_data,
        'monthly': monthly_data
    }

# database.py main add karo

def save_daily_snapshot(platform, category, snapshot_date, polarization_score, total_products):
    """Daily snapshot save with retry"""
    
    if hasattr(snapshot_date, 'strftime'):
        date_str = snapshot_date.strftime('%Y-%m-%d')
    else:
        date_str = str(snapshot_date)
    
    print(f"💾 Saving daily snapshot: {platform}/{category} on {date_str}")
    
    max_retries = 5
    for attempt in range(max_retries):
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    category TEXT NOT NULL,
                    snapshot_date TEXT NOT NULL,
                    polarization_score REAL,
                    total_products INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                INSERT OR REPLACE INTO daily_snapshots
                (platform, category, snapshot_date, polarization_score, total_products)
                VALUES (?, ?, ?, ?, ?)
            ''', (platform, category, date_str, polarization_score, total_products))
            
            conn.commit()
            print(f"   ✅ Daily snapshot saved")
            return True
            
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                print(f"   ⚠️ Database locked, retrying... ({attempt + 2}/{max_retries})")
                time.sleep(1)
                continue
            else:
                print(f"   ❌ Database error: {e}")
                raise e
        except Exception as e:
            print(f"   ❌ Error: {e}")
            raise e
        finally:
            if conn:
                conn.close()
    
    return False
def get_daily_snapshots(platform, category, start_date=None, end_date=None):
    """特定日期 range main daily snapshots fetch karo"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if start_date and end_date:
        cursor.execute('''
            SELECT snapshot_date, polarization_score, total_products
            FROM daily_snapshots
            WHERE platform = ? AND category = ?
            AND snapshot_date BETWEEN ? AND ?
            ORDER BY snapshot_date ASC
        ''', (platform, category, start_date, end_date))
    else:
        # ✅ Agar date range nahi di to saara data lelo
        cursor.execute('''
            SELECT snapshot_date, polarization_score, total_products
            FROM daily_snapshots
            WHERE platform = ? AND category = ?
            ORDER BY snapshot_date ASC
        ''', (platform, category))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {'date': row[0], 'polarization_score': row[1], 'total_products': row[2]}
        for row in rows
    ]

def get_weekly_snapshots(platform, category, num_weeks):
    """Last N weeks ke weekly snapshots fetch karo"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT analysis_date, polarization_score, total_products
        FROM polarization_analysis
        WHERE platform = ? AND category = ? AND analysis_type = 'weekly'
        ORDER BY analysis_date DESC
        LIMIT ?
    ''', (platform, category, num_weeks))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Reverse karo taake chronological order mile
    rows.reverse()
    
    return [
        {'date': row[0], 'polarization_score': row[1], 'total_products': row[2]}
        for row in rows
    ]


# ============================================================
# SYSTEM SETTINGS FUNCTIONS
# ============================================================

def get_system_settings():
    """Get system settings from database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create table if not exists (without updated_at)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                config_key TEXT UNIQUE,
                config_value TEXT
            )
        """)
        
        # Get all settings
        cursor.execute("SELECT config_key, config_value FROM system_settings")
        rows = cursor.fetchall()
        conn.close()
        
        # Default settings
        settings = {
            "analysis": {
                "default_k_value": 3,
                "max_products": 100,
                "weekly_analysis_enabled": True,
                "monthly_analysis_enabled": True
            },
            "email": {
                "sender": "admin@polarization.com",
                "otp_expiry_minutes": 10
            }
        }
        
        # Override with database values
        for key, value in rows:
            if key.startswith("analysis."):
                setting_key = key.replace("analysis.", "")
                if setting_key in settings["analysis"]:
                    if isinstance(settings["analysis"][setting_key], bool):
                        settings["analysis"][setting_key] = value.lower() == "true"
                    elif isinstance(settings["analysis"][setting_key], int):
                        settings["analysis"][setting_key] = int(value)
                    else:
                        settings["analysis"][setting_key] = value
            elif key.startswith("email."):
                setting_key = key.replace("email.", "")
                if setting_key in settings["email"]:
                    if isinstance(settings["email"][setting_key], int):
                        settings["email"][setting_key] = int(value)
                    else:
                        settings["email"][setting_key] = value
        
        return settings
        
    except Exception as e:
        print(f"❌ Error getting settings: {e}")
        traceback.print_exc()
        return {
            "analysis": {
                "default_k_value": 3,
                "max_products": 100,
                "weekly_analysis_enabled": True,
                "monthly_analysis_enabled": True
            },
            "email": {
                "sender": "admin@polarization.com",
                "otp_expiry_minutes": 10
            }
        }
def save_system_settings(settings):
    """Save system settings to database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create table if not exists (without updated_at)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                config_key TEXT UNIQUE,
                config_value TEXT
            )
        """)
        
        # Flatten settings dictionary
        flat_settings = {}
        
        # Analysis settings
        if "analysis" in settings:
            for key, value in settings["analysis"].items():
                flat_settings[f"analysis.{key}"] = str(value)
        
        # Email settings
        if "email" in settings:
            for key, value in settings["email"].items():
                flat_settings[f"email.{key}"] = str(value)
        
        # Insert or update each setting (without updated_at)
        for key, value in flat_settings.items():
            cursor.execute("""
                INSERT INTO system_settings (config_key, config_value)
                VALUES (?, ?)
                ON CONFLICT(config_key) DO UPDATE SET 
                    config_value = excluded.config_value
            """, (key, value))
        
        conn.commit()
        conn.close()
        print(f"✅ System settings saved: {len(flat_settings)} settings")
        return True
        
    except Exception as e:
        print(f"❌ Error saving settings: {e}")
        traceback.print_exc()
        return False
def get_setting(key, default=None):
    """Get a single setting value"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT config_value FROM system_settings WHERE config_key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return row[0]
        return default
    except Exception as e:
        print(f"❌ Error getting setting {key}: {e}")
        return default


def save_setting(key, value):
    """Save a single setting value"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO system_settings (config_key, config_value)
            VALUES (?, ?)
            ON CONFLICT(config_key) DO UPDATE SET 
                config_value = excluded.config_value,
                updated_at = CURRENT_TIMESTAMP
        """, (key, str(value)))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error saving setting {key}: {e}")
        return False

# Initialize database on module load
init_database()
init_raw_data_table()