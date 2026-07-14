from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import os
import json
import urllib.request
import urllib.error
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

API_BASE_URL = os.getenv("API_BASE_URL", "https://product-polarization-analyzer-production.up.railway.app")

PLATFORMS = {
    "daraz": ["earpods", "powerbanks", "gaming_accessories", "mobile_phone_accessories", "smart_watches"],
    "etsy": ["wall_art", "handmade_gifts", "jewelry", "vintage", "accessories"]
}

def run_daily_analysis():
    """Daily analysis using urllib (no requests package needed)"""
    
    logging.info(f"🚀 Daily Analysis Started at {datetime.now()}")
    success, failed = 0, 0
    
    for platform, categories in PLATFORMS.items():
        for category in categories:
            try:
                url = f"{API_BASE_URL}/api/analyze-public"
                
                payload = {
                    "platform": platform,
                    "category": category,
                    "subcategory": category,
                    "max_products": 100,
                    "analysis_type": "current",
                    "save_to_db": True,
                    "k_value": None,
                    "weights": None
                }
                
                data = json.dumps(payload).encode('utf-8')
                
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={
                        'Content-Type': 'application/json',
                        'Content-Length': str(len(data))
                    },
                    method='POST'
                )
                
                with urllib.request.urlopen(req, timeout=120) as response:
                    if response.status == 200:
                        result = json.loads(response.read().decode())
                        score = result.get('polarization_score', 'N/A')
                        logging.info(f"✅ {platform}/{category} - Score: {score}")
                        success += 1
                    else:
                        logging.error(f"❌ {platform}/{category} - Failed: {response.status}")
                        failed += 1
                        
            except urllib.error.URLError as e:
                logging.error(f"❌ {platform}/{category} - URL Error: {e.reason}")
                failed += 1
            except Exception as e:
                logging.error(f"❌ {platform}/{category} - Error: {e}")
                failed += 1
    
    logging.info(f"📊 Complete - Success: {success}, Failed: {failed}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_daily_analysis, 
        'cron', 
        hour=2, 
        minute=0, 
        id='daily_analysis', 
        replace_existing=True
    )
    scheduler.start()
    logging.info("✅ Daily Scheduler Started - 2:00 AM Daily")
    return scheduler