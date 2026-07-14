import requests
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

API_BASE_URL = os.getenv("API_BASE_URL", "https://product-polarization-analyzer-production.up.railway.app")

PLATFORMS = {
    "daraz": ["earpods", "powerbanks", "gaming_accessories", "mobile_phone_accessories", "smart_watches"],
    "etsy": ["wall_art", "handmade_gifts", "jewelry", "vintage", "accessories"]
}

def run_daily_analysis():
    logging.info(f"🚀 Daily Analysis Started at {datetime.now()}")
    success, failed = 0, 0
    
    for platform, categories in PLATFORMS.items():
        for category in categories:
            try:
                # ✅ Sahi endpoint - /api/analyze
                response = requests.post(
                    f"{API_BASE_URL}/api/analyze",
                    json={
                        "platform": platform,  # ✅ "daraz" ya "etsy"
                        "category": category,
                        "subcategory": category,
                        "max_products": 100,
                        "analysis_type": "current",
                        "save_to_db": True,
                        "k_value": None,
                        "weights": None
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=120
                )
                
                if response.status_code == 200:
                    data = response.json()
                    score = data.get('polarization_score', 'N/A')
                    logging.info(f"✅ {platform}/{category} - Score: {score}")
                    success += 1
                else:
                    logging.error(f"❌ {platform}/{category} - Failed: {response.status_code}")
                    failed += 1
                    
            except Exception as e:
                logging.error(f"❌ {platform}/{category} - Error: {e}")
                failed += 1
    
    logging.info(f"📊 Complete - Success: {success}, Failed: {failed}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_daily_analysis, 'cron', hour=2, minute=0, id='daily_analysis', replace_existing=True)
    scheduler.start()
    logging.info("✅ Daily Scheduler Started - 2:00 AM Daily")
    return scheduler