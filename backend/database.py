import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os
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

def save_analysis_result(platform: str, category: str, analysis_type: str,
                         analysis_date: datetime, total_products: int,
                         polarization_score: float, polarization_level: str,
                         silhouette_score: float, clusters: List[Dict],
                         feature_importance: Dict, top_products: List[Dict]):
    """Save analysis result with retry logic"""
    
    week_num = analysis_date.isocalendar()[1]
    month_num = analysis_date.month
    year = analysis_date.year
    
    # Microsecond hatado taake consistent rahe
    analysis_date_clean = analysis_date.replace(microsecond=0)
    
    max_retries = 5
    for attempt in range(max_retries):
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO polarization_analysis
                (platform, category, analysis_type, analysis_date, week_number, month_number, year,
                 total_products, polarization_score, polarization_level, silhouette_score,
                 cluster_data, feature_importance, top_products)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                platform, category, analysis_type, analysis_date_clean, week_num, month_num, year,
                total_products, polarization_score, polarization_level, silhouette_score,
                json.dumps(clusters), json.dumps(feature_importance), json.dumps(top_products[:10])
            ))
            
            conn.commit()
            print(f"✅ Saved {analysis_type} analysis for {platform}/{category}")
            return True
            
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                print(f"⚠️ Database locked, retrying... ({attempt + 2}/{max_retries})")
                time.sleep(1)
                continue
            else:
                print(f"❌ Database error: {e}")
                raise e
        except Exception as e:
            print(f"❌ Error: {e}")
            raise e
        finally:
            if conn:
                conn.close()
    
    return False
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

def save_time_snapshot(platform: str, category: str, snapshot_type: str,
                       snapshot_date: datetime, polarization_score: float,
                       total_products: int, avg_price: float, avg_rating: float,
                       cluster_distribution: Dict):
    """Save time-based snapshot for trend analysis"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO time_snapshots 
        (platform, category, snapshot_type, snapshot_date, polarization_score,
         total_products, avg_price, avg_rating, cluster_distribution)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        platform, category, snapshot_type, snapshot_date, polarization_score,
        total_products, avg_price, avg_rating, json.dumps(cluster_distribution)
    ))
    
    conn.commit()
    conn.close()

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

# Initialize database on module load
init_database()